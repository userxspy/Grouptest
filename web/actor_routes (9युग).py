import io
import gc
import time
import json
import html
from aiohttp import web
from bson.objectid import ObjectId
from utils import temp, get_size
from info import BIN_CHANNEL, MAX_WEB_RESULTS
from database.ia_filterdb import actors, get_actor_search_results
from web.web_assets import build_page, get_auth, form_wrapper

actor_routes = web.RouteTableDef()

# ─────────────────────────────────────────────────────────
# 🎭 PUBLIC VIEW: ACTORS DIRECTORY CATALOG PAGE
# ─────────────────────────────────────────────────────────
@actor_routes.get('/actors')
async def actors_directory_page(req):
    role, _ = await get_auth(req)
    if not role: return web.HTTPFound('/login')
        
    cursor = actors.find({}).sort("created_at", -1)
    all_actors = await cursor.to_list(length=200)
    
    admin_header_action = ""
    if role == 'admin':
        admin_header_action = '''
        <div style="display:flex; justify-content:flex-end; margin-bottom:25px;">
            <a href="/admin/create_actor" style="background:var(--accent); color:#fff; padding:12px 24px; border-radius:8px; font-weight:700; text-decoration:none; font-size:14px; transition:0.2s; box-shadow:0 4px 15px rgba(229,9,20,0.3);">➕ Create New Actor</a>
        </div>
        '''
        
    actors_grid_html = ""
    if not all_actors:
        actors_grid_html = '<div style="color:var(--muted); text-align:center; padding:60px 20px; grid-column:1/-1;">🎭 No actor profiles created yet.</div>'
    else:
        actors_grid_html = '<div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(160px, 1fr)); gap:20px;">'
        for act in all_actors:
            act_id = str(act["_id"])
            actors_grid_html += f'''
            <div style="background:var(--card); border:1px solid var(--border); border-radius:10px; overflow:hidden; transition:0.2s; cursor:pointer;" onclick="window.location.href='/actor/{act_id}'">
                <div style="position:relative; padding-top:135%; background:var(--bg3); overflow:hidden;">
                    <img src="/api/actor/photo?id={act_id}" style="position:absolute; inset:0; width:100%; height:100%; object-fit:cover;" loading="lazy">
                </div>
                <div style="padding:12px; text-align:center;">
                    <div style="font-size:14px; font-weight:700; color:var(--text); text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">{html.escape(act.get('name', ''))}</div>
                </div>
            </div>
            '''
        actors_grid_html += '</div>'

    page_body = f'''
    <div class="main" style="padding-top:30px; max-width:1100px; margin:0 auto; padding-left:20px; padding-right:20px;">
        <div style="margin-bottom:20px;">
            <h1 style="font-size:28px; font-weight:900; color:var(--text); margin-bottom:4px;">🎭 Actors Catalog</h1>
            <p style="color:var(--muted); font-size:14px;">Browse verified star profiles and linked content grids.</p>
        </div>
        {admin_header_action}
        {actors_grid_html}
    </div>
    '''
    return build_page("Actors Directory - Fast Finder", page_body, "", "actors", role)

# ─────────────────────────────────────────────────────────
# 🎭 ADMIN VIEW: CREATE ACTOR PROFILE PAGE FORM
# ─────────────────────────────────────────────────────────
@actor_routes.get('/admin/create_actor')
async def create_actor_page(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.HTTPFound('/dashboard')
        
    content = f'''
    <form action="/api/create_actor" method="post" enctype="multipart/form-data">
        <input type="text" name="name" placeholder="Actor Full Name (e.g., Shah Rukh Khan)" required>
        <textarea name="bio" placeholder="Actor Biography / Details..." style="width:100%; background:var(--bg3); border:1px solid var(--border); padding:12px; color:var(--text); border-radius:6px; min-height:100px; outline:none; margin-bottom:15px; font-family:inherit;" required></textarea>
        
        <div class="scard-label" style="margin-bottom:4px; color:var(--muted);">Search Tags (Comma Separated)</div>
        <input type="text" name="tags" placeholder="e.g. SRK, Shahrukh, King Khan" style="width:100%; background:var(--bg3); border:1px solid var(--border); padding:12px; color:var(--text); border-radius:6px; margin-bottom:15px; outline:none;">

        <div class="scard-label" style="margin-bottom:8px; color:var(--muted);">Actor Profile Photo</div>
        <input type="file" name="photo" accept="image/*" required style="padding:10px 0; color:var(--text);">
        
        <button class="submit-btn" type="submit" style="background:var(--accent); color:#fff; width:100%; padding:14px; border:0; border-radius:6px; font-weight:700; cursor:pointer; margin-top:10px;">Create Actor Profile</button>
    </form>
    <div style="margin-top:15px; text-align:center;"><a href="/actors" style="color:var(--muted); text-decoration:none; font-size:13px;">← Back to Actors Catalog</a></div>
    '''
    return build_page("Create Actor Profile", form_wrapper("Add New Actor", content, req.query.get('err',''), req.query.get('msg','')), "login-bg", "actors", role)

# ─────────────────────────────────────────────────────────
# ⚙️ ADMIN API: UPLOAD TO TG & SAVE TO MONGO
# ─────────────────────────────────────────────────────────
@actor_routes.post('/api/create_actor')
async def api_create_actor(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403)
        
    try:
        reader = await req.multipart()
        name, bio, tags_raw, image_bytes = None, None, "", None
        while True:
            part = await reader.next()
            if part is None: break
            if part.name == 'name': name = (await part.read()).decode().strip()
            elif part.name == 'bio': bio = (await part.read()).decode().strip()
            elif part.name == 'tags': tags_raw = (await part.read()).decode().strip()
            elif part.name == 'photo': image_bytes = await part.read()

        if not name or not bio or not image_bytes:
            return web.HTTPFound('/admin/create_actor?err=All fields are required!')

        tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]

        with io.BytesIO(image_bytes) as img_buffer:
            img_buffer.name = f"{name.replace(' ', '_')}.jpg"
            msg = await temp.BOT.send_photo(chat_id=BIN_CHANNEL, photo=img_buffer)

        if not msg or not msg.photo: return web.HTTPFound('/admin/create_actor?err=Telegram Upload Failed!')
        tg_photo_id = msg.photo.sizes[-1].file_id if hasattr(msg.photo, "sizes") and msg.photo.sizes else msg.photo.file_id
        
        actor_doc = {
            "name": name,
            "bio": bio,
            "tags": tags_list,
            "photo_url": f"TG_ID:{tg_photo_id}",
            "social_links": {"instagram": "", "youtube": "", "twitter": ""},
            "gallery": [],
            "created_at": time.time()
        }
        await actors.insert_one(actor_doc)
        return web.HTTPFound('/actors?msg=Actor Profile created successfully!')
    except Exception as e:
        return web.HTTPFound(f'/admin/create_actor?err=Server Error: {str(e)}')

# ─────────────────────────────────────────────────────────
# 🖼️ ZERO-RAM GENERAL PHOTO ENGINE
# ─────────────────────────────────────────────────────────
@actor_routes.get('/api/actor/photo')
async def get_actor_photo(req):
    actor_id = req.query.get("id")
    img_index = req.query.get("gallery_idx")
    if not actor_id: return web.Response(status=400)
    
    try:
        doc = await actors.find_one({"_id": ObjectId(actor_id)})
        if not doc: return web.Response(status=404)
        
        if img_index is not None:
            idx = int(img_index)
            raw_url = doc.get("gallery", [])[idx]
        else:
            raw_url = doc.get("photo_url")
            
        if not raw_url or not raw_url.startswith("TG_ID:"): return web.Response(status=404)
        tg_id = raw_url.replace("TG_ID:", "")
        
        file_data = await temp.BOT.download_media(tg_id, in_memory=True)
        if not file_data: return web.Response(status=404)
        
        body_bytes = file_data.getvalue()
        file_data.close()
        del file_data
        
        headers = {"Cache-Control": "public, max-age=31536000, immutable", "Content-Disposition": 'inline; filename="photo.jpg"'}
        return web.Response(body=body_bytes, content_type="image/jpeg", headers=headers)
    except Exception: return web.Response(status=500)
    finally: gc.collect()

# ─────────────────────────────────────────────────────────
# 🌐 PUBLIC VIEW: ACTOR PROFILE MASTER INTERFACE
# ─────────────────────────────────────────────────────────
@actor_routes.get('/actor/{id}')
async def actor_profile_display(req):
    role, _ = await get_auth(req)
    if not role: return web.HTTPFound('/login')
    
    try:
        actor_id = req.match_info['id']
        actor = await actors.find_one({"_id": ObjectId(actor_id)})
        if not actor: return web.Response(text="Actor Not Found", status=404)
    except: return web.Response(text="Invalid ID", status=400)
        
    actor_name = actor["name"]
    tags_list = actor.get("tags", [])
    social = actor.get("social_links", {"instagram": "", "youtube": "", "twitter": ""})
    gallery_list = actor.get("gallery", [])
    
    tags_chips_html = '<div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:8px;">'
    for tag in tags_list:
        tags_chips_html += f'<span style="background:var(--bg3); border:1px solid var(--border); color:var(--muted); font-size:11px; padding:3px 8px; border-radius:4px; font-weight:600;">#{html.escape(tag)}</span>'
    tags_chips_html += '</div>'

    social_html = '<div style="display:flex; gap:12px; margin-top:12px; flex-wrap:wrap;">'
    if social.get("instagram"): social_html += f'<a href="{html.escape(social["instagram"])}" target="_blank" style="background:#ff007f; color:#fff; padding:6px 14px; border-radius:6px; text-decoration:none; font-size:12px; font-weight:700;">📸 Instagram</a>'
    if social.get("youtube"): social_html += f'<a href="{html.escape(social["youtube"])}" target="_blank" style="background:#ff0000; color:#fff; padding:6px 14px; border-radius:6px; text-decoration:none; font-size:12px; font-weight:700;">📺 YouTube</a>'
    if social.get("twitter"): social_html += f'<a href="{html.escape(social["twitter"])}" target="_blank" style="background:#1da1f2; color:#fff; padding:6px 14px; border-radius:6px; text-decoration:none; font-size:12px; font-weight:700;">🐦 Twitter / X</a>'
    social_html += '</div>'

    gallery_grid_html = ""
    if role == 'admin':
        gallery_grid_html += f'''
        <div style="background:var(--card); border:1px dashed var(--border); padding:20px; border-radius:8px; text-align:center; margin-bottom:20px;">
            <form action="/api/actor/gallery_upload" method="post" enctype="multipart/form-data" style="margin:0;">
                <input type="hidden" name="actor_id" value="{actor_id}">
                <label style="background:var(--accent); color:#fff; padding:10px 20px; border-radius:6px; font-weight:700; cursor:pointer; font-size:13px; display:inline-block;">
                    📂 Add Image to Gallery
                    <input type="file" name="gallery_img" accept="image/*" style="display:none;" onchange="this.form.submit()">
                </label>
            </form>
        </div>
        '''
    if not gallery_list:
        gallery_grid_html += '<div style="color:var(--muted); text-align:center; padding:40px;"> 🖼️ Gallery is empty. Upload images to show here.</div>'
    else:
        gallery_grid_html += '<div class="gallery-grid">'
        for i in range(len(gallery_list)):
            # ✅ गैलरी इमेज डिलीट और फुल स्क्रीन लाइटबॉक्स ट्रिगर सपोर्ट
            del_btn = f'<button class="gallery-del-btn" onclick="deleteGalleryImage(\'{actor_id}\', {i}, event)">🗑️ Delete</button>' if role == 'admin' else ""
            gallery_grid_html += f'''
            <div class="gallery-item-wrap" onclick="openLightbox('/api/actor/photo?id={actor_id}&gallery_idx={i}')">
                <img src="/api/actor/photo?id={actor_id}&gallery_idx={i}" class="gallery-item" loading="lazy">
                {del_btn}
            </div>
            '''
        gallery_grid_html += '</div>'

    admin_actions_html = ""
    if role == 'admin':
        admin_actions_html = f'''
        <div style="display:flex; gap:10px; margin-top:10px; flex-wrap:wrap;">
            <button onclick="openActorEditModal()" style="background:var(--bg4); border:1px solid var(--border); color:var(--text); padding:8px 16px; border-radius:6px; font-size:12px; font-weight:700; cursor:pointer;">✏️ Edit Profile & Socials</button>
            <button onclick="deleteActorProfile('{actor_id}')" style="background:rgba(160,8,8,.78); border:1px solid rgba(229,9,20,.45); color:#fff; padding:8px 16px; border-radius:6px; font-size:12px; font-weight:700; cursor:pointer;">🗑️ Delete Profile</button>
            <label style="background:var(--bg3); border:1px dashed var(--border); color:var(--text); padding:7px 14px; border-radius:6px; font-size:12px; font-weight:700; cursor:pointer; display:inline-block;">
                📸 Change Avatar
                <input type="file" id="avatarUpdateInput" accept="image/*" style="display:none;" onchange="updateActorAvatar('{actor_id}')">
            </label>
        </div>
        '''
        
    tags_json_payload = html.escape(json.dumps(tags_list))
    safe_bio = html.escape(actor.get("bio", ""))

    tab_engine_ui = f'''
    <style>
        .actor-tab-bar {{ display: flex; gap: 10px; border-bottom: 2px solid var(--border); margin-bottom: 25px; }}
        .actor-tab {{ background: transparent; border: none; color: var(--muted); padding: 12px 20px; font-size: 15px; font-weight: 700; cursor: pointer; transition: 0.2s; position: relative; font-family: inherit; }}
        .actor-tab.active {{ color: var(--text) !important; }}
        .actor-tab.active::after {{ content: ''; position: absolute; bottom: -2px; left: 0; right: 0; height: 2px; background: var(--accent); }}
        .actor-panel {{ display: none; }}
        .actor-panel.active {{ display: block !important; }}
        
        /* ── गैलरी नोड विथ डिलीट ओवरले ── */
        .gallery-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 14px; }}
        @media(min-width:600px) {{ .gallery-grid {{ grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); }} }}
        .gallery-item-wrap {{ position: relative; border-radius: 8px; overflow: hidden; border: 1px solid var(--border); aspect-ratio: 1; cursor: pointer; }}
        .gallery-item {{ width: 100%; height: 100%; object-fit: cover; transition: transform 0.2s; }}
        .gallery-item-wrap:hover .gallery-item {{ transform: scale(1.04); }}
        .gallery-del-btn {{ position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%); background: rgba(160,8,8,.85); border: 1px solid var(--accent); color: #fff; padding: 4px 10px; border-radius: 4px; font-size: 10px; font-weight: 700; cursor: pointer; z-index: 5; opacity: 0; transition: opacity 0.15s; }}
        .gallery-item_wrap:hover .gallery-del-btn {{ opacity: 1; }}
        
        /* ── फुलस्क्रीन लाइटबॉक्स ── */
        .lightbox {{ position: fixed; inset: 0; background: rgba(0,0,0,.92); backdrop-filter: blur(15px); z-index: 99999; display: none; align-items: center; justify-content: center; opacity: 0; transition: opacity 0.2s ease; }}
        .lightbox.open {{ display: flex; opacity: 1; }}
        .lightbox-img {{ max-width: 92%; max-height: 88vh; object-fit: contain; border-radius: 6px; box-shadow: 0 10px 40px rgba(0,0,0,.8); transform: scale(.95); transition: transform .2s cubic-bezier(.4,0,.2,1); }}
        .lightbox.open .lightbox-img {{ transform: scale(1); }}
        .lightbox-close {{ position: absolute; top: 20px; right: 25px; background: none; border: none; color: #fff; font-size: 32px; cursor: pointer; opacity: .7; }}
        .lightbox-close:hover {{ opacity: 1; }}

        /* ── डैशबोर्ड की प्रीमियम रिस्पॉन्सिव ग्रिड ── */
        .search-zone-actor {{ padding: 16px 0 0 0; }}
        .search-row1-actor {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }}
        .search-row2-actor {{ display: flex; align-items: center; justify-content: flex-start; gap: 10px; margin-bottom: 16px; }}
        @media(min-width:768px){{
          .search-zone-actor {{ display: flex; align-items: center; gap: 10px; flex-wrap: nowrap; padding-bottom: 16px; }}
          .search-row1-actor {{ flex: 1; margin-bottom: 0; }}
          .search-row2-actor {{ margin-bottom: 0; flex-shrink: 0; }}
        }}
        .search-wrap-actor {{ flex: 1; min-width: 0; display: flex; align-items: center; background: var(--bg3); border: 1.5px solid var(--border); border-radius: 12px; padding: 0 6px 0 18px; gap: 8px; overflow: hidden; min-height: 38px; }}
        .search-input-actor {{ flex: 1; min-width: 0; width: 100%; background: transparent; border: none; outline: none; color: var(--text); font-size: 14px; font-weight: 600; padding: 6px 0; font-family: inherit; }}
        .search-input-actor::placeholder {{ color: var(--muted); font-weight: 400; }}
        .search-btn-actor {{ flex-shrink: 0; background: var(--accent); color: #fff; border: none; border-radius: 12px; padding: 0 20px; height: 38px; font-size: 14px; font-weight: 700; cursor: pointer; white-space: nowrap; transition: transform .15s, background .15s; }}
        .search-btn-actor:hover {{ background: var(--accent-hover); transform: scale(1.03); }}
        
        .cdd-wrap-actor {{ flex: 0 1 auto; min-width: 0; position: relative; user-select: none; }}
        .cdd-btn-actor {{ width: auto; background: var(--bg3); color: var(--text); border: 1.5px solid var(--border); border-radius: 999px; padding: 8px 28px 8px 14px; font-size: 11px; font-weight: 700; cursor: pointer; font-family: inherit; box-sizing: border-box; display: inline-flex; align-items: center; gap: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; transition: border-color .15s; }}
        .cdd-btn-actor:hover, .cdd-btn-actor.open {{ border-color: var(--accent); }}
        .cdd-arrow-actor {{ position: absolute; right: 12px; top: 50%; transform: translateY(-50%); pointer-events: none; font-size: 9px; color: var(--muted); transition: transform .2s; }}
        .cdd-btn-actor.open + .cdd-arrow-actor {{ transform: translateY(-50%) rotate(180deg); }}
        .cdd-menu-actor {{ position: absolute; top: calc(100% + 7px); left: 50%; transform: translateX(-50%); min-width: max-content; background: var(--bg2); border: 1.5px solid var(--border); border-radius: 16px; overflow: hidden; z-index: 9999; box-shadow: 0 8px 32px rgba(0,0,0,.45); display: none; }}
        .cdd-item-actor {{ display: flex; align-items: center; gap: 10px; padding: 11px 14px; font-size: 12px; font-weight: 700; color: var(--text); cursor: pointer; transition: background .12s; border-bottom: 1px solid var(--border); }}
        .cdd-item-actor:last-child {{ border-bottom: none; }}
        .cdd-item-actor:hover {{ background: var(--bg3); }}
        .cdd-item-actor.selected {{ color: var(--accent); }}
        .cdd-radio-actor {{ width: 16px; height: 16px; border-radius: 50%; border: 2px solid var(--border); margin-left: auto; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }}
        .cdd-item-actor.selected .cdd-radio-actor {{ border-color: var(--accent); }}
        .cdd-radio-dot-actor {{ width: 6px; height: 6px; border-radius: 50%; background: var(--accent); display: none; }}
        .cdd-item-actor.selected .cdd-radio-dot-actor {{ display: block; }}

        .res-grid {{ display: grid; grid-template-columns: 1fr; gap: 4px; margin-bottom: 24px; }}
        @media(min-width:600px){{ .res-grid {{ grid-template-columns: repeat(3, 1fr); gap: 14px; }} }}
        .file-card {{ background: var(--card); border-radius: 6px; overflow: hidden; border: 1px solid var(--border); transition: transform .22s cubic-bezier(.4,0,.2,1),box-shadow .22s; cursor: pointer; }}
        .file-card:hover {{ transform: translateY(-4px); border-color: rgba(229,9,20,.4); box-shadow: 0 14px 36px rgba(0,0,0,.6); }}
        .poster-box {{ position: relative; padding-top: 56.25%; background: var(--bg3); overflow: hidden; }}
        .fc-poster {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 0.25s ease-in-out; }}
        .fc-poster.loaded {{ opacity: 1; }}
        
        .poster-top {{ position: absolute; top: 0; left: 0; right: 0; display: flex; align-items: center; gap: 5px; padding: 8px; z-index: 3; }}
        .type-chip {{ background: rgba(0,0,0,.72); backdrop-filter: blur(8px); color: #fff; border-radius: 5px; padding: 3px 8px; font-size: 10px; font-weight: 800; border: 1px solid rgba(255,255,255,.14); }}
        .size-chip {{ background: rgba(0,0,0,.60); backdrop-filter: blur(8px); color: #e0e0e0; border-radius: 5px; padding: 3px 8px; font-size: 10px; font-weight: 600; border: 1px solid rgba(255,255,255,.08); }}
        .source-pill {{ margin-left: auto; border-radius: 20px; padding: 3px 8px; font-size: 9px; font-weight: 700; display: inline-flex; align-items: center; gap: 4px; backdrop-filter: blur(8px); }}
        .source-pill.primary {{ background: #14532d; color: #4ade80; border: 1px solid #22c55e; }}
        .source-pill.cloud {{ background: #1e3a5f; color: #93c5fd; border: 1px solid #60a5fa; }}
        .source-pill.archive {{ background: #7c2d12; color: #fdba74; border: 1px solid #fb923c; }}
        .source-dot {{ width: 5px; height: 5px; border-radius: 50%; background: currentColor; }}
        
        .fc-body {{ padding: 10px 11px 12px; }}
        .fc-name {{ color: var(--text); font-size: 12.5px; font-weight: 600; line-height: 1.45; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; text-decoration: none; cursor: pointer; }}
        .fc-name:hover {{ color: var(--accent); text-decoration: underline; }}
        .res-grid.mode-none .poster-box {{ display: none; }}
        
        .pagination {{ display: flex; align-items: center; justify-content: center; gap: 12px; margin-top: 20px; }}
        .pg-btn {{ background: var(--bg4); color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: 8px 18px; font-size: 12px; font-weight: 700; cursor: pointer; transition: background .15s; }}
        .pg-btn:disabled {{ opacity: .45; cursor: not-allowed; }}
        .pg-btn:not(:disabled):hover {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
        .pg-info {{ color: var(--muted); font-size: 12px; font-weight: 600; }}
        .spin-wrap {{ display: flex; flex-direction: column; align-items: center; gap: 16px; padding: 60px 20px; color: var(--muted); grid-column: 1/-1; }}
        .spinner {{ width: 36px; height: 36px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin .8s linear infinite; }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        .empty {{ text-align: center; padding: 60px 20px; color: var(--muted); grid-column: 1/-1; }}
    </style>

    <div class="main" style="padding-top:30px; max-width:1100px; margin: 0 auto; padding-left:20px; padding-right:20px;">
        <div style="margin-bottom:15px;"><a href="/actors" style="color:var(--muted); text-decoration:none; font-size:14px; font-weight:700;">← Back to Catalog</a></div>
        
        <div style="display:flex; gap:25px; background:var(--card); border:1px solid var(--border); padding:25px; border-radius:12px; margin-bottom:35px; flex-wrap:wrap;">
            <div style="width:160px; height:220px; background:var(--bg3); border-radius:8px; overflow:hidden; border:1px solid var(--border); flex-shrink:0;">
                <img id="actorMasterAvatarImage" src="/api/actor/photo?id={actor_id}" style="width:100%; height:100%; object-fit:cover;">
            </div>
            <div style="flex:1; min-width:300px; display:flex; flex-direction:column; justify-content:center;">
                <h1 style="font-size:32px; font-weight:900; color:var(--text); margin-bottom:2px;">{html.escape(actor_name)}</h1>
                {tags_chips_html}
                {social_html}
                {admin_actions_html}
            </div>
        </div>

        <div class="actor-tab-bar">
            <button class="actor-tab active" onclick="switchActorTab(event, 'tab-info')">ℹ️ Info</button>
            <button class="actor-tab" onclick="switchActorTab(event, 'tab-video')">🎬 Video</button>
            <button class="actor-tab" onclick="switchActorTab(event, 'tab-gallery')">🖼️ Gallery</button>
        </div>

        <div id="tab-info" class="actor-panel active">
            <div style="background:var(--card); border:1px solid var(--border); padding:25px; border-radius:8px; line-height:1.7; color:var(--text); font-size:15px; white-space:pre-line;">
                {safe_bio}
            </div>
        </div>

        <div id="tab-video" class="actor-panel">
            <div class="search-zone-actor">
                <div class="search-row1-actor">
                    <div class="search-wrap-actor">
                        <input type="text" id="actor_movie_q" value="" placeholder="Search inside actor movies..." class="search-input-actor">
                    </div>
                    <button onclick="resetActorSearchPage(); triggerActorSearchAjax()" class="search-btn-actor">Search</button>
                </div>
                <div class="search-row2-actor">
                    <div class="cdd-wrap-actor">
                        <div class="cdd-btn-actor" id="cddColBtnActor" onclick="toggleActorCdd('col', event)">
                            <span id="cddColLabelActor">📂 All Collections</span>
                        </div>
                        <span class="cdd-arrow-actor">&#9660;</span>
                        <div class="cdd-menu-actor" id="cddColMenuActor">
                            <div class="cdd-item-actor selected" data-val="all" onclick="pickActorCol('all','📂 All Collections',this,event)">📂 All Collections<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
                            <div class="cdd-item-actor" data-val="primary" onclick="pickActorCol('primary','🟢 Primary',this,event)">🟢 Primary<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
                            <div class="cdd-item-actor" data-val="cloud" onclick="pickActorCol('cloud','🔵 Cloud',this,event)">🔵 Cloud<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
                            <div class="cdd-item-actor" data-val="archive" onclick="pickActorCol('archive','🟠 Archive',this,event)">🟠 Archive<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
                        </div>
                    </div>

                    <div class="cdd-wrap-actor">
                        <div class="cdd-btn-actor" id="cddModeBtnActor" onclick="toggleActorCdd('mode', event)">
                            <span id="cddModeLabelActor">🖼️ Original TG Thumb</span>
                        </div>
                        <span class="cdd-arrow-actor">&#9660;</span>
                        <div class="cdd-menu-actor" id="cddModeMenuActor">
                            <div class="cdd-item-actor selected" data-val="tg" onclick="pickActorMode('tg','🖼️ Original TG Thumb',this,event)">🖼️ Original TG Thumb<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
                            <div class="cdd-item-actor" data-val="none" onclick="pickActorMode('none','⚡ Text Only (Fastest)',this,event)">⚡ Text Only (Fastest)<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
                        </div>
                    </div>
                </div>
            </div>

            <div id="actor_video_results" class="res-grid"></div>
            
            <div class="pagination" id="actor_page_box" style="display:none;">
                <button class="pg-btn" id="actor_pBtn" onclick="actorPagePrev()" disabled>Previous</button>
                <span class="pg-info" id="actor_pgInfo">Page 1</span>
                <button class="pg-btn" id="actor_nBtn" onclick="actorPageNext()">Next</button>
            </div>
        </div>

        <div id="tab-gallery" class="actor-panel">
            {gallery_grid_html}
        </div>
    </div>

    <div id="actorLightboxModal" class="lightbox" onclick="closeLightbox()">
        <button class="lightbox-close" onclick="closeLightbox()">&times;</button>
        <img id="lightboxTargetImg" class="lightbox-img" src="" onclick="event.stopPropagation()">
    </div>

    <input type="hidden" id="actor_master_tags_payload" value="{tags_json_payload}">

    <div class="edit-modal" id="actorEditModal" onclick="if(event.target===this)closeActorEditModal()">
        <div class="em-card" style="max-width:550px; background: var(--card); border:1px solid var(--border); padding:25px; border-radius:12px;">
            <button class="em-close" onclick="closeActorEditModal()" style="position:absolute; top:15px; right:20px; background:none; border:none; color:var(--muted); font-size:24px; cursor:pointer;">&#10005;</button>
            <div class="em-title" style="font-size:18px; font-weight:700; margin-bottom:20px; color:var(--text);">✏️ Edit Actor Profile Matrix</div>
            <form action="/api/actor/update_profile" method="post">
                <input type="hidden" name="actor_id" value="{actor_id}">
                
                <div class="scard-label">Actor Full Name</div>
                <input type="text" name="name" value="{html.escape(actor_name)}" class="em-input" style="width:100%; background:var(--bg); border:1px solid var(--border); padding:12px; color:var(--text); margin-bottom:15px; border-radius:6px;" required>
                
                <div class="scard-label">Biography Details</div>
                <textarea name="bio" class="em-input" style="width:100%; background:var(--bg); border:1px solid var(--border); min-height:120px; font-family:inherit; padding:10px; line-height:1.5; color:var(--text); margin-bottom:15px; border-radius:6px;" required>{safe_bio}</textarea>
                
                <div class="scard-label">Search Tags (Comma Separated)</div>
                <input type="text" name="tags" value="{html.escape(', '.join(tags_list))}" placeholder="e.g. SRK, Shahrukh, King Khan" class="em-input" style="width:100%; background:var(--bg); border:1px solid var(--border); padding:12px; color:var(--text); margin-bottom:15px; border-radius:6px;">

                <div class="em-title" style="font-size:14px; margin-top:15px; margin-bottom:10px; color:var(--text);">🌐 Social Media Channels Matrix</div>
                
                <div class="scard-label">Instagram Link</div>
                <input type="url" name="insta" value="{html.escape(social.get('instagram',''))}" placeholder="https://instagram.com/..." class="em-input" style="width:100%; background:var(--bg); border:1px solid var(--border); padding:12px; color:var(--text); margin-bottom:15px; border-radius:6px;">
                
                <div class="scard-label">YouTube Channel Link</div>
                <input type="url" name="yt" value="{html.escape(social.get('youtube',''))}" placeholder="https://youtube.com/..." class="em-input" style="width:100%; background:var(--bg); border:1px solid var(--border); padding:12px; color:var(--text); margin-bottom:15px; border-radius:6px;">
                
                <div class="scard-label">Twitter / X Profile Link</div>
                <input type="url" name="twitter" value="{html.escape(social.get('twitter',''))}" placeholder="https://x.com/..." class="em-input" style="width:100%; background:var(--bg); border:1px solid var(--border); padding:12px; color:var(--text); margin-bottom:20px; border-radius:6px;">
                
                <button class="em-save-btn" type="submit" style="width:100%; background:var(--accent); color:#fff; border:none; padding:14px; font-weight:700; border-radius:6px; cursor:pointer; font-size:15px;">Save Changes & Sync Grid</button>
            </form>
        </div>
    </div>

    <script>
        var actCurPage = 1, actOffset = 0, actNextOffset = "";
        var actLimit = 21;
        var actorDefaultName = "{html.escape(actor_name)}";
        var actCol = "all", actMode = "tg";

        function closeActorCdds(){{
            document.getElementById('cddColMenuActor').style.display='none';
            document.getElementById('cddColBtnActor').classList.remove('open');
            document.getElementById('cddModeMenuActor').style.display='none';
            document.getElementById('cddModeBtnActor').classList.remove('open');
        }}
        function toggleActorCdd(which, e){{
            if(e){{e.stopPropagation();}}
            var menuId = which === 'col' ? 'cddColMenuActor' : 'cddModeMenuActor';
            var btnId = which === 'col' ? 'cddColBtnActor' : 'cddModeBtnActor';
            var otherId = which === 'col' ? 'cddModeMenuActor' : 'cddColMenuActor';
            var otherBtnId = which === 'col' ? 'cddModeBtnActor' : 'cddColBtnActor';
            
            var menu = document.getElementById(menuId);
            var btn = document.getElementById(btnId);
            var isOpen = menu.style.display === 'block';
            
            document.getElementById(otherId).style.display = 'none';
            document.getElementById(otherBtnId).classList.remove('open');
            
            if(isOpen){{ menu.style.display = 'none'; btn.classList.remove('open'); }}
            else{{ menu.style.display = 'block'; btn.classList.add('open'); }}
        }}
        function pickActorCol(val, label, el, e){{
            if(e){{e.stopPropagation();}}
            actCol = val;
            document.getElementById('cddColLabelActor').textContent = label;
            document.querySelectorAll('#cddColMenuActor .cdd-item-actor').forEach(function(i){{i.classList.remove('selected');}});
            el.classList.add('selected');
            closeActorCdds();
            resetActorSearchPage();
            triggerActorSearchAjax();
        }}
        function pickActorMode(val, label, el, e){{
            if(e){{e.stopPropagation();}}
            actMode = val;
            document.getElementById('cddModeLabelActor').textContent = label;
            document.querySelectorAll('#cddModeMenuActor .cdd-item-actor').forEach(function(i){{i.classList.remove('selected');}});
            el.classList.add('selected');
            closeActorCdds();
            resetActorSearchPage();
            triggerActorSearchAjax();
        }}
        document.addEventListener('click', function(){{ closeActorCdds(); }});

        /* ── लाइटबॉक्स इंजन ── */
        function openLightbox(src) {{
            var lb = document.getElementById('actorLightboxModal');
            document.getElementById('lightboxTargetImg').src = src;
            lb.style.display = 'flex';
            setTimeout(function(){{ lb.classList.add('open'); }}, 10);
        }}
        function closeLightbox() {{
            var lb = document.getElementById('actorLightboxModal');
            lb.classList.remove('open');
            setTimeout(function(){{ lb.style.display = 'none'; }}, 200);
        }}

        function switchActorTab(evt, tabId) {{
            var panels = document.querySelectorAll('.actor-panel');
            for (var i = 0; i < panels.length; i++) {{ panels[i].classList.remove('active'); }}
            var tabs = document.querySelectorAll('.actor-tab');
            for (var j = 0; j < tabs.length; j++) {{ tabs[j].classList.remove('active'); }}
            
            document.getElementById(tabId).classList.add('active');
            evt.currentTarget.classList.add('active');
            if(tabId === 'tab-video' && document.getElementById('actor_video_results').innerHTML === "") {{
                triggerActorSearchAjax();
            }}
        }}

        function openActorEditModal() {{ document.getElementById('actorEditModal').classList.add('open'); }}
        function closeActorEditModal() {{ document.getElementById('actorEditModal').classList.remove('open'); }}
        function resetActorSearchPage() {{ actCurPage = 1; actOffset = 0; }}

        async function triggerActorSearchAjax() {{
            var typedQ = document.getElementById('actor_movie_q').value.trim();
            var q = typedQ || actorDefaultName; 
            var grid = document.getElementById('actor_video_results');
            
            grid.className = 'res-grid mode-' + actMode;
            grid.innerHTML = '<div class="spin-wrap"><div class="spinner"></div><span>Filtering Cross-Network Matrix...</span></div>';
            
            try {{
                var targetUrl = '/api/actor/search?q=' + encodeURIComponent(q) + '&offset=' + actOffset + '&col=' + actCol + '&mode=' + actMode + '&id={actor_id}';
                var r = await fetch(targetUrl);
                var d = await r.json();
                if(!d.results || !d.results.length) {{
                    grid.innerHTML = '<div class="empty"><p>No video assets matching filters found inside database.</p></div>';
                    document.getElementById('actor_page_box').style.display = 'none';
                    return;
                }}
                var h = '';
                d.results.forEach(function(f) {{
                    var sc = (f.source || 'primary').toLowerCase();
                    var posterHtml = '';
                    if(actMode !== 'none') {{
                        posterHtml = '<div class="poster-box">' +
                            '<img src="'+f.tg_thumb+'" class="fc-poster" onload="this.classList.add(\\'loaded\\')" loading="lazy">' +
                            '<div class="poster-top">' +
                                '<span class="type-chip">'+f.type.toUpperCase()+'</span>' +
                                '<span class="size-chip">'+f.size+'</span>' +
                                '<span class="source-pill '+sc+'"><span class="source-dot"></span>'+sc.toUpperCase()+'</span>' +
                            '</div>' +
                        '</div>';
                    }} else {{
                        posterHtml = '<div class="fc-text-info">' +
                            '<span class="tc-type">'+f.type.toUpperCase()+'</span>' +
                            '<span class="tc-size">'+f.size+'</span>' +
                            '<span class="source-pill '+sc+'" style="margin-left:auto"><span class="source-dot"></span>'+sc.toUpperCase()+'</span>' +
                        '</div>';
                    }}
                    h += '<div class="file-card" onclick="window.open(\\''+f.watch+'\\',\\'_blank\\')">' + 
                        posterHtml + 
                        '<div class="fc-body">' +
                            '<div class="fc-name">'+f.name+'</div>' +
                        '</div>' +
                    '</div>';
                }});
                grid.innerHTML = h;
                actNextOffset = d.next_offset;
                document.getElementById('actor_page_box').style.display = 'flex';
                document.getElementById('actor_pBtn').disabled = (actOffset === 0);
                document.getElementById('actor_nBtn').disabled = !actNextOffset;
                document.getElementById('actor_pgInfo').textContent = 'Page ' + actCurPage;
            }} catch(e) {{
                grid.innerHTML = '<div class="empty"><p>Matrix pipeline sync timeout error.</p></div>';
            }}
        }}

        // ✅ लाइव फोटो रीलोडर: बिना पेज रिफ्रेश किए ब्राउज़र में अवतार तुरंत बदलेगा
        async function updateActorAvatar(actorId) {{
            var fileInput = document.getElementById('avatarUpdateInput');
            if(!fileInput.files || !fileInput.files[0]) return;
            
            var formData = new FormData();
            formData.append('actor_id', actorId);
            formData.append('photo', fileInput.files[0]);
            
            try {{
                var r = await fetch('/api/actor/update_avatar', {{ method: 'POST', body: formData }});
                var d = await r.json();
                if(d.success) {{
                    var timestamp = new Date().getTime();
                    document.getElementById('actorMasterAvatarImage').src = '/api/actor/photo?id=' + actorId + '&t=' + timestamp;
                    alert("Profile photo updated successfully!");
                }} else {{
                    alert(d.error || "Upload failed!");
                }}
            }} catch(e) {{ alert("Network update error!"); }}
        }}

        // 🗑️ गैलरी इमेज डिलीट इंजन
        async function deleteGalleryImage(actorId, idx, e) {{
            if(e) {{ e.stopPropagation(); }}
            if(!confirm("Delete this photo from gallery permanently?")) return;
            try {{
                var r = await fetch('/api/actor/gallery_delete', {{
                    method: 'POST',
                    body: JSON.stringify({{ actor_id: actorId, index: idx }}),
                    headers: {{ 'Content-Type': 'application/json' }}
                }});
                var d = await r.json();
                if(d.success) {{
                    alert("Image removed from gallery!");
                    window.location.reload();
                }} else {{ alert(d.error || "Delete failed!"); }}
            }} catch(e) {{ alert("Network deletion error!"); }}
        }}

        async function deleteActorProfile(id) {{
            if (!confirm("Are you sure you want to permanently delete this actor profile?")) return;
            try {{
                var r = await fetch('/api/actor/delete?id=' + id, {{ method: 'POST' }});
                var d = await r.json();
                if (d.success) {{
                    alert("Profile deleted successfully!");
                    window.location.href = '/actors';
                }} else {{ alert(d.error || "Deletion failed!"); }}
            }} catch(e) {{ alert("Network communication error!"); }}
        }}

        function actorPageNext() {{ if(actNextOffset) {{ actCurPage++; actOffset = actNextOffset; triggerActorSearchAjax(); window.scrollTo(0,350); }} }}
        function actorPagePrev() {{ if(actCurPage > 1) {{ actCurPage--; actOffset = Math.max(0, actOffset - actLimit); triggerActorSearchAjax(); window.scrollTo(0,350); }} }}
        
        document.getElementById('actor_movie_q').addEventListener('keydown', function(e) {{ if(e.key === 'Enter') {{ resetActorSearchPage(); triggerActorSearchAjax(); }} }});
    </script>
    '''
    return build_page(f"{actor_name} - Profile Matrix", tab_engine_ui, "", "actors", role)

# ─────────────────────────────────────────────────────────
# ⚙️ ADMIN API: DYNAMIC AJAX OR SEARCH PIPELINE FOR ACTOR PAGE
# ─────────────────────────────────────────────────────────
@actor_routes.get('/api/actor/search')
async def api_actor_search_handler(req):
    role, _ = await get_auth(req)
    if not role: return web.json_response({"error": "Unauthorized"}, status=403)
    
    actor_id = req.query.get("id")
    q_custom = req.query.get("q", "").strip()
    off = req.query.get("offset", "0")
    col = req.query.get("col", "all").lower()
    mode = req.query.get("mode", "tg").lower()
    
    if not actor_id: return web.json_response({"results": []})
    try: off = max(0, int(off))
    except: off = 0
        
    actor = await actors.find_one({"_id": ObjectId(actor_id)})
    if not actor: return web.json_response({"results": []})
    
    search_query = q_custom if q_custom else actor["name"]
    tags_list = actor.get("tags", [])
    
    lim = 21
    
    all_m, next_offset = await get_actor_search_results(
        search_query, tags_list, max_results=lim, offset=off, collection_type=col
    )
    
    results_list = []
    for d in all_m:
        fid = d.get("file_ref") or d.get("_id")
        db_id = d.get("_id")
        source_col = d.get("source_col", "primary")
        
        raw_thumb = d.get("thumb_url", "")
        v_salt = raw_thumb[-8:] if (raw_thumb and raw_thumb.startswith("TG_ID:")) else "0"
        tg_thumb = f"/api/thumb?file_id={db_id}&col={source_col}&v={v_salt}"
        
        results_list.append({
            "file_id": db_id,
            "name": d.get("file_name", "Unknown File"),
            "size": get_size(d.get("file_size", 0)),
            "type": d.get("file_type", "document").upper(),
            "source": source_col.capitalize(),
            "tg_thumb": tg_thumb,
            "watch": f"/setup_stream?file_id={fid}&mode=watch"
        })
        
    return web.json_response({"results": results_list, "next_offset": next_offset})

# ─────────────────────────────────────────────────────────
# ⚙️ ADMIN API: UPDATE PROFILE DETAILS & SOCIAL MEDIA CHANNELS
# ─────────────────────────────────────────────────────────
@actor_routes.post('/api/actor/update_profile')
async def api_actor_update_profile(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403)
    
    d = await req.post()
    actor_id = d.get('actor_id')
    name = d.get('name', '').strip()
    bio = d.get('bio', '').strip()
    tags_raw = d.get('tags', '').strip()
    insta = d.get('insta', '').strip()
    yt = d.get('yt', '').strip()
    twitter = d.get('twitter', '').strip()
    
    if not actor_id or not name or not bio: return web.HTTPFound('/actors?err=Missing assets data')
    
    tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]
    
    update_doc = {
        "name": name,
        "bio": bio,
        "tags": tags_list,
        "social_links": {"instagram": insta, "youtube": yt, "twitter": twitter}
    }
    
    await actors.update_one({"_id": ObjectId(actor_id)}, {"$set": update_doc})
    return web.HTTPFound(f'/actor/{actor_id}?msg=Profile and Social Networks synced successfully!')

# ─────────────────────────────────────────────────────────
# 🖼️ ADMIN API: LIVE UPDATE ACTOR AVATAR
# ─────────────────────────────────────────────────────────
@actor_routes.post('/api/actor/update_avatar')
async def api_actor_update_avatar(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403)
    
    try:
        data = await req.post()
        actor_id = data.get("actor_id")
        photo_part = data.get("photo")
        
        if not actor_id or not photo_part:
            return web.json_response({"success": False, "error": "Invalid assets data"})
            
        image_bytes = photo_part.file.read()
        
        with io.BytesIO(image_bytes) as img_buffer:
            img_buffer.name = f"avatar_{actor_id}_{int(time.time())}.jpg"
            msg = await temp.BOT.send_photo(chat_id=BIN_CHANNEL, photo=img_buffer)
            
        if not msg or not msg.photo:
            return web.json_response({"success": False, "error": "Telegram upload failed"})
            
        tg_photo_id = msg.photo.sizes[-1].file_id if hasattr(msg.photo, "sizes") and msg.photo.sizes else msg.photo.file_id
        
        await actors.update_one({"_id": ObjectId(actor_id)}, {"$set": {"photo_url": f"TG_ID:{tg_photo_id}"}})
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)})

# ─────────────────────────────────────────────────────────
# 🖼️ ADMIN API: UPLOAD NATIVE IMAGE TO GALLERY
# ─────────────────────────────────────────────────────────
@actor_routes.post('/api/actor/gallery_upload')
async def api_actor_gallery_upload(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403)
    
    try:
        reader = await req.multipart()
        actor_id, image_bytes = None, None
        while True:
            part = await reader.next()
            if part is None: break
            if part.name == 'actor_id': actor_id = (await part.read()).decode().strip()
            elif part.name == 'gallery_img': image_bytes = await part.read()
            
        if not actor_id or not image_bytes: return web.HTTPFound('/actors?err=Assets reading packet failure')
        
        with io.BytesIO(image_bytes) as img_buffer:
            img_buffer.name = f"gallery_{actor_id}_{int(time.time())}.jpg"
            msg = await temp.BOT.send_photo(chat_id=BIN_CHANNEL, photo=img_buffer)
            
        if not msg or not msg.photo: return web.HTTPFound(f'/actor/{actor_id}?err=Telegram Node Gallery Upload Failed')
        tg_photo_id = msg.photo.sizes[-1].file_id if hasattr(msg.photo, "sizes") and msg.photo.sizes else msg.photo.file_id
        
        await actors.update_one({"_id": ObjectId(actor_id)}, {"$push": {"gallery": f"TG_ID:{tg_photo_id}"}})
        return web.HTTPFound(f'/actor/{actor_id}?msg=New portrait uploaded successfully to star gallery!')
    except Exception as e:
        return web.HTTPFound(f'/actors?err=System core crash: {str(e)}')

# ─────────────────────────────────────────────────────────
# 🗑️ ADMIN API: DELETE SINGLE GALLERY IMAGE FROM ARRAY
# ─────────────────────────────────────────────────────────
@actor_routes.post('/api/actor/gallery_delete')
async def api_actor_gallery_delete(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403)
    
    try:
        body = await req.json()
        actor_id = body.get("actor_id")
        idx = body.get("index")
        
        actor = await actors.find_one({"_id": ObjectId(actor_id)})
        if not actor or "gallery" not in actor:
            return web.json_response({"success": False, "error": "Actor not found"})
            
        gallery = actor["gallery"]
        if 0 <= idx < len(gallery):
            del gallery[idx]
            await actors.update_one({"_id": ObjectId(actor_id)}, {"$set": {"gallery": gallery}})
            return web.json_response({"success": True})
        return web.json_response({"success": False, "error": "Index out of bounds"})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)})

# ─────────────────────────────────────────────────────────
# 🗑️ ADMIN API: DELETE ACTOR PROFILE COMPLETELY
# ─────────────────────────────────────────────────────────
@actor_routes.post('/api/actor/delete')
async def api_actor_delete(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403)
    
    actor_id = req.query.get("id")
    if not actor_id: return web.json_response({"error": "Missing ID"}, status=400)
    
    try:
        await actors.delete_one({"_id": ObjectId(actor_id)})
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
