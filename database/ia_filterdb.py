import logging
import re
import base64
import asyncio
import time
from struct import pack
from bson.objectid import ObjectId
import motor.motor_asyncio
from hydrogram.file_id import FileId
from info import DATABASE_URL, DATABASE_NAME, USE_CAPTION_FILTER

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# ⚙️ MOTOR CONNECTION — Memory-Leak & RAM Guard Optimized
# ─────────────────────────────────────────────────────────
client = motor.motor_asyncio.AsyncIOMotorClient(
    DATABASE_URL,
    maxPoolSize=15,             
    minPoolSize=0,              
    maxIdleTimeMS=30000,        
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000,
    socketTimeoutMS=20000,
    retryWrites=True,
    retryReads=True,
)
db = client[DATABASE_NAME]

primary = db["Primary"]
cloud   = db["Cloud"]
archive = db["Archive"]
actors  = db["Actors"]  

COLLECTIONS = {
    "primary": primary,
    "cloud":   cloud,
    "archive": archive,
    "actors":  actors,   
}

_stats_cache = None
_stats_cache_time = 0
STATS_CACHE_TTL = 60  

# ─────────────────────────────────────────────────────────
# 🧹 REGEX NAME CLEANER — (आपके फ़ाइल फ़ॉर्मेट के लिए विशेष रूप से निर्मित)
# ─────────────────────────────────────────────────────────
def extract_clean_name(file_name: str) -> str:
    if not file_name:
        return "Unknown File"
    name = re.sub(r'^\[.*?\]', '', file_name).strip()
    if '|' in name:
        name = name.split('|')[0].strip()
    name = re.sub(r'\.(mp4|mkv|mov|avi|ts|wmv)$', '', name, flags=re.IGNORECASE).strip()
    return name

# ─────────────────────────────────────────────────────────
# ⚡ INDEXES — Dynamic Configuration
# ─────────────────────────────────────────────────────────
async def ensure_indexes():
    for name, col in COLLECTIONS.items():
        try:
            if name == "actors":
                continue

            if USE_CAPTION_FILTER:
                await col.create_index([("file_name", "text"), ("caption", "text")], name=f"{name}_text")
            else:
                await col.create_index([("file_name", "text")], name=f"{name}_text")
            
            await col.create_index("file_name", name=f"{name}_filename_idx")
            await col.create_index("group_id", name=f"{name}_group_id_idx", sparse=True)
            logger.info(f"✅ Fast Search & Non-Bloated Indexes OK: {name}")
        except Exception as e:
            if "already exists" in str(e) or "IndexKeySpecsConflict" in str(e): pass
            else: logger.warning(f"Index warning [{name}]: {e}")

    try:
        await actors.create_index([("name", "text")], name="actors_name_text")
        logger.info("✅ Actor Profile System Indexes OK")
    except Exception as e:
        if "already exists" not in str(e) and "IndexKeySpecsConflict" not in str(e):
            logger.warning(f"Actor Index warning: {e}")

# ─────────────────────────────────────────────────────────
# 📊 DB STATS
# ─────────────────────────────────────────────────────────
async def db_count_documents():
    global _stats_cache, _stats_cache_time
    now = time.time()
    if _stats_cache and (now - _stats_cache_time < STATS_CACHE_TTL):
        return _stats_cache

    try:
        p_task = primary.estimated_document_count()
        c_task = cloud.estimated_document_count()
        a_task = archive.estimated_document_count()
        
        thumb_query = {"thumb_url": {"$exists": True, "$type": "string", "$ne": "NO_THUMB"}}
        pt_task = primary.count_documents(thumb_query)
        ct_task = cloud.count_documents(thumb_query)
        at_task = archive.count_documents(thumb_query)

        p, c, a, pt, ct, at = await asyncio.gather(p_task, c_task, a_task, pt_task, ct_task, at_task)
        
        _stats_cache = {
            "primary": p, "cloud": c, "archive": a, "total": p + c + a,
            "primary_thumb": pt, "cloud_thumb": ct, "archive_thumb": at, "total_thumb": pt + ct + at
        }
        _stats_cache_time = now
        return _stats_cache
    except Exception as e:
        logger.error(f"Count Breakdown error: {e}")
        return {"primary": 0, "cloud": 0, "archive": 0, "total": 0, "primary_thumb": 0, "cloud_thumb": 0, "archive_thumb": 0, "total_thumb": 0}

# ─────────────────────────────────────────────────────────
# 💾 SAVE FILE
# ─────────────────────────────────────────────────────────
async def save_file(media, collection_type="primary"):
    try:
        file_id = unpack_new_file_id(media.file_id)
        if not file_id: return "err"

        f_name  = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.file_name or "")).strip()
        caption = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.caption  or "")).strip()
        file_type = type(media).__name__.lower()
        col = COLLECTIONS.get(collection_type, primary)
        
        existing_doc = await col.find_one({"_id": file_id}, {"file_ref": 1, "thumb_url": 1, "caption": 1, "group_id": 1})
        if existing_doc:
            if existing_doc.get("file_ref") == media.file_id: return "dup"
            old_thumb = existing_doc.get("thumb_url")
            thumb_url = old_thumb if old_thumb and old_thumb != "NO_THUMB" else None
            group_id = existing_doc.get("group_id", "") 
        else:
            thumb_url = None
            group_id = ""

        update_set = {"file_ref":  media.file_id, "file_name": f_name, "file_size": media.file_size, "file_type": file_type}
        if thumb_url: update_set["thumb_url"] = thumb_url
        if group_id: update_set["group_id"] = group_id

        update_payload = {"$set": update_set}
        unset_payload = {}

        if USE_CAPTION_FILTER and caption: update_set["caption"] = caption
        else: unset_payload["caption"] = ""

        if unset_payload: update_payload["$unset"] = unset_payload

        await col.update_one({"_id": file_id}, update_payload, upsert=True)
        return "suc"
    except Exception as e:
        logger.error(f"save_file error: {e}")
        return "err"

# ─────────────────────────────────────────────────────────
# 🔍 REGEX BUILDER WITH SHORT-QUERY SHIELD
# ─────────────────────────────────────────────────────────
ALLOWED_SHORT = {"hd", "4k", "3d", "8k", "5.1", "7.1", "kg", "rr", "uhd", "hevc", "x265", "x264"}

def _build_regex(query: str):
    query = query.strip()
    if not query: return None
    q_lower = query.lower()
    
    if len(query) < 2 or (len(query) == 2 and q_lower not in ALLOWED_SHORT): return None
    if ' ' not in query: raw = r'(\b|[\.\+\-_])' + re.escape(query) + r'(\b|[\.\+\-_])'
    else: raw = re.escape(query).replace(r'\ ', r'.*[\s\.\+\-_]')

    try: return re.compile(raw, flags=re.IGNORECASE)
    except Exception: return re.compile(re.escape(query), flags=re.IGNORECASE)

# ─────────────────────────────────────────────────────────
# 🚀 SMART SEARCH ENGINE (With Dynamic Grouping Core)
# ─────────────────────────────────────────────────────────
async def _search(col, raw_query: str, regex, offset: int, limit: int, lang=None, bypass_count=False, view_mode="group"):
    clean_query = raw_query.replace('"', '').replace("'", "").strip()
    words = clean_query.split() if clean_query else []
    strict_query = " ".join(f'"{word}"' for word in words) if words else ""

    fetch_limit = limit * 6 if view_mode == "group" else limit
    fetch_offset = 0 if view_mode == "group" else offset

    docs = []
    text_flt = {}
    is_text_search = False

    if strict_query:
        text_flt = {"$text": {"$search": strict_query}}
        if lang: text_flt = {"$and": [text_flt, {"file_name": re.compile(lang, re.IGNORECASE)}]}
        is_text_search = True
        
        cursor = col.find(text_flt, {"_id": 1, "file_name": 1, "file_size": 1, "file_type": 1, "file_ref": 1, "caption": 1, "thumb_url": 1, "group_id": 1, "score": {"$meta": "textScore"}})
        cursor.sort([("score", {"$meta": "textScore"})])
        cursor.skip(fetch_offset).limit(fetch_limit)
        docs = await cursor.to_list(length=fetch_limit)

    if not docs and regex:
        is_text_search = False
        reg_flt = {"$or": [{"file_name": regex}, {"caption": regex}]} if USE_CAPTION_FILTER else {"file_name": regex}
        if lang: reg_flt = {"$and": [reg_flt, {"file_name": re.compile(lang, re.IGNORECASE)}]}
        
        cursor = col.find(reg_flt, {"_id": 1, "file_name": 1, "file_size": 1, "file_type": 1, "file_ref": 1, "caption": 1, "thumb_url": 1, "group_id": 1}).sort('_id', -1)
        cursor.skip(fetch_offset).limit(fetch_limit)
        docs = await cursor.to_list(length=fetch_limit)

    for doc in docs: 
        doc["file_id"] = doc["_id"]

    if view_mode == "group" and docs:
        grouped_dict = {}
        for d in docs:
            g_id = d.get("group_id", "").strip()
            clean_title = extract_clean_name(d.get("file_name", "Unknown File"))
            group_key = g_id if g_id else clean_title.lower()

            if group_key not in grouped_dict:
                grouped_dict[group_key] = {
                    "_id": d["_id"],
                    "file_id": d["_id"],
                    "file_name": clean_title,  
                    "thumb_url": d.get("thumb_url"),
                    "file_type": d.get("file_type", "document"),
                    "caption": d.get("caption", ""),
                    "group_id": group_key,
                    "is_group": True,
                    "files": []
                }
            
            if (not grouped_dict[group_key]["thumb_url"] or grouped_dict[group_key]["thumb_url"] == "NO_THUMB") and d.get("thumb_url") and d.get("thumb_url") != "NO_THUMB":
                grouped_dict[group_key]["thumb_url"] = d["thumb_url"]

            grouped_dict[group_key]["files"].append({
                "file_id": d["_id"],
                "file_name": d.get("file_name", "Unknown File"),
                "file_size": d.get("file_size", 0),
                "file_type": d.get("file_type", "document"),
                "file_ref": d.get("file_ref") or d["_id"],
                "caption": d.get("caption", ""),
                "thumb_url": d.get("thumb_url")
            })

        grouped_docs = list(grouped_dict.values())
        paginated_docs = grouped_docs[offset:offset+limit]
        
        if bypass_count: count = 0
        else:
            flt_query = text_flt if is_text_search else (reg_flt if 'reg_flt' in locals() else {})
            count = await col.count_documents(flt_query)
            
        return paginated_docs, count

    if bypass_count: count = 0
    else:
        flt_query = text_flt if is_text_search else (reg_flt if 'reg_flt' in locals() else {})
        count = await col.count_documents(flt_query) if docs else 0

    return docs, count

# ─────────────────────────────────────────────────────────
# 🌐 PUBLIC SEARCH API
# ─────────────────────────────────────────────────────────
async def get_search_results(query, max_results, offset=0, lang=None, collection_type="primary", bypass_count=False, view_mode="group"):
    if not query: return [], "", 0, collection_type
    raw_query  = str(query).strip()
    regex      = _build_regex(raw_query)
    
    if not raw_query.replace('"', '').replace("'", "").strip().split() and not regex:
        return [], "", 0, collection_type

    results, total, actual_src = [], 0, collection_type

    if collection_type == "all":
        for src, col in [("primary", primary), ("cloud", cloud), ("archive", archive)]:
            docs, cnt = await _search(col, raw_query, regex, offset, max_results, lang, bypass_count=bypass_count, view_mode=view_mode)
            if docs:
                results, total, actual_src = docs, cnt, src
                break  
    else:
        col = COLLECTIONS.get(collection_type, primary)
        results, total = await _search(col, raw_query, regex, offset, max_results, lang, bypass_count=bypass_count, view_mode=view_mode)

    if bypass_count:
        has_more = len(results) == max_results
        next_offset = offset + max_results if has_more else ""
        total = offset + len(results) + (1 if has_more else 0)
    else:
        next_offset = offset + max_results
        next_offset = "" if next_offset >= total else next_offset

    return results, next_offset, total, actual_src

# ─────────────────────────────────────────────────────────
# 🗑 DELETE FILES 
# ─────────────────────────────────────────────────────────
async def delete_files(query, collection_type="all"):
    deleted = 0
    try:
        if query == "*":
            cols = [col for name, col in COLLECTIONS.items() if (collection_type == "all" or name == collection_type) and name != "actors"]
            for col in cols:
                res = await col.delete_many({})
                deleted += res.deleted_count
            return deleted

        regex = _build_regex(str(query))
        if not regex: return 0
        flt   = {"file_name": regex}
        cols  = [col for name, col in COLLECTIONS.items() if (collection_type == "all" or name == collection_type) and name != "actors"]
        for col in cols:
            res = await col.delete_many(flt)
            deleted += res.deleted_count
        return deleted
    except Exception as e:
        logger.error(f"delete_files error: {e}")
        return deleted

async def get_file_details(file_id):
    try:
        for col in [primary, cloud, archive]:
            doc = await col.find_one({"_id": file_id}, {"_id": 1, "file_name": 1, "file_size": 1, "file_ref": 1, "caption": 1, "thumb_url": 1, "group_id": 1})
            if doc:
                doc["file_id"] = doc["_id"]  
                return doc
        return None
    except Exception as e:
        logger.error(f"get_file_details error: {e}")
        return None

def encode_file_id(s: bytes) -> str:
    r, n = b"", 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0: n += 1
        else:
            if n: r += b"\x00" + bytes([n]); n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def unpack_new_file_id(new_file_id: str):
    try:
        decoded = FileId.decode(new_file_id)
        return encode_file_id(pack("<iiqq", int(decoded.file_type), decoded.dc_id, decoded.media_id, decoded.access_hash))
    except Exception as e:
        logger.error(f"unpack_new_file_id error: {e}")
        return None

# ─────────────────────────────────────────────────────────
# 🎭 ACTOR TAGS SEARCH (100% FIXED FOR ORIGINAL NATIVE LAYOUT)
# ─────────────────────────────────────────────────────────
async def get_actor_search_results(actor_name, tags_list, max_results, offset=0, collection_type="all"):
    all_terms = []
    if actor_name and str(actor_name).strip():
        all_terms.append(str(actor_name).strip())
    if tags_list and isinstance(tags_list, list):
        for t in tags_list:
            if t and str(t).strip():
                all_terms.append(str(t).strip())
                
    if not all_terms:
        return [], ""
                
    escaped_terms = [re.escape(term) for term in all_terms if term]
    combined_raw = r'(' + '|'.join(escaped_terms) + r')'
    
    try: regex = re.compile(combined_raw, flags=re.IGNORECASE)
    except Exception: regex = re.compile(re.escape(actor_name) if actor_name else "NO_ACTOR_MATCH_FOUND", flags=re.IGNORECASE)
        
    reg_flt = {"$or": [{"file_name": regex}, {"caption": regex}]} if USE_CAPTION_FILTER else {"file_name": regex}
    results = []
    cols = [primary, cloud, archive] if collection_type == "all" else [COLLECTIONS.get(collection_type, primary)]
    
    for col in cols:
        cursor = col.find(reg_flt, {"_id": 1, "file_name": 1, "file_size": 1, "file_type": 1, "file_ref": 1, "caption": 1, "thumb_url": 1, "group_id": 1}).sort('_id', -1)
        cursor.skip(offset).limit(max_results)
        docs = await cursor.to_list(length=max_results)
        if docs:
            for doc in docs:
                doc["file_id"] = doc["_id"]
                doc["source_col"] = col.name.lower()
            results.extend(docs)

    has_more = len(results) == max_results
    next_offset = offset + max_results if has_more else ""
    return results, next_offset

# ─────────────────────────────────────────────────────────
# 🗑️ ACTOR PROFILE PURGE PIPELINE
# ─────────────────────────────────────────────────────────
async def delete_actor_profile(actor_id):
    try:
        res = await actors.delete_one({"_id": ObjectId(actor_id)})
        return bool(res.deleted_count)
    except Exception as e:
        logger.error(f"delete_actor_profile error: {e}")
        return False

async def delete_gallery_image_by_index(actor_id, index: int):
    try:
        doc = await actors.find_one({"_id": ObjectId(actor_id)})
        if not doc or "gallery" not in doc: return False
        gallery = doc["gallery"]
        if index < 0 or index >= len(gallery): return False
        target_tg_id = gallery[index]
        res = await actors.update_one({"_id": ObjectId(actor_id)}, {"$pull": {"gallery": target_tg_id}})
        return bool(res.modified_count)
    except Exception as e:
        logger.error(f"delete_gallery_image error: {e}")
        return False
