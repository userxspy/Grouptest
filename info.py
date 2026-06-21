import re
import os
import logging
from os import environ
from Script import script

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 🧠 HELPERS & BOOLEAN PARSERS (RAM Safe)
# ─────────────────────────────────────────────
def is_enabled(key, default=False):
    val = environ.get(key, str(default)).lower()
    if val in ("true", "1", "yes", "y", "enable"): return True
    if val in ("false", "0", "no", "n", "disable"): return False
    logger.error(f"❌ {key} has invalid value")
    exit(1)

def is_valid_ip(ip):
    ip_pattern = (
        r'\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    )
    return re.match(ip_pattern, ip) is not None

def get_channels(env_var):
    val = environ.get(env_var, "").replace(",", " ").strip()
    if not val: return []
    # ✅ टेलीग्राम आईडी के ऋणात्मक चिह्नों (-100) को सुरक्षित पार्स करने के लिए न्यूमेरिक चेक
    return [int(x) for x in val.split() if x.replace("-", "").isnumeric()]

# ─────────────────────────────────────────────
# 🤖 BOT CREDENTIALS
# ─────────────────────────────────────────────
API_ID = int(environ.get("API_ID", "0"))
API_HASH = environ.get("API_HASH", "")
BOT_TOKEN = environ.get("BOT_TOKEN", "")

if not API_ID or not API_HASH or not BOT_TOKEN:
    logger.error("❌ API_ID / API_HASH / BOT_TOKEN missing")
    exit(1)

BOT_ID = int(BOT_TOKEN.split(":")[0])
PORT = int(environ.get("PORT", 8080)) # कोएब (Koyeb) के डायनेमिक बाइंडिंग के लिए 8080 यूनिवर्सल बेस्ट पोर्ट है

# ─────────────────────────────────────────────
# 👑 ADMINS & SECURITY
# ─────────────────────────────────────────────
ADMINS = environ.get("ADMINS", "")
if not ADMINS:
    logger.error("❌ ADMINS environment variable missing")
    exit(1)
ADMINS = [int(x) for x in ADMINS.split() if x.isnumeric()]

# ─────────────────────────────────────────────
# 🖼️ IMAGES & CORE AI KEYS
# ─────────────────────────────────────────────
PICS = environ.get("PICS", "https://i.postimg.cc/8C15CQ5y/1.png").split()

# ─────────────────────────────────────────────
# 📢 STORAGE & MICRO-ROUTING CHANNELS SYNC
# ─────────────────────────────────────────────
PRIMARY_CHANNEL = get_channels("PRIMARY_CHANNEL")
CLOUD_CHANNEL = get_channels("CLOUD_CHANNEL")
ARCHIVE_CHANNEL = get_channels("ARCHIVE_CHANNEL")

LOG_CHANNEL = int(environ.get("LOG_CHANNEL", "0"))
if not LOG_CHANNEL:
    logger.error("❌ LOG_CHANNEL missing")
    exit(1)

# पुराना मिक्स्ड बिन चैनल (फाइलों के डिफ़ॉल्ट डाउनलोड के लिए)
BIN_CHANNEL = int(environ.get("BIN_CHANNEL", "0"))
if not BIN_CHANNEL:
    logger.error("❌ BIN_CHANNEL missing")
    exit(1)

# ⚡ [NEW FEATURE] नए पृथक media और थंबनेल स्टोरेज चैनल्स
# (यदि पर्यावरण वेरिएबल्स सेट नहीं हैं, तो यह सुरक्षित रूप से BIN_CHANNEL पर फॉल-बैक करेगा)
ACTOR_STORAGE_CHANNEL = int(environ.get("ACTOR_STORAGE_CHANNEL", BIN_CHANNEL))
THUMBNAIL_STORAGE_CHANNEL = int(environ.get("THUMBNAIL_STORAGE_CHANNEL", BIN_CHANNEL))

# ─────────────────────────────────────────────
# 🗄️ DATABASE CONNECTION URL
# ─────────────────────────────────────────────
DATABASE_URL = environ.get("DATABASE_URL", "")
DATABASE_NAME = environ.get("DATABASE_NAME", "Cluster0")

if not DATABASE_URL:
    logger.error("❌ DATABASE_URL missing")
    exit(1)

# ─────────────────────────────────────────────
# ⚙️ GLOBAL SETTINGS & ADAPTIVE RESULTS SYNC
# ─────────────────────────────────────────────
TIME_ZONE = environ.get("TIME_ZONE", "Asia/Kolkata")

# बोट के बटन्स (12) और वेब/मिनी ऐप (21) की स्वतंत्र रिज़ल्ट लिमिट
MAX_BOT_RESULTS = int(environ.get("MAX_BOT_RESULTS", 12)) 
MAX_WEB_RESULTS = int(environ.get("MAX_WEB_RESULTS", 21)) 

# ⚡ [NEW VARIABLE] डिफ़ॉल्ट सर्च मोड (group या single) - मल्टी-क्वालिटी बंडलिंग के लिए
DEFAULT_VIEW_MODE = environ.get("DEFAULT_VIEW_MODE", "group").lower()

# ─────────────────────────────────────────────
# ⏳ TIMERS ENGINE (सेंट्रलाइज्ड कस्टमाइजेबल टाइमर्स)
# ─────────────────────────────────────────────
DELETE_TIME = int(environ.get("DELETE_TIME", 300)) 
PM_FILE_DELETE_TIME = int(environ.get("PM_FILE_DELETE_TIME", 600)) 
PREMIUM_REMINDER_BUSY_GAP = int(environ.get("PREMIUM_REMINDER_BUSY_GAP", 60)) 
THUMB_DELETE_TIME = int(environ.get("THUMB_DELETE_TIME", 5))

# ─────────────────────────────────────────────
# ⚡ SPEED, BUFFER & ANTI-SPAM THRU LMT
# ─────────────────────────────────────────────
SEARCH_LIMIT_PER_SEC = int(environ.get("SEARCH_LIMIT_PER_SEC", 2))
MAX_THUMB_CACHE = int(environ.get("MAX_THUMB_CACHE", 500))

# ─────────────────────────────────────────────
# 🧩 FEATURE FLAGS
# ─────────────────────────────────────────────
USE_CAPTION_FILTER = is_enabled("USE_CAPTION_FILTER", True)
AUTO_DELETE = is_enabled("AUTO_DELETE", True)
PROTECT_CONTENT = is_enabled("PROTECT_CONTENT", False)
SPELL_CHECK = is_enabled("SPELL_CHECK", True)
IS_STREAM = is_enabled("IS_STREAM", True)
IS_PREMIUM = is_enabled("IS_PREMIUM", True)

# ─────────────────────────────────────────────
# 📝 TEXT FILE CAPTION TEMPLATE
# ─────────────────────────────────────────────
FILE_CAPTION = environ.get("FILE_CAPTION", script.FILE_CAPTION)

# ─────────────────────────────────────────────
# 👑 STREAM ENGINE & WEB APP DOMAIN CONVERTER
# ─────────────────────────────────────────────
URL = environ.get("URL", "").strip()
if not URL:
    logger.error("❌ Web URL environment variable missing")
    exit(1)

# WebApp-Compatible HTTPS URL Auto-Builder Engine
if URL.startswith("http://"):
    logger.warning(f"⚠️ URL is HTTP, auto-converting to HTTPS: {URL}")
    URL = "https://" + URL[len("http://"):]

if URL.startswith("https://"):
    if not URL.endswith("/"): URL += "/"
elif is_valid_ip(URL):
    URL = f"https://{URL}/"
    logger.warning("⚠️ IP-based URL detected. Telegram WebApp requires a valid HTTPS domain.")
else:
    if not URL.startswith("https://") and "." in URL:
        URL = "https://" + URL.rstrip("/") + "/"
        logger.info(f"✅ Auto-Formatted incomplete URL string to valid domain structure: {URL}")
    else:
        logger.error("❌ Invalid URL - must start with https:// for Telegram Mini App support")
        exit(1)

# ─────────────────────────────────────────────
# 💎 PREMIUM PAYMENT CONFIGURATIONS
# ─────────────────────────────────────────────
REACTIONS = environ.get("REACTIONS", "👍 ❤️ 🔥 😍 🤝").split()

PRE_DAY_AMOUNT = int(environ.get("PRE_DAY_AMOUNT", 10))
UPI_ID = environ.get("UPI_ID", "").strip()
UPI_NAME = environ.get("UPI_NAME", "").strip()

RECEIPT_SEND_USERNAME = environ.get("RECEIPT_SEND_USERNAME", "").strip()
if RECEIPT_SEND_USERNAME and not RECEIPT_SEND_USERNAME.startswith("@") and not RECEIPT_SEND_USERNAME.isnumeric():
    RECEIPT_SEND_USERNAME = "@" + RECEIPT_SEND_USERNAME

if not UPI_ID or not UPI_NAME:
    logger.warning("⚠️ UPI_ID or UPI_NAME is missing. Payment flow might get interrupted.")
