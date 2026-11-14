"""
================================================================================
          ✨ GEMINI TELEGRAM USERBOT & AUTOMATION SUITE
================================================================================
Shaxsiyati: Qat'iy Google Gemini AI (Multimodal) + Avtomatik Google Maps Reklama
Kutubxonalar: Telethon, Rich, Google-GenAI, Selenium, Python-Dotenv
Interfeys: Cyan, Bright Blue va Bright Green palitrali Rich CMD interfeysi
Asosiy buyruqlar:
  • .start reklama [soha/turli xil] [soni] — Google Maps'dan veb-sayti yo'q restoran
                                               yoki turli xil bizneslarni topib reklama yuborish
  • .stop reklama                — Faol reklama tarqatishni to'xtatish
  • .reklama <raqam/username>    — Bitta manzilga samimiy taklif yuborish
  • .mijoz                       — Chatni mijoz sifatida saqlash
  • .mijozlar / .papka           — Barcha mijozlarni 'Mijozlar' papkasiga yig'ish
================================================================================
"""

import os
import re
import sys
import math
import time
import json
import random
import asyncio
from datetime import datetime
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Telethon kutubxonalari
from telethon import TelegramClient, events, Button, utils as tl_utils
from telethon.sessions import StringSession
from telethon.tl.types import User, InputPhoneContact
from telethon.tl import types as tl_types, functions as tl_functions
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.errors import FloodWaitError, PeerFloodError

# Rich — Estetik va rang-barang terminal interfeysi
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box

# Google Gemini rasmiy SDK
from google import genai
from google.genai import types
from google.genai.errors import APIError

# Selenium — Google Maps tahlili uchun
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bot_ui import register_bot_handlers, _build_dashboard, main_reply_keyboard

# UTF-8 va Windows konsol sozlamalari
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

console = Console()
load_dotenv()
if os.path.exists(".env.txt"):
    load_dotenv(".env.txt", override=True)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
TELEGRAM_SESSION = os.getenv("TELEGRAM_SESSION", "").strip()
BOT_SESSION = os.getenv("BOT_SESSION", "").strip()
ALERT_CHANNEL = os.getenv("ALERT_CHANNEL", "").strip()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", BASE_DIR).strip() or BASE_DIR
os.makedirs(DATA_DIR, exist_ok=True)

if not API_ID or not API_HASH:
    console.print("[bold red]❌ XATO:[/bold red] .env faylida API_ID yoki API_HASH topilmadi!")
    sys.exit(1)

if not GEMINI_API_KEY:
    console.print("[bold red]❌ XATO:[/bold red] .env faylida GEMINI_API_KEY topilmadi!")
    sys.exit(1)

API_ID = int(API_ID)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

SESSION_NAME = os.path.join(BASE_DIR, "gemini_userbot_session")
_user_session = StringSession(TELEGRAM_SESSION) if TELEGRAM_SESSION else SESSION_NAME
client = TelegramClient(
    _user_session,
    API_ID,
    API_HASH,
    connection_retries=-1,
    retry_delay=5,
    auto_reconnect=True,
)

# Foydalanuvchi taqdim etgan Google Maps koordinatasi (Andijon hududi)
DEFAULT_LAT = 40.7639683
DEFAULT_LON = 72.3623834

# ==============================================================================
# 1. GEMINI SHAXSIYATI VA TIZIM KO'RSATMALARI
# ==============================================================================
GEMINI_SYSTEM_INSTRUCTION = (
    "Sen — Google tomonidan yaratilgan rasmiy 'Gemini' sun'iy intellekt assistentisan. "
    "Sening isming qat'iy ravishda: Gemini. (Hech qachon o'zingni boshqa nom bilan atama). "
    "Uslubing: Intellektual, yuqori darajada professional, muloyim, aniq va tahliliy. "
    "Foydalanuvchining barcha savollariga (dasturlash, fan, biznes, matnlar tahlili, hujjatlar va multimedia) "
    "keng qamrovli va eng yuqori sifatda yordam ber. "
    "Foydalanuvchi qaysi tilda so'rasa (o'zbek, rus, ingliz va h.k.), aynan shu tilda mukammal javob qaytar."
)

CLIENT_SALES_SYSTEM_PROMPT = (
    "Sen Muhammadrizosan — O'zbekistondagi veb-dasturchi va reklama video tayyorlaydigan mutaxassissan. "
    "Hozir sen Telegramda mijoz (restoran, kafe yoki boshqa biznes egasi) bilan oddiy shaxsiy chatda yozishyapsan. "
    "QAT'IY QOIDALAR:\n"
    "- Hech qachon o'zingni AI, bot yoki Gemini deb aytma!\n"
    "- Hech qachon emoji belgilar (1️⃣, 💡, 🔥, 🚀, ✅, 🎁 va h.k.), jirniy yulduzchalar (**) yoki reklama broshyurasiga o'xshagan sarlavhali ro'yxatlar ishlatma!\n"
    "- Xuddi tirik inson Telegramda qo'lda yozayotgandek oddiy, samimiy, hurmatli va jonli o'zbek tilida gaplash.\n\n"
    "Mijoz sening taklifingga qiziqib 'nimalar qilib bera olasiz?', 'batafsil tushuntiring', 'narxi qancha?' "
    "yoki shunga o'xshash savol bermoqda. Uning sohasiga qarab oddiy va hayotiy qilib tushuntir:\n"
    "- Veb-sayt: restoran/kafe bo'lsa rasmli onlayn menyu, stollarga QR-kod, stol band qilish va yetkazib berishga buyurtma to'g'ri Telegramga tushishi; "
    "boshqa biznes (klinika, salon, servis, do'kon) bo'lsa xizmatlar va narxlar sahifasi, rasmlar va mijozlarning onlayn yozilib/buyurtma qoldirishi.\n"
    "- Google xarita va qidiruvdan odamlar osongina topib kelishi.\n"
    "- Xohlasalar Instagram, TikTok va Telegram uchun reklama video ham tayyorlab berishing.\n"
    "- Narx haqida so'rasa: avval hech qanday to'lovsiz ularning nomiga mos bepul namuna (ko'rinish) tayyorlab ko'rsatishingni, yoqsa hamyonbop narxda kelishishingizni, yoqmasa majburiy emasligini ayt.\n\n"
    "Javobing o'qishga yengil, 2-3 qisqa abzas bo'lsin va oxirida 'Agar xohlasangiz, hoziroq bepul namuna ko'rinishini tayyorlab ko'rsataymi?' deb muloyim so'ra."
)

BOT_TAG = "✨ **Gemini:**\n\n"
chat_sessions = {}
sent_message_ids = set()

config_state = {
    "model": DEFAULT_MODEL,
    "autoreply_pm": False,
    "campaign_running": False,
    "auto_reply": True,
    "auto_folder": True,
    "delay_min": 14.0,
    "delay_max": 24.0,
    "lat": DEFAULT_LAT,
    "lon": DEFAULT_LON,
    "location_label": "Andijon",
    "alert_channel": ALERT_CHANNEL,
}

SETTINGS_FILE = os.path.join(DATA_DIR, "bot_settings.json")
ENV_FILE = os.path.join(BASE_DIR, ".env")
bot_ctx = {"bot_client": None, "notify_bot_owner": None}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for k in ("model", "auto_reply", "auto_folder", "delay_min", "delay_max", "lat", "lon", "location_label", "alert_channel"):
                if k in saved:
                    config_state[k] = saved[k]
        except Exception:
            pass

def save_settings():
    try:
        payload = {k: config_state[k] for k in ("model", "auto_reply", "auto_folder", "delay_min", "delay_max", "lat", "lon", "location_label", "alert_channel")}
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def save_env_key(key: str, value: str):
    """Yangi kalitni (masalan BOT_TOKEN) .env fayliga xavfsiz saqlaydi."""
    try:
        lines = []
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        updated = False
        new_lines = []
        for ln in lines:
            if ln.strip().startswith(f"{key}="):
                new_lines.append(f"{key}={value}")
                updated = True
            else:
                new_lines.append(ln)
        if not updated:
            new_lines.append(f"{key}={value}")
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n")
    except Exception:
        pass

def parse_location_input(raw_text: str):
    """Google Maps havolasi yoki '40.76, 72.36' matnidan lat, lon ajratadi."""
    m = re.search(r"@?(-?\d{1,2}\.\d{3,}),\s*(-?\d{1,3}\.\d{3,})", raw_text)
    if m:
        lat = float(m.group(1))
        lon = float(m.group(2))
        return lat, lon, f"{lat:.4f}, {lon:.4f}"
    return None, None, None

load_settings()

# Reklama yuborilgan mijozlar va tekshirilgan raqamlar bazasi (ad_leads.json)
AD_LEADS_FILE = os.path.join(DATA_DIR, "ad_leads.json")

def load_ad_leads():
    if os.path.exists(AD_LEADS_FILE):
        try:
            with open(AD_LEADS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "contacted_phones" not in data:
                    data["contacted_phones"] = []
                return data
        except Exception:
            return {"contacted_phones": []}
    return {"contacted_phones": []}

def save_ad_leads(leads):
    try:
        with open(AD_LEADS_FILE, "w", encoding="utf-8") as f:
            json.dump(leads, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

ad_leads = load_ad_leads()

CLIENT_FILES_DIR = os.path.join(DATA_DIR, "mijozlar_fayllari")
os.makedirs(CLIENT_FILES_DIR, exist_ok=True)


# ==============================================================================
# 2. RICH CMD VIZUALIZATSIYA FUNKSIYALARI
# ==============================================================================
def print_banner():
    ascii_art = r"""
   ______ ______ __  ___ ____ _   __ ____
  / ____// ____//  |/  //  _// | / //  _/
 / / __ / __/  / /|_/ / / / /  |/ / / /  
/ /_/ // /___ / /  / /_/ / / /|  /_/ /   
\____//_____//_/  /_//___//_/ |_//___/   
    """
    banner_text = Text(ascii_art, style="bold bright_cyan")
    subtitle = Text(
        "✨ Advanced AI Telegram Userbot & Google Maps Automation\nPowered by Google Gemini, Selenium & Telethon",
        style="italic bright_blue",
        justify="center"
    )
    panel_content = Align.center(Text.assemble(banner_text, "\n", subtitle))
    console.print(Panel(
        panel_content,
        border_style="bright_cyan",
        box=box.ROUNDED,
        padding=(1, 2)
    ))

def print_user_info(me, model_name: str):
    table = Table(
        title="[bold bright_cyan]TIZIM STATUSI VA PROFIL[/bold bright_cyan]",
        border_style="bright_blue",
        box=box.ROUNDED,
        header_style="bold cyan"
    )
    table.add_column("Parametr", style="bright_cyan", width=22)
    table.add_column("Qiymat / Holat", style="bright_white")

    username = f"@{me.username}" if me.username else "[grey50]Mavjud emas[/grey50]"
    phone = me.phone if me.phone else "[grey50]Yashirin[/grey50]"

    table.add_row("👤 Telegram Egasi", f"[bold bright_white]{me.first_name}[/bold bright_white] ({username})")
    table.add_row("📱 Telefon Raqam", f"[cyan]+{phone}[/cyan]")
    table.add_row("🧠 AI Dvigateli", f"[bold bright_cyan]Google {model_name}[/bold bright_cyan]")
    table.add_row("🗺️ Maps Qidiruvi", "[bold bright_green]● TAYYOR (Chrome Headless)[/bold bright_green]")
    table.add_row("⚡ Tizim Holati", "[bold bright_green]● ONLINE (FAOL ISHLAMOQDA)[/bold bright_green]")
    table.add_row("🛠️ Buyruqlar", "[bright_blue].start reklama[/bright_blue], [bright_blue].stop reklama[/bright_blue], [bright_cyan].reklama[/bright_cyan], [bright_cyan].mijoz[/bright_cyan], [bright_cyan].mijozlar[/bright_cyan], [bright_cyan].ai[/bright_cyan]")

    console.print(table)
    console.print()

def log_event(event_type: str, target: str, status: str, details: str):
    current_time = datetime.now().strftime("%H:%M:%S")
    table = Table(show_header=False, box=box.SIMPLE_HEAVY, border_style="grey37")
    table.add_column("Vaqt", style="grey70", width=10)
    table.add_column("Hodisa", style="bold bright_blue", width=20)
    table.add_column("Target / Chat", style="bright_cyan", width=24)
    table.add_column("Holat", style="bold bright_green", width=16)
    table.add_column("Tafsilot", style="bright_white")

    table.add_row(
        f"[grey50]{current_time}[/grey50]",
        event_type,
        target,
        status,
        details
    )
    console.print(table)


# ==============================================================================
# 3. GOOGLE MAPS QIDIRUV MODULI (Restoran va turli xil bizneslarni topish)
# ==============================================================================
DEFAULT_MULTI_CATEGORIES = [
    "restoran",
    "kafe",
    "stomatologiya",
    "go'zallik saloni",
    "avtoservis",
    "o'quv markaz",
    "klinika",
    "do'kon",
]

LOCATION_HINTS = {
    "toshkent", "tashkent", "samarqand", "samarkand", "buxoro", "bukhara",
    "farg'ona", "fargona", "fergana", "namangan", "andijon", "andijan",
    "xorazm", "urganch", "navoiy", "qarshi", "nukus", "termiz",
    "jizzax", "guliston", "qo'qon", "qoqon", "kokand", "marg'ilon", "margilon",
    "o'zbekiston", "ozbekiston", "uzbekistan",
}

MULTI_CATEGORY_KEYWORDS = (
    "turli xil", "turli hil", "turlixil", "turlihil",
    "har xil", "har hil", "hammasi", "barchasi", "aralash", "mix",
)

def normalize_phone(phone: str) -> str:
    """Telefon raqamini toza +998... formatiga keltiradi"""
    digits = "".join(c for c in phone if c.isdigit() or c == "+")
    if digits and not digits.startswith("+"):
        digits = "+" + digits
    return digits

def is_food_category(category: str = None) -> bool:
    """Berilgan soha restoran/ovqatlanish yo'nalishi ekanligini aniqlaydi."""
    if not category:
        return True
    cl = category.lower()
    food_words = (
        "restoran", "restaurant", "kafe", "cafe", "oshxona", "choyxona",
        "fast food", "fastfood", "pizza", "pizzeria", "burger", "lavash",
        "shirinlik", "bakery", "milliy taom", "sushi", "kebab", "bar", "grill",
    )
    return any(w in cl for w in food_words)

# --- Google Maps natijalarini filtrlash: noto'g'ri joylarni o'tkazib yuborish ---

# Aniq brend/do'konlar va aloqasi yo'q joylar nomlari
EXCLUDED_BRAND_NAMES = {
    "apple", "apple store", "samsung", "xiaomi", "huawei", "honor", "oppo",
    "vivo", "realme", "oneplus", "google store", "microsoft", "lenovo", "asus",
    "acer", "dell", "hp store", "lg", "sony", "nokia", "motorola", "tecno",
    "infinix", "itel", "iphone", "istore", "ishop", "ipoint",
    "mediapark", "media park", "texnomart", "texno mart", "elmakon",
    "olx", "uzum", "wildberries", "ozon",
    "mcdonalds", "mcdonald's", "kfc", "burger king", "subway", "starbucks",
    "dominos", "domino's", "papa johns", "papa john's", "baskin robbins",
    "coca cola", "coca-cola", "pepsi",
    "megaplanet", "mega planet", "makro", "macro", "korzinka", "havas",
    "beeline", "ucell", "mobiuz", "humans", "uzmobile",
    "apteka", "pharmacy", "dorixona",
    "masjid", "mosque", "maktab", "school", "universitet", "university",
    "bank", "ipoteka",
}

# Soha => joyning Google Maps sahifasida ko'rinadigan teglar ro'yxati
# (masalan: restoran -> "Restaurant", stomatologiya -> "Dentist" yoki "Dental clinic")
CATEGORY_RELEVANCE_TAGS = {
    "restoran": ("restaurant", "restoran", "eatery", "dining", "ovqat", "taom",
                 "cuisine", "national food", "milliy", "grill", "bbq"),
    "kafe": ("cafe", "coffee", "kafe", "kofe", "qahva", "qahvaxona", "tea",
             "choy", "bakery", "dessert", "pastry"),
    "stomatologiya": ("dentist", "dental", "stomatolog", "tish", "orthodont"),
    "go'zallik saloni": ("beauty", "salon", "spa", "nail", "hair", "barber",
                         "go'zallik", "sartarosh", "stilist", "makeup", "cosmet"),
    "avtoservis": ("auto", "car", "avto", "repair", "servis", "service", "wash",
                   "yuvish", "mechanic", "tire", "shinomontaj", "shin"),
    "o'quv markaz": ("education", "learning", "course", "training", "school",
                     "o'quv", "oquv", "kurs", "til", "language", "academy",
                     "akadem", "center", "markaz", "study", "tutor"),
    "klinika": ("clinic", "hospital", "medical", "health", "doctor", "physician",
                "klinika", "shifoxona", "shifokor", "tibbiy", "med"),
    "sartaroshxona": ("barber", "hair", "salon", "sartarosh", "stilist", "beauty"),
    "mebel": ("furniture", "mebel", "divan", "shkaf", "home goods", "interior"),
    "mehmonxona": ("hotel", "hostel", "guest house", "mehmonxona", "inn", "resort", "lodging"),
    "fitnes": ("fitness", "gym", "sport", "workout", "fitnes", "zal", "trener"),
    "gul do'koni": ("flower", "florist", "gul", "bouquet", "buket"),
    "foto studiya": ("photo", "video", "studio", "foto", "studiya", "camera"),
    "do'kon": ("shop", "store", "market", "do'kon", "dokon", "savdo",
               "magazin", "boutique", "retail", "super"),
}

def _extract_maps_category(driver) -> str:
    """Google Maps joy sahifasidan soha/tur matnini oladi (masalan: 'Restaurant', 'Dental clinic')."""
    try:
        # Asosiy soha tugmasi (odatda joylashuv ostida ko'rinadi)
        cat_els = driver.find_elements(By.CSS_SELECTOR, "button[jsaction*='category']")
        if cat_els:
            return cat_els[0].text.strip().lower()
        # Zaxira: birinchi jslog bilan soha ko'rsatilishi
        cat_els2 = driver.find_elements(By.CSS_SELECTOR, "[class*='fontBodyMedium'] span[jstcache]")
        for el in cat_els2[:5]:
            txt = el.text.strip().lower()
            if txt and len(txt) < 50 and not txt.startswith("+") and not txt[0].isdigit():
                return txt
    except Exception:
        pass
    return ""

def _is_excluded_brand(name: str) -> bool:
    """Bizga aloqasi yo'q brend yoki zanjir do'kon ekanligini tekshiradi."""
    nl = name.lower().strip()
    for brand in EXCLUDED_BRAND_NAMES:
        if brand in nl:
            return True
    return False

def _is_relevant_to_category(name: str, maps_category_text: str, search_category: str) -> bool:
    """
    Topilgan joyning nomi yoki Google Maps turi qidirilayotgan sohaga tegishli ekanligini tekshiradi.
    Agar soha bo'yicha teglar aniqlanmagan bo'lsa, avtomatik o'tkazib yuboramiz.
    """
    # Shahar nomi va umumiy so'zlarni olib tashlab, sof soha so'zini ajratamiz
    search_key = search_category.lower().strip()
    for loc in LOCATION_HINTS:
        search_key = search_key.replace(loc, "").strip()

    tags = None
    for cat_key, cat_tags in CATEGORY_RELEVANCE_TAGS.items():
        if cat_key in search_key or search_key in cat_key:
            tags = cat_tags
            break

    # Agar ushbu soha uchun teglar mavjud bo'lmasa, filtrsiz o'tkazamiz
    if not tags:
        return True

    # Joyning nomi yoki Google Maps sohasida kamida bitta teg bor-yo'qligini tekshiramiz
    combined_text = f"{name} {maps_category_text}".lower()
    return any(tag in combined_text for tag in tags)

def expand_search_categories(query: str) -> list[str]:
    """
    Foydalanuvchi kiritgan so'rovni Google Maps qidiruv sohalariga ajratadi:
    masalan: 'restoran', 'stomatologiya', 'turli xil' yoki 'restoran, kafe, klinika'.
    """
    raw = (query or "restoran").strip()
    if "," in raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        expanded = []
        for p in parts:
            expanded.extend(expand_search_categories(p))
        return expanded or ["restoran"]

    lower = raw.lower()
    matched_kw = next((kw for kw in MULTI_CATEGORY_KEYWORDS if kw in lower), None)
    if matched_kw:
        extra_context = lower.replace(matched_kw, " ").strip()
        extra_context = " ".join(extra_context.split())
        if extra_context:
            return [f"{extra_context} {cat}" for cat in DEFAULT_MULTI_CATEGORIES]
        return list(DEFAULT_MULTI_CATEGORIES)

    return [raw]

def scrape_google_maps_no_website(query: str = "restoran", max_results: int = 5, skip_phones: set = None):
    """
    Google Maps orqali restoran yoki turli xil bizneslarni ko'rib chiqadi,
    veb-sayti YO'Q va telefon raqami BOR joylarni topib qaytaradi.
    """
    if skip_phones is None:
        skip_phones = set()

    sub_queries = expand_search_categories(query)
    seen_phones = set(skip_phones)
    seen_urls = set()

    opts = ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,800")
    opts.add_argument("--lang=en")
    # ⚡ 10x Tezlashtirish: Rasm, shrift va keraksiz og'ir resurslarni bloklash
    opts.add_argument("--blink-settings=imagesEnabled=false")
    opts.add_argument("--disable-remote-fonts")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-background-networking")
    opts.add_argument("--disk-cache-size=1")
    opts.page_load_strategy = "eager"  # DOMContentLoaded tayyor bo'lishi bilan ishlaydi

    chrome_bin = os.getenv("CHROME_BIN") or next(
        (p for p in ("/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome") if os.path.exists(p)),
        None,
    )
    if chrome_bin:
        opts.binary_location = chrome_bin

    driver_bin = os.getenv("CHROMEDRIVER_PATH") or next(
        (p for p in ("/usr/bin/chromedriver", "/usr/lib/chromium/chromedriver") if os.path.exists(p)),
        None,
    )
    if driver_bin:
        driver = webdriver.Chrome(service=ChromeService(driver_bin), options=opts)
    else:
        driver = webdriver.Chrome(options=opts)
    found_targets = []
    social_domains = [
        "instagram.com", "t.me", "telegram.me", "facebook.com",
        "fb.com", "youtube.com", "tiktok.com", "vk.com",
    ]

    try:
        # 🍪 Google Cookie Consent bypass (Yevropa / Render serverlari uchun)
        try:
            driver.get("https://www.google.com/robots.txt")
            driver.add_cookie({
                "name": "SOCS",
                "value": "CAISHAgBEhJnd3NfMjAyNDA4MDgtMF9SQzEaAmVuIAEaBgiA_LyaBg",
                "domain": ".google.com",
                "path": "/"
            })
        except Exception:
            pass

        total_cats = len(sub_queries)
        for cat_idx, sub_q in enumerate(sub_queries):
            if len(found_targets) >= max_results:
                break

            remaining_slots = max_results - len(found_targets)
            remaining_cats = total_cats - cat_idx
            cat_limit = min(remaining_slots, max(1, math.ceil(remaining_slots / remaining_cats)))

            has_city = any(loc in sub_q.lower() for loc in LOCATION_HINTS)
            encoded_q = quote_plus(sub_q)
            if has_city:
                url = f"https://www.google.com/maps/search/{encoded_q}?hl=en"
            else:
                cur_lat = float(config_state.get("lat", DEFAULT_LAT))
                cur_lon = float(config_state.get("lon", DEFAULT_LON))
                url = f"https://www.google.com/maps/search/{encoded_q}/@{cur_lat},{cur_lon},13z?hl=en"

            driver.get(url)

            # Agar consent sahifasiga o'tib ketgan bo'lsa, 'Accept all' tugmasini bosish
            if "consent.google" in driver.current_url:
                try:
                    for b in driver.find_elements(By.CSS_SELECTOR, "button"):
                        t = (b.text or "").lower()
                        if any(w in t for w in ["accept", "agree", "alle akzeptieren", "zustimmen", "принять"]):
                            driver.execute_script("arguments[0].click();", b)
                            time.sleep(1.5)
                            break
                except Exception:
                    pass

            try:
                wait = WebDriverWait(driver, 8)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.hfpxzc, a[href*='/maps/place/'], div.Nv2PK, h1")))
            except Exception:
                continue

            # 🔍 Deep Search: Ro'yxatni pastga chuqur aylantirib ko'proq joylarni yuklash
            scroll_rounds = 10 if total_cats <= 2 else 6
            try:
                feed = driver.find_element(By.CSS_SELECTOR, "div[role='feed']")
                for _ in range(scroll_rounds):
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed)
                    time.sleep(0.7)
            except Exception:
                pass

            items = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc, a[href*='/maps/place/']")
            candidates = []
            for item in items:
                name = item.get_attribute("aria-label")
                href = item.get_attribute("href")
                if not name or not href:
                    continue
                if href not in seen_urls:
                    seen_urls.add(href)
                    candidates.append((name, href))
                # 🔍 Deep Search: ko'proq biznes nomzodlarini to'plash
                if len(candidates) >= max(30, cat_limit * 8):
                    break

            # Agar to'g'ridan-to'g'ri bitta joy ochilgan bo'lsa
            if "/maps/place/" in driver.current_url and not candidates:
                try:
                    h1_els = driver.find_elements(By.CSS_SELECTOR, "h1")
                    if h1_els:
                        candidates.append((h1_els[0].text, driver.current_url))
                except Exception:
                    pass

            cat_found = 0
            for name, href in candidates:
                if cat_found >= cat_limit or len(found_targets) >= max_results:
                    break

                # Aniq brend/zanjir do'konlarni darhol o'tkazib yuboramiz
                if _is_excluded_brand(name):
                    continue

                driver.get(href)
                try:
                    # ⚡ Tezkor kutish: h1 yoki telefon bloki chiqishi bilan darhol o'qish (4s o'rniga 2.5s)
                    WebDriverWait(driver, 2.5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "h1, [data-item-id^='phone:tel:']"))
                    )
                    time.sleep(0.2)
                except Exception:
                    continue

                # Google Maps sahifasidagi joy turini o'qiymiz
                maps_cat_text = _extract_maps_category(driver)

                # Qidirilayotgan sohaga tegishli emasligini tekshiramiz
                if not _is_relevant_to_category(name, maps_cat_text, sub_q):
                    continue

                phone = None
                phone_els = driver.find_elements(By.CSS_SELECTOR, "[data-item-id^='phone:tel:']")
                if phone_els:
                    raw_phone = phone_els[0].get_attribute("data-item-id").replace("phone:tel:", "").strip()
                    phone = normalize_phone(raw_phone)

                if not phone or phone in seen_phones:
                    continue

                website = None
                web_els = driver.find_elements(By.CSS_SELECTOR, "[data-item-id='authority']")
                if web_els:
                    website = web_els[0].get_attribute("href") or web_els[0].text

                # Agar haqiqiy veb-sayti bo'lsa (Instagram/Telegramdan tashqari) o'tkazib yuboramiz
                has_real_site = False
                if website:
                    wl = website.lower()
                    if not any(sd in wl for sd in social_domains):
                        has_real_site = True

                if not has_real_site:
                    seen_phones.add(phone)
                    cat_found += 1
                    found_targets.append({
                        "name": name,
                        "phone": phone,
                        "website": website,
                        "maps_url": href,
                        "category": sub_q,
                    })
    finally:
        driver.quit()

    return found_targets


# ==============================================================================
# 4. SAMIMIY VA INSONIY REKLAMA MATNLARI (Spamsiz, tirik odamdek)
# ==============================================================================
def generate_web_ad(
    owner_name: str,
    recipient_title: str = None,
    username: str = None,
    phone: str = None,
    is_maps_restaurant: bool = False,
    business_category: str = None,
) -> str:
    """
    100% oddiy odam yozgandek tabiiy, samimiy va spamsiz taklif matni.
    """
    if (is_maps_restaurant or business_category) and recipient_title:
        opener = random.choice([
            f"Assalomu alaykum! Kechirasiz bezovta qilgan bo'lsam, siz \"{recipient_title}\" admini yoki egasimisiz?",
            f"Assalomu alaykum! Siz \"{recipient_title}\" boshqaruvchisi yoki egasimisiz?",
            f"Assalomu alaykum! Uzr, bezovta qilyapman — siz \"{recipient_title}\" ga mas'ul kishimisiz?",
        ])

        if is_food_category(business_category):
            return (
                f"{opener}\n\n"
                f"Mening ismim {owner_name}, men veb-saytlar yarataman. Bugun onlayn xaritalarda \"{recipient_title}\" ni ko'rib qolib, shaxsan o'zingizga yozayotgandim. "
                f"Hozir ko'pchilik yaxshi ovqatlanish joyi qidirganda avval Google'dan qaraydi — agar shaxsiy saytingiz ham bo'lsa, mijozlar telefonidan taomlar rasmi, narxlari va menyuni darrov ko'rib, ikkilanmasdan sizlarga kelishadi yoki onlayn stol band qilib buyurtma berishadi.\n\n"
                f"Xohlasangiz, shunday qulay va chiroyli veb-sayt qilib berishim mumkin, yo'q deyishga shoshilmang. "
                f"Agar faqat sayt yetarli emas desangiz, hatto mijoz jalb qiladigan chiroyli reklama video ham tayyorlab bera olaman.\n\n"
                f"Bu sizga mutlaqo majburiy emas, xohlagan paytingizda bemalol rad etishingiz mumkin. Qiziq bo'lsa shu yerga javob yozib qo'ysangiz bas."
            )

        soha_label = business_category.strip() if business_category else "xizmat"
        return (
            f"{opener}\n\n"
            f"Mening ismim {owner_name}, men veb-saytlar yarataman. Bugun onlayn xaritalarda \"{recipient_title}\" ({soha_label}) ni ko'rib qolib, shaxsan o'zingizga yozayotgandim. "
            f"Hozir odamlar biror xizmat yoki mutaxassis qidirganda ko'pincha Google orqali izlashadi — agar o'zingizning saytingiz bo'lsa, mijozlar xizmatlaringiz, narxlar va rasmlaringizni bir joyda ko'rib, ishonch bilan sizlarga yozilishi yoki buyurtma qoldirishi osonlashadi.\n\n"
            f"Xohlasangiz, faoliyatingizga mos chiroyli veb-sayt qilib berishim mumkin, yo'q deyishga shoshilmang. "
            f"Agar sayt yetarli emas desangiz, hatto sifatli reklama video ham tayyorlab bera olaman.\n\n"
            f"Bu sizga mutlaqo majburiy emas, xohlagan paytingizda bemalol rad etishingiz mumkin. Qiziq bo'lsa shu yerga yozib qo'ysangiz bo'ldi."
        )

    # Oddiy .reklama buyrug'i uchun tirik odamdek tabiiy matn
    if recipient_title:
        greeting = f"Assalomu alaykum, siz {recipient_title}misiz?"
    else:
        greeting = "Assalomu alaykum! Kechirasiz bezovta qilgan bo'lsam."

    return (
        f"{greeting}\n\n"
        f"Mening ismim {owner_name}, men veb-sayt yarataman. Sizni onlayn ko'rib qoldim, keyin shaxsan o'zingizga yuzlanyapman. "
        f"Hozir odamlar usta yoki biror xizmat qidirganda avvalo telefondan Google orqali izlashadi — shaxsiy saytingizda ishlaringiz rasmlari, narxlari va raqamingiz tursa, mijozlar ko'rib ishonch bilan sizga bog'lanadi, har bir odamga telefonda qayta-qayta tushuntirib o'tirmaysiz.\n\n"
        f"Xohlasangiz, ishingizga mos chiroyli veb-sayt qilib beraman, yo'q deyishga shoshilmang. "
        f"Agar veb-sayt yetarli emas desangiz, hatto reklama video ham qilib bera olaman.\n\n"
        f"Bu sizga mutlaqo majburiy emas, bemalol rad etishingiz mumkin."
    )

def generate_followup_ad(business_title: str = None) -> str:
    """Mijoz 'kerakmas', 'yo'q' yoki 'rahmat' deganda tabiiy insoniy javob"""
    if business_title:
        biz_phrase = f"sizning ishingiz ({business_title})"
    else:
        biz_phrase = "sizning biznesingiz"

    return (
        "Unday deyishga shoshilmang.\n\n"
        f"Bilaman, qarang, men sizga oddiy qilib tushuntiraman: {biz_phrase} hozir odamlar, tanish-bilishlar yoki video orqali tarqalayotgan bo'lishi mumkin. "
        "To'g'ri, ular ham ko'p odamlar olib kelishi mumkin, lekin bunga doimiy kafolat yo'q.\n\n"
        "Men sizga veb-saytning ko'rinishini va u nimalar qila olishini ko'rsatsam rostdan ham yoqib qoladi. "
        "Hech bo'lmasa bir ko'rib chiqing — agar yoqmasa mayli, vaqtingiz va e'tiboringiz uchun rahmat deb boshqa bezovta qilmayman.\n\n"
        "Bir dona namunasini ko'rsataymi?"
    )

def get_fallback_details_explanation(business_title: str = None, business_category: str = None) -> str:
    """Mijoz 'nimalar qilib bera olasiz?' yoki 'batafsil tushuntiring' deganda oddiy insoniy javob"""
    biz = f"\"{business_title}\"" if business_title else "biznesingiz"
    if is_food_category(business_category):
        return (
            f"Albatta, tushuntirib beraman.\n\n"
            f"Men {biz} uchun birinchidan chiroyli va telefondan ochishga juda qulay veb-sayt tayyorlab beraman. "
            f"Unda taomlaringiz rasmlari, narxlari va onlayn menyu bo'ladi (xohlasangiz stollar uchun QR-kod ham ulab beraman). "
            f"Saytdan stol band qilishsa yoki yetkazib berishga buyurtma berishsa, xabari darrov sizning Telegramingizga tushadi. "
            f"Shuningdek odamlar Google'dan restoran qidirganda ham sizning joyingiz chiqishi osonlashadi.\n\n"
            f"Bundan tashqari, agar kerak bo'lsa Instagram, TikTok va Telegram uchun taomlaringizni chiroyli ko'rsatib beradigan reklama video ham tayyorlab bera olaman.\n\n"
            f"Narxiga kelsak, avval sizga hech qanday to'lovsiz bitta namuna ko'rinishini tayyorlab ko'rsataman. "
            f"Ko'rib yoqsa keyin kelishamiz, yoqmasa mutlaqo majburiy emas.\n\n"
            f"Xohlasangiz hoziroq birinchi namunani tayyorlab ko'rsataymi?"
        )

    return (
        f"Albatta, tushuntirib beraman.\n\n"
        f"Men {biz} uchun avvalo telefondan ochishga qulay zamonaviy veb-sayt qilib beraman. "
        f"Unda barcha xizmatlaringiz, narxlar, rasmlar va manzilingiz chiroyli ko'rinib turadi. "
        f"Mijoz saytga kirib ariza yoki buyurtma qoldirsa, xabari darrov sizning Telegramingizga keladi. "
        f"Google'dan xizmat qidirgan odamlar ham sizni osongina topib kelishadi.\n\n"
        f"Agar qo'shimcha kerak bo'lsa, Instagram, TikTok va Telegramda mijoz jalb qilish uchun sifatli reklama video ham tayyorlab bera olaman.\n\n"
        f"Eng qulayi, avval hech qanday to'lovsiz bitta namuna tayyorlab ko'rsataman. Ko'rib yoqsa keyin kelishamiz, yoqmasa majburiy emas.\n\n"
        f"Xohlasangiz hoziroq birinchi namunani tayyorlab ko'rsataymi?"
    )

def _normalize_uz_text(text: str) -> str:
    if not text:
        return ""
    t = text.lower().strip()
    for ch in ("’", "‘", "ʻ", "ʼ", "`", "ʹ"):
        t = t.replace(ch, "'")
    return t

def is_refusal_message(text: str) -> bool:
    t = _normalize_uz_text(text)
    if not t:
        return False
    exact_refusals = {
        "yo'q", "yoq", "yoq.", "yo'q.", "yo", "yoq rahmat", "yo'q rahmat",
        "rahmat", "rahmat.", "kerakmas", "keremas", "kerekmas", "kerak emas", "shartmas",
        "shart emas", "qiziqmas", "qiziq emas", "hojati yoq", "hojati yo'q",
        "keragi yoq", "keragi yo'q", "zarur emas", "yoq kerekmas", "yoq kerakmas",
        "kerak emas rahmat", "kerakmas rahmat", "net", "нет", "спасибо не надо", "не надо", "не интересует"
    }
    if t in exact_refusals:
        return True
    refusal_patterns = [
        "kerak emas", "kerek emas", "kerakmas", "keremas", "kerekmas", "shart emas", "shartmas",
        "qiziq emas", "qiziqmas", "hojati yo'q", "hojati yoq", "keragi yo'q", "keragi yoq",
        "yo'q rahmat", "yoq rahmat", "rahmat, kerak emas", "rahmat kerakmas",
        "kerak bo'lsa aytaman", "kerak bolsa aytaman", "kerak bo'lsa", "kerak bolsa",
        "hozircha kerak emas", "hozircha kerakmas", "hozircha yo'q", "hozircha yoq",
        "bizga kerakmas", "menga kerakmas", "bizga kerak emas", "menga kerak emas",
        "yoq uka", "yo'q uka", "yoq usta",
        "не надо", "не нужно", "не интересует", "спасибо, не надо"
    ]
    return any(p in t for p in refusal_patterns)

def is_objection(text: str) -> bool:
    """Mijoz e'tiroz yoki ikkilanish bildirayotganini aniqlaydi (qimmat, instagram bor, vaqtim yo'q)"""
    t = _normalize_uz_text(text)
    if not t or is_refusal_message(t):
        return False
    objection_patterns = [
        "qimmat", "arzon", "puli kop", "puli ko'p", "mablag", "byudjet",
        "instagram", "insta", "telegram kanal", "tg kanal", "instagramim",
        "vaqt yoq", "vaqtim yo'q", "vaqtimiz yo'q", "keyinroq", "hozir emas", "hozircha emas",
        "kerak emas hozir", "o'ylab ko'ramiz", "oylab koramiz", "maslahatlash", "sherigim",
        "дорого", "нет времени", "позже", "инстаграм есть", "подумаем"
    ]
    return any(p in t for p in objection_patterns)

def is_detail_question(text: str) -> bool:
    """Mijoz 'nimalar qilib bera olasiz', 'batafsil tushuntiring', 'narxi qancha' deb so'rayotganini aniqlaydi"""
    t = _normalize_uz_text(text)
    if not t or is_refusal_message(t):
        return False
    question_patterns = [
        "nimalar", "nima qilib", "nima qila", "batafsil", "tushuntir", "qanday", "qanaqa",
        "narx", "qancha", "necha pul", "nechi pul", "shartlar", "nima foyda", "foydasi",
        "imkoniyat", "video qanaqa", "sayt haqida", "batafsilroq", "aytib bering",
        "подробнее", "что вы делаете", "сколько стоит", "цена", "какие услуги"
    ]
    if any(p in t for p in question_patterns):
        return True
    if "?" in t and len(t) > 10:
        return True
    return False

def is_positive_interest(text: str) -> bool:
    t = _normalize_uz_text(text)
    if not t or is_refusal_message(t):
        return False
    cleaned = "".join(c for c in t if c.isalnum() or c.isspace())
    words = set(cleaned.split())
    positive_exact = {
        "ha", "xa", "kerak", "kerek", "kk", "lozim", "zarur", "mayli", "qani",
        "hop", "xop", "ok", "okay", "albatta", "davay", "roziman", "rozi",
        "maqul", "yaxshi", "boladi", "qiziq", "qiziqarli", "qiziqtirdi",
        "korsating", "koraylik", "koraychi", "yuboring", "tashlang", "namuna", "namunani",
        "eshitaman", "eshitaylik", "gaplashamiz", "gaplashaylik", "boshlaylik", "tayyorlang",
        "да", "давай", "давайте", "покажи", "покажите", "интересно", "можно", "хорошо",
        "нужно", "нужен", "нужна", "надо", "хочу", "согласен", "согласна", "пришлите",
        "скиньте", "актуально", "требуется"
    }
    if words.intersection(positive_exact):
        return True
    positive_phrases = [
        "ha mayli", "xa mayli", "ha kerak", "xa kerak", "bizga kerak", "menga kerak",
        "sayt kerak", "bot kerak", "reklama kerak", "juda kerak", "albatta kerak",
        "kerak edi", "kerek edi", "kerak boladi", "kerak bo'ladi", "kerak bolardi", "kerak bo'lardi",
        "kerak bizga", "kerak menga", "qani korsating", "qani ko'rsating", "mayli korsating",
        "mayli ko'rsating", "qani koraylik", "qani ko'raylik", "namunani korsating",
        "namunani ko'rsating", "bir koraylik", "bir ko'raylik", "korsatingchi",
        "ko'rsatingchi", "mayli qani", "qiziq ekan", "korsat", "ko'rsat", "yubor", "tashla",
        "qilib bering", "yasab bering", "tayyorlab bering", "qilsak boladi", "qilsak bo'ladi",
        "namuna tayyorlang", "namuna ko'rsating", "namuna korsating",
        "нам нужно", "мне нужно", "было бы хорошо", "давайте посмотрим"
    ]
    return any(p in t for p in positive_phrases)

async def send_to_recipient(target: str, message_text: str):
    target = target.strip()
    if target.startswith("https://t.me/"):
        target = "@" + target.replace("https://t.me/", "")

    entity = None
    if target.startswith("@"):
        entity = await client.get_entity(target)
    else:
        cleaned_phone = normalize_phone(target)
        if cleaned_phone.startswith("+") and len(cleaned_phone) > 6:
            try:
                entity = await client.get_entity(cleaned_phone)
            except Exception:
                contact = InputPhoneContact(client_id=0, phone=cleaned_phone, first_name="Mijoz", last_name="")
                import_result = await client(ImportContactsRequest([contact]))
                if import_result.users:
                    entity = import_result.users[0]
                else:
                    raise ValueError(f"Raqam Telegramda ochilmagan: {cleaned_phone}")
        else:
            entity = await client.get_entity(target)

    async with client.action(entity, "typing"):
        await asyncio.sleep(random.uniform(2.0, 4.0))
    return await client.send_message(entity, message_text, parse_mode=None)


MIJOZLAR_FOLDER_NAME = "Mijozlar"
folder_lock = asyncio.Lock()


async def _ensure_peers_in_mijozlar_folder(input_peers: list) -> bool:
    """Berilgan chatlarni Telegramdagi alohida 'Mijozlar' papkasiga qo'shadi."""
    if not input_peers:
        return True

    async with folder_lock:
        try:
            resp = await client(tl_functions.messages.GetDialogFiltersRequest())
            filters_list = getattr(resp, "filters", []) or []

            existing_filter = None
            used_ids = set()
            for f in filters_list:
                fid = getattr(f, "id", None)
                if fid is not None:
                    used_ids.add(fid)
                if isinstance(f, tl_types.DialogFilter):
                    title_obj = getattr(f, "title", None)
                    title_str = getattr(title_obj, "text", str(title_obj or "")).strip()
                    if title_str.lower() == MIJOZLAR_FOLDER_NAME.lower():
                        existing_filter = f

            if existing_filter:
                filter_id = existing_filter.id
                pinned_peers = list(existing_filter.pinned_peers or [])
                include_peers = list(existing_filter.include_peers or [])
                exclude_peers = list(existing_filter.exclude_peers or [])
                emoticon = existing_filter.emoticon or "💼"
                contacts = bool(existing_filter.contacts)
                non_contacts = bool(existing_filter.non_contacts)
                groups = bool(existing_filter.groups)
                broadcasts = bool(existing_filter.broadcasts)
                bots = bool(existing_filter.bots)
                exclude_muted = bool(existing_filter.exclude_muted)
                exclude_read = bool(existing_filter.exclude_read)
                color = getattr(existing_filter, "color", None)
            else:
                filter_id = 2
                while filter_id in used_ids:
                    filter_id += 1
                pinned_peers = []
                include_peers = []
                exclude_peers = []
                emoticon = "💼"
                contacts = False
                non_contacts = False
                groups = False
                broadcasts = False
                bots = False
                exclude_muted = False
                exclude_read = False
                color = None

            existing_ids = set()
            for p in include_peers:
                try:
                    existing_ids.add(tl_utils.get_peer_id(p))
                except Exception:
                    pass

            changed = existing_filter is None or bool(getattr(existing_filter, "exclude_archived", False))
            for peer in input_peers:
                try:
                    pid = tl_utils.get_peer_id(peer)
                except Exception:
                    continue
                if pid not in existing_ids:
                    include_peers.append(peer)
                    existing_ids.add(pid)
                    changed = True

            if not changed:
                return True

            def _build_filter(peers_slice):
                return tl_types.DialogFilter(
                    id=filter_id,
                    title=tl_types.TextWithEntities(text=MIJOZLAR_FOLDER_NAME, entities=[]),
                    pinned_peers=pinned_peers,
                    include_peers=peers_slice,
                    exclude_peers=exclude_peers,
                    contacts=contacts,
                    non_contacts=non_contacts,
                    groups=groups,
                    broadcasts=broadcasts,
                    bots=bots,
                    exclude_muted=exclude_muted,
                    exclude_read=exclude_read,
                    exclude_archived=False,  # Arxivlangan bo'lsa ham Mijozlar papkasida ko'rinib tursin
                    emoticon=emoticon,
                    color=color,
                )

            try:
                await client(tl_functions.messages.UpdateDialogFilterRequest(
                    id=filter_id,
                    filter=_build_filter(include_peers)
                ))
            except Exception as err:
                # Oddiy (Premium bo'lmagan) Telegramda papkada max 100 ta chat sig'adi
                if len(include_peers) > 100:
                    await client(tl_functions.messages.UpdateDialogFilterRequest(
                        id=filter_id,
                        filter=_build_filter(include_peers[-100:])
                    ))
                else:
                    raise err
            return True
        except Exception as err:
            log_event("⚠️ PAPKA XATO", MIJOZLAR_FOLDER_NAME, "[yellow]OGOHLANTIRISH[/yellow]", str(err)[:45])
            return False


async def move_chat_to_mijozlar(entity_or_id, archive: bool | None = None) -> bool:
    """Chatni 'Mijozlar' papkasiga qo'shadi va ixtiyoriy ravishda asosiy chatlardan arxivga/orqaga oladi."""
    try:
        input_peer = await client.get_input_entity(entity_or_id)
    except Exception:
        return False

    if archive is True:
        try:
            await client.edit_folder(input_peer, 1)
        except Exception:
            pass
    elif archive is False:
        try:
            await client.edit_folder(input_peer, 0)
        except Exception:
            pass

    return await _ensure_peers_in_mijozlar_folder([input_peer])


async def sync_all_leads_to_mijozlar() -> tuple[int, int]:
    """ad_leads.json dagi barcha mavjud mijozlarni 'Mijozlar' papkasiga jamlaydi."""
    peers_to_add = []
    skipped = 0
    for cid, lead in ad_leads.items():
        if cid == "contacted_phones" or not isinstance(lead, dict):
            continue
        input_peer = None
        candidates = []
        try:
            candidates.append(int(cid))
        except Exception:
            pass
        if lead.get("target") and not str(lead["target"]).startswith("ID:"):
            candidates.append(lead["target"])

        for cand in candidates:
            try:
                input_peer = await client.get_input_entity(cand)
                break
            except Exception:
                continue

        if not input_peer:
            skipped += 1
            continue

        peers_to_add.append(input_peer)
        # Rozilik bildirganlar asosiy chatda ko'rinsin, javob bermagan sovuq reklamalar arxivda turib Mijozlar papkasida jamlanadi
        target_folder = 0 if lead.get("agreed") else 1
        try:
            await client.edit_folder(input_peer, target_folder)
        except Exception:
            pass

    if peers_to_add:
        await _ensure_peers_in_mijozlar_folder(peers_to_add)
    else:
        # Kamida papkaning o'zini yaratib qo'yamiz (o'z chatimiz yoki bo'sh)
        await _ensure_peers_in_mijozlar_folder([])
    return len(peers_to_add), skipped


# ==============================================================================
# 5. GEMINI AI SO'ROV FUNKSIYALARI
# ==============================================================================
async def call_gemini(contents, chat_id: int = None, system_instruction: str = GEMINI_SYSTEM_INSTRUCTION) -> str:
    candidate_models = [
        config_state["model"],
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash"
    ]
    seen = set()
    models = [m for m in candidate_models if not (m in seen or seen.add(m))]

    last_error = None
    for model_name in models:
        try:
            if chat_id is not None and isinstance(contents, str):
                if chat_id not in chat_sessions:
                    chat_sessions[chat_id] = gemini_client.aio.chats.create(
                        model=model_name,
                        config=types.GenerateContentConfig(system_instruction=system_instruction)
                    )
                chat = chat_sessions[chat_id]
                response = await chat.send_message(contents)
                return response.text
            else:
                response = await gemini_client.aio.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=system_instruction)
                )
                return response.text
        except APIError as e:
            last_error = e
            if chat_id and chat_id in chat_sessions:
                chat_sessions.pop(chat_id, None)
            continue
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"Gemini xatosi: {last_error}")

async def reply_or_edit(event, text: str, edit: bool = False):
    MAX_CHUNK = 4000
    chunks = [text[i:i + MAX_CHUNK] for i in range(0, len(text), MAX_CHUNK)] if len(text) > MAX_CHUNK else [text]
    first_chunk = chunks[0]
    first_sent = None

    if edit:
        try:
            first_sent = await event.edit(first_chunk, parse_mode="md")
        except Exception:
            first_sent = await event.edit(first_chunk, parse_mode=None)
    else:
        try:
            first_sent = await event.reply(first_chunk, parse_mode="md")
        except Exception:
            first_sent = await event.reply(first_chunk, parse_mode=None)

    if first_sent:
        sent_message_ids.add(first_sent.id)

    for chunk in chunks[1:]:
        try:
            sent_msg = await event.respond(chunk, parse_mode="md")
        except Exception:
            sent_msg = await event.respond(chunk, parse_mode=None)
        if sent_msg:
            sent_message_ids.add(sent_msg.id)


# ==============================================================================
# 🗺️ 6. AVTOMATIK GOOGLE MAPS REKLAMA (.start reklama / .stop reklama)
# ==============================================================================
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.stop\s+reklama$"))
async def handle_stop_reklama(event):
    if config_state["campaign_running"]:
        config_state["campaign_running"] = False
        await event.edit("🛑 **Reklama tarqatish to'xtatildi!**")
        log_event("🛑 .STOP", "Campaign", "[bold yellow]TO'XTATILDI[/bold yellow]", "Foydalanuvchi tomonidan to'xtatildi")
    else:
        await event.edit("ℹ️ Hozirda faol reklama jarayoni yo'q.")

async def run_outreach_campaign(query: str = "restoran", max_targets: int = 5, progress_cb=None) -> dict:
    """
    Userbot hamda tugmali Telegram bot uchun umumiy Google Maps reklama tarqatish dvigateli.
    """
    expanded_cats = expand_search_categories(query)
    config_state["campaign_running"] = True
    log_event("🗺️ MAPS QIDIRUV", query[:24], "[bright_cyan]IZLANMOQDA...[/bright_cyan]", f"{len(expanded_cats)} soha | Max: {max_targets} ta")

    skip_phones = set(ad_leads.get("contacted_phones", []))

    try:
        targets = await asyncio.to_thread(
            scrape_google_maps_no_website,
            query=query,
            max_results=max_targets,
            skip_phones=skip_phones
        )
    except Exception as e:
        config_state["campaign_running"] = False
        log_event("❌ MAPS XATO", query[:24], "[bold red]XATOLIK[/bold red]", str(e))
        return {"ok": False, "summary_text": f"❌ Google Maps'ni tekshirishda xatolik:\n`{e}`"}

    if not targets:
        config_state["campaign_running"] = False
        return {"ok": False, "summary_text": f"ℹ️ `{query}` bo'yicha veb-sayti yo'q yangi joylar topilmadi (yoki hammasi avval yozilgan)."}

    # CMD da topilgan bizneslar jadvalini chiqarish
    found_table = Table(
        title=f"[bold bright_cyan]GOOGLE MAPS'DAN TOPILGAN VEB-SAYTSIZ BIZNESLAR ({len(targets)} ta)[/bold bright_cyan]",
        border_style="bright_blue",
        box=box.ROUNDED
    )
    found_table.add_column("#", style="grey70", width=4)
    found_table.add_column("Nomi", style="bold bright_white")
    found_table.add_column("Soha", style="bright_blue")
    found_table.add_column("Telefon Raqami", style="bright_cyan")
    found_table.add_column("Veb-sayt", style="yellow")
    for idx, t in enumerate(targets, 1):
        found_table.add_row(str(idx), t["name"], t.get("category", query), t["phone"], t["website"] or "Yo'q ❌")
    console.print(found_table)

    me = await client.get_me()
    owner_name = me.first_name if (me and me.first_name) else "Muhammadrizo"
    owner_username = me.username
    owner_phone = me.phone

    dmin = float(config_state.get("delay_min", 14.0))
    dmax = float(config_state.get("delay_max", 24.0))

    if progress_cb:
        await progress_cb(
            f"✅ **Google Maps'dan {len(targets)} ta veb-sayti yo'q joy topildi!**\n"
            f"📤 Telegram orqali insoniy tarzda yuborish boshlanmoqda ({int(dmin)}–{int(dmax)} soniya tanaffus bilan)..."
        )

    sent_count = 0
    not_on_tg = 0
    errors_count = 0

    for idx, item in enumerate(targets, 1):
        if not config_state["campaign_running"]:
            break

        r_name = item["name"]
        r_phone = item["phone"]
        r_cat = item.get("category", query)

        if progress_cb:
            await progress_cb(
                f"📤 **Yuborilmoqda: {idx}/{len(targets)}**\n"
                f"🏷️ **Biznes:** {r_name} (`{r_cat}`)\n"
                f"📞 **Raqam:** `{r_phone}`\n"
                f"✅ **Yuborildi:** {sent_count} | 📵 **TG yo'q:** {not_on_tg}"
            )

        if r_phone not in ad_leads["contacted_phones"]:
            ad_leads["contacted_phones"].append(r_phone)
            save_ad_leads(ad_leads)

        ad_text = generate_web_ad(
            owner_name=owner_name,
            recipient_title=r_name,
            username=owner_username,
            phone=owner_phone,
            is_maps_restaurant=is_food_category(r_cat),
            business_category=r_cat
        )

        try:
            sent_msg = await send_to_recipient(r_phone, ad_text)
            if sent_msg and hasattr(sent_msg, "chat_id"):
                recipient_id = str(sent_msg.chat_id)
                ad_leads[recipient_id] = {
                    "target": r_phone,
                    "title": r_name,
                    "category": r_cat,
                    "maps_url": item["maps_url"],
                    "sent_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "followup_sent": False,
                    "agreed": False,
                    "details_explained": False
                }
                save_ad_leads(ad_leads)
                if config_state.get("auto_folder", True):
                    await move_chat_to_mijozlar(sent_msg.input_chat or sent_msg.chat_id, archive=True)

            sent_count += 1
            log_event("📢 AVTO-REKLAMA", f"{r_name[:22]}", "[bold bright_green]YUBORILDI ✅[/bold bright_green]", f"{r_cat} | Tel: {r_phone}")

            if idx < len(targets) and config_state["campaign_running"]:
                await asyncio.sleep(random.uniform(dmin, dmax))

        except PeerFloodError:
            log_event("🚨 ANTI-SPAM", r_phone, "[bold red]TO'XTATILDI[/bold red]", "Telegram spam cheklovi (PeerFlood)!")
            await client.send_message('me', "⚠️ **DIQQAT!** Telegram vaqtincha cheklov (PeerFlood) qo'ydi. Xavfsizlik uchun tarqatish to'xtatildi.")
            config_state["campaign_running"] = False
            break
        except FloodWaitError as fw:
            log_event("⏳ FLOOD WAIT", r_phone, "[yellow]KUTISH[/yellow]", f"{fw.seconds} soniya kutilmoqda...")
            await asyncio.sleep(fw.seconds + 3)
        except ValueError as ve:
            not_on_tg += 1
            log_event("⚠️ TG YO'Q", f"{r_name[:22]}", "[yellow]TOPILMADI[/yellow]", str(ve))
        except Exception as err:
            errors_count += 1
            log_event("❌ XATOLIK", f"{r_name[:22]}", "[bold red]XATO[/bold red]", str(err)[:40])

    config_state["campaign_running"] = False

    summary = (
        f"🏁 **Google Maps Reklama Yakunlandi!**\n\n"
        f"📌 **Yo'nalish:** `{query}`\n"
        f"🔎 **Topildi (saytsiz):** {len(targets)} ta joy\n"
        f"✅ **Telegramda yuborildi:** {sent_count} ta\n"
        f"📵 **Telegramda ochilmagan:** {not_on_tg} ta\n"
        f"❌ **Boshqa xatolar:** {errors_count} ta\n"
        f"💼 **Joylashtirildi:** Barcha chatlar alohida **'{MIJOZLAR_FOLDER_NAME}'** papkasiga jamlandi!\n\n"
        f"🤖 Kim javob yozsa (\"kerakmas\", \"nimalar qilib bera olasiz\", \"ha\"), bot avtomatik javob berib, sizni ogohlantiradi!"
    )
    return {"ok": True, "summary_text": summary, "sent": sent_count, "found": len(targets)}

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.start\s+reklama(?:\s+([\s\S]+))?$"))
async def handle_start_reklama(event):
    """
    Google Maps'dan veb-sayti YO'Q restoran yoki turli xil bizneslarni avtomatik topib,
    ularning telefon raqamiga Telegram orqali sohasiga mos reklama yuboradi.
    """
    if config_state["campaign_running"]:
        await event.edit("⚠️ Reklama jarayoni allaqachon ishlamoqda! To'xtatish uchun: `.stop reklama`")
        return

    raw_arg = (event.pattern_match.group(1) or "").strip()
    query = "restoran"
    max_targets = 5

    if raw_arg:
        parts = raw_arg.split()
        if parts[-1].isdigit():
            max_targets = min(int(parts[-1]), 15)
            query = " ".join(parts[:-1]).strip() or "restoran"
        else:
            query = raw_arg

    expanded_cats = expand_search_categories(query)
    if len(expanded_cats) > 1 and max_targets == 5 and not (raw_arg and raw_arg.split()[-1].isdigit()):
        max_targets = 8

    cats_preview = ", ".join(expanded_cats[:4]) + ("..." if len(expanded_cats) > 4 else "")
    await event.edit(
        f"🔍 **Google Maps tahlil qilinmoqda...**\n"
        f"📌 **So'rov:** `{query}` ({len(expanded_cats)} ta yo'nalish: `{cats_preview}`)\n"
        f"🎯 **Maqsad:** {max_targets} tagacha veb-sayti yo'q va telefoni bor joylar izlanmoqda..."
    )

    async def _progress(msg):
        try:
            await event.edit(msg)
        except Exception:
            pass

    res = await run_outreach_campaign(query=query, max_targets=max_targets, progress_cb=_progress)
    await event.reply(res["summary_text"])


# ==============================================================================
# 🎯 7. QO'LDA .reklama, .mijoz VA .mijozlar PAPKA BUYRUQLARI
# ==============================================================================
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.reklama(?:\s+([^\s]+))?(?:\s+([\s\S]+))?"))
async def handle_reklama_command(event):
    target = event.pattern_match.group(1)
    recipient_title = event.pattern_match.group(2)
    if recipient_title:
        recipient_title = recipient_title.strip()

    if not target:
        if event.is_private and event.chat_id == (await client.get_me()).id:
            await event.edit("⚠️ **Foydalanish:** `.reklama <+998901234567 yoki @username> [ism/kasb]`")
            return
        target = str(event.chat_id)

    me = await client.get_me()
    owner_name = me.first_name if (me and me.first_name) else "Muhammadrizo"
    owner_username = me.username
    owner_phone = me.phone

    await event.edit(f"⏳ `{target}` manziliga samimiy taklif xabari jo'natilmoqda...")

    with console.status(f"[bold bright_cyan]Xabar yuborilmoqda: [bright_yellow]{target}[/bright_yellow]...[/bold bright_cyan]", spinner="dots"):
        try:
            ad_text = generate_web_ad(
                owner_name=owner_name,
                recipient_title=recipient_title,
                username=owner_username,
                phone=owner_phone
            )
            sent_msg = await send_to_recipient(target, ad_text)
            if sent_msg and hasattr(sent_msg, "chat_id"):
                recipient_id = str(sent_msg.chat_id)
                ad_leads[recipient_id] = {
                    "target": target,
                    "title": recipient_title or "",
                    "sent_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "followup_sent": False,
                    "agreed": False,
                    "details_explained": False
                }
                if target.startswith("+") and target not in ad_leads["contacted_phones"]:
                    ad_leads["contacted_phones"].append(target)
                save_ad_leads(ad_leads)
                await move_chat_to_mijozlar(sent_msg.input_chat or sent_msg.chat_id, archive=True)

            log_event("📢 .REKLAMA", target, "[bold bright_green]YUBORILDI ✅[/bold bright_green]", f"Kimga: {recipient_title or 'Mijoz'}")
            await event.edit(
                f"✅ **Taklif xabari muvaffaqiyatli yetkazildi!**\n"
                f"🎯 **Qabul qiluvchi:** `{target}`\n"
                f"💼 Chat alohida **'{MIJOZLAR_FOLDER_NAME}'** papkasiga qo'shildi."
            )
        except Exception as err:
            log_event("📢 .REKLAMA", target, "[bold bright_red]XATOLIK ❌[/bold bright_red]", str(err))
            await event.edit(f"❌ Xabar yuborishda muammo yuz berdi:\n`{err}`")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.(?:mijoz|lead)(?:\s+(.+))?$"))
async def handle_mark_as_lead(event):
    custom_title = event.pattern_match.group(1)
    chat_id = str(event.chat_id)
    chat = await event.get_chat()
    title = custom_title if custom_title else (getattr(chat, 'first_name', '') or getattr(chat, 'title', '') or "Mijoz")
    phone = getattr(chat, 'phone', None)
    target_str = f"+{phone}" if phone else f"ID: {chat_id}"

    ad_leads[chat_id] = {
        "target": target_str,
        "title": title,
        "sent_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "followup_sent": True,
        "agreed": True,
        "details_explained": False
    }
    save_ad_leads(ad_leads)
    await move_chat_to_mijozlar(event.input_chat or event.chat_id, archive=False)

    await event.edit(
        f"✅ **[Mijoz Muvaffaqiyatli Belgilandi]**\n"
        f"👤 **Mijoz:** {title}\n"
        f"💼 **Papka:** '{MIJOZLAR_FOLDER_NAME}' bo'limiga qo'shildi\n"
        f"📁 Endi ushbu chatdagi barcha yangi rasmlar, audio va matnlar avtomatik **Saqlangan xabarlar**ingizga va kompyuterga yig'iladi!"
    )
    log_event("📌 .MIJOZ", chat_id, "[bold bright_green]BIRIKTIRILDI ✅[/bold bright_green]", f"Mijoz belgilandi: {title}")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.(?:mijozlar|papka)$"))
async def handle_sync_mijozlar_folder(event):
    await event.edit(f"⏳ Barcha mijozlar **'{MIJOZLAR_FOLDER_NAME}'** papkasiga tartiblanmoqda...")
    added_count, skipped_count = await sync_all_leads_to_mijozlar()
    if added_count > 0:
        await event.edit(
            f"✅ **'{MIJOZLAR_FOLDER_NAME}' papkasi tayyor va yangilandi!**\n"
            f"💼 **Jamlangan chatlar:** {added_count} ta\n"
            f"ℹ️ **O'tkazib yuborilgan (topilmagan):** {skipped_count} ta\n\n"
            f"📌 Telegramning yuqori/chap qismidagi **'{MIJOZLAR_FOLDER_NAME}'** bo'limidan barcha mijozlarni bir joyda ko'rishingiz mumkin (rozi bo'lganlar asosiy ro'yxatda ham qoladi, qolganlari asosiy chatni to'ldirmasligi uchun tartiblandi)."
        )
    else:
        await event.edit(
            f"ℹ️ Hozircha `{AD_LEADS_FILE}` da saqlangan mijozlar topilmadi.\n"
            f"Birinchi `.start reklama`, `.reklama` yoki `.mijoz` ishlatishingiz bilan **'{MIJOZLAR_FOLDER_NAME}'** papkasi avtomatik ochiladi!"
        )
    log_event("💼 .MIJOZLAR", MIJOZLAR_FOLDER_NAME, "[bold bright_green]TARTIBLANDI ✅[/bold bright_green]", f"{added_count} ta chat jamlandi")


# ==============================================================================
# 🎯 8. MIJOZ JAVOBLARINI AVTOMATIK BOSHQARISH ("Nimalar qila olasiz?", "HA", "Yo'q", Fayllar)
# ==============================================================================
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_incoming_client_reply(event):
    sender = await event.get_sender()
    if not isinstance(sender, User) or sender.is_self or sender.bot:
        return

    sender_id = str(event.chat_id)
    text = (event.message.message or "").strip()
    has_media = bool(event.message.media)

    # 🎙️ Ovozli xabarlar (Voice / Audio) qabul qilish va Gemini AI bilan transkripsiya
    is_voice = bool(getattr(event.message, "voice", False) or getattr(event.message, "audio", False))
    voice_transcript = None
    if is_voice:
        try:
            voice_bytes = await event.message.download_media(file=bytes)
            if voice_bytes:
                audio_part = types.Part.from_bytes(data=voice_bytes, mime_type="audio/ogg")
                prompt_transcribe = (
                    "Bu mijozdan kelgan audio/ovozli xabar. "
                    "Faqat va faqat uning aytgan so'zlarini o'zbek tilida aniq transkripsiya qilib yozib ber (hech qanday qo'shimcha so'zsiz):"
                )
                vt = await call_gemini([audio_part, prompt_transcribe], system_instruction="Sen aniq audio transkripsiya AI tizimisan.")
                if vt and len(vt.strip()) > 1:
                    voice_transcript = vt.strip()
                    text = voice_transcript
                    log_event("🎙️ OVOZ TUSHUNILDI", str(event.chat_id), "[bright_cyan]AUDIO[/bright_cyan]", f"'{voice_transcript[:35]}...'")
        except Exception as _ve:
            log_event("⚠️ OVOZ XATOSI", str(event.chat_id), "[yellow]WARN[/yellow]", str(_ve))

    if sender_id not in ad_leads:
        sender_phone_plus = f"+{sender.phone}" if getattr(sender, "phone", None) else ""
        contacted_list = ad_leads.get("contacted_phones", [])
        was_contacted = bool(sender_phone_plus and sender_phone_plus in contacted_list)
        if was_contacted or is_positive_interest(text) or is_detail_question(text) or is_objection(text) or is_voice:
            ad_leads[sender_id] = {
                "target": sender_phone_plus if sender_phone_plus else (f"@{sender.username}" if sender.username else sender.first_name),
                "title": sender.first_name or "Mijoz",
                "sent_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "followup_sent": False if was_contacted else True,
                "agreed": False,
                "details_explained": False
            }
            save_ad_leads(ad_leads)
        else:
            return

    lead = ad_leads[sender_id]
    target_name = lead.get("title") or lead.get("target") or sender_id

    # 1-HOLAT: Mijoz "Nimalar qilib bera olasiz?", "Batafsil tushuntiring", "Narxi qancha?" deb so'rasa
    if config_state.get("auto_reply", True) and is_detail_question(text) and not lead.get("details_explained"):
        async with client.action(event.chat_id, "typing"):
            await asyncio.sleep(2)
            lead_cat = lead.get("category", "")
            try:
                prompt = (
                    f"Mijozning biznesi/joyi: '{target_name}' (sohasi: '{lead_cat or 'biznes'}').\n"
                    f"Mijoz shunday savol yozdi: '{text}'.\n"
                    f"Unga tirik inson Muhammadrizo nomidan aynan shu sohasiga mos, samimiy, aniq va tushunarli javob yoz."
                )
                reply_text = await call_gemini(prompt, chat_id=None, system_instruction=CLIENT_SALES_SYSTEM_PROMPT)
            except Exception:
                # Agar Gemini API band bo'lsa, tayyor mukammal javobdan foydalanamiz
                reply_text = get_fallback_details_explanation(business_title=lead.get("title"), business_category=lead_cat)

            await event.reply(reply_text)
            lead["details_explained"] = True
            lead["agreed"] = True
            lead["followup_sent"] = True
            save_ad_leads(ad_leads)
            await move_chat_to_mijozlar(event.input_chat or event.chat_id, archive=False)

            alert_msg = (
                f"💡 **MIJOZ BATAFSIL MA'LUMOT SO'RADI (QIZIQMOQDA)!**\n"
                f"👤 **Mijoz:** `{lead.get('target', sender_id)}` ({target_name})\n"
                f"💬 **Mijoz savoli:** \"{text}\"\n"
                f"✅ **Avto-javob berildi!** Endi u yuboradigan barcha ma'lumotlar shu yerga saqlanadi."
            )
            await client.send_message('me', alert_msg)
            if bot_ctx.get("notify_bot_owner"):
                await bot_ctx["notify_bot_owner"](
                    alert_msg,
                    buttons=[[Button.inline("👤 Mijozni ochish", f"ld:{sender_id}".encode()), Button.inline("👥 CRM", b"m:crm")]]
                )
            log_event("💡 BATAFSIL JAVOB", str(event.chat_id), "[bold bright_green]TUSHUNTIRILDI ✅[/bold bright_green]", f"Mijoz: '{text[:22]}...'")
        return

    # 2-HOLAT: Mijoz allaqachon rozi bo'lgan va materiallar/talablar yubormoqda
    if lead.get("agreed"):
        client_dir = os.path.join(CLIENT_FILES_DIR, f"mijoz_{sender_id}")
        os.makedirs(client_dir, exist_ok=True)

        saved_file_note = ""
        if has_media:
            try:
                saved_path = await event.message.download_media(file=client_dir)
                saved_file_note = f"\n💾 **Fayl kompyuterda saqlandi:** `{saved_path}`"
            except Exception as e:
                saved_file_note = f"\n⚠️ Faylni yuklashda xato: {e}"

        if text:
            try:
                with open(os.path.join(client_dir, "talablar.txt"), "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {text}\n")
            except Exception:
                pass

        header_text = (
            f"📁 **[MIJOZ MA'LUMOTI KELDI]**\n"
            f"👤 **Mijoz:** `{lead.get('target', sender_id)}` ({target_name})\n"
            f"🕒 **Vaqt:** {datetime.now().strftime('%H:%M:%S')}"
            f"{saved_file_note}\n"
            f"👇 Quyidagi xabar/fayl mijozdan keldi:"
        )
        await client.send_message('me', header_text)
        await client.forward_messages('me', event.message)
        if bot_ctx.get("notify_bot_owner"):
            await bot_ctx["notify_bot_owner"](
                f"📁 **YANGI MIJOZ MA'LUMOTI KELDI!**\n👤 **Mijoz:** {target_name}\n💬 **Matn:** `{text[:120] or '[Media fayl]'}`",
                buttons=[[Button.inline("📁 Fayl & Talablarni olish", f"la:files:{sender_id}".encode()), Button.inline("👤 CRM", f"ld:{sender_id}".encode())]]
            )

        log_event("📥 FAYL/MATN KELDI", str(event.chat_id), "[bold bright_green]SAQLANDI ✅[/bold bright_green]", f"Saqlangan xabarlarga tashlandi ({target_name})")
        return

    # 3-HOLAT: Mijoz birinchi marta "HA", "mayli ko'rsating" deb rozilik bildirsa
    if config_state.get("auto_reply", True) and is_positive_interest(text):
        lead["agreed"] = True
        lead["followup_sent"] = True
        save_ad_leads(ad_leads)
        await move_chat_to_mijozlar(event.input_chat or event.chat_id, archive=False)

        yes_alert = (
            f"🔥 **KLIENT HA DEDI! (YANGI MIJOZ)** 🔥\n\n"
            f"👤 **Klient:** `{lead.get('target', sender_id)}` ({target_name})\n"
            f"💬 **Klient yozgan xabar:** \"{text}\"\n"
            f"🕒 **Vaqt:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"📌 **Status:** Muloqot boshlandi! U yuboradigan barcha rasm, audio va matnlar avtomatik saqlanib, sizga yuboriladi."
        )
        await client.send_message('me', yes_alert)
        if bot_ctx.get("notify_bot_owner"):
            await bot_ctx["notify_bot_owner"](
                yes_alert,
                buttons=[
                    [Button.inline("👤 Mijozni ko'rish", f"ld:{sender_id}".encode()), Button.inline("📁 Fayllari", f"la:files:{sender_id}".encode())],
                    [Button.inline("👥 CRM Baza", b"m:crm")],
                ]
            )

        async with client.action(event.chat_id, "typing"):
            await asyncio.sleep(2)
            welcome_reply = (
                "Yaxshi, katta rahmat.\n\n"
                "Hozir sizga qulay bo'lishi uchun aynan faoliyatingizga mos sayt namunasini tayyorlab beraman. "
                "Saytda aynan qanday xizmatlaringiz, narxlaringiz yoki rasmlar bo'lishini xohlaysiz — shu yerga tashlab qo'ysangiz (rasm, matn yoki ovozli xabar bo'lsa ham mayli), hammasini chiroyli qilib joylab beraman."
            )
            await event.reply(welcome_reply)

        log_event("🔥 ROZILIK (HA!)", str(event.chat_id), "[bold bright_green]YANGI MIJOZ ✅[/bold bright_green]", f"Mijoz 'HA' dedi: '{text[:20]}...'")
        return

    # 3.5-HOLAT: Mijoz e'tiroz yoki ikkilanish bildirsa (qimmat, instagram bor, vaqtim yo'q, o'ylab ko'ramiz)
    if config_state.get("auto_reply", True) and is_objection(text) and not lead.get("objection_handled"):
        async with client.action(event.chat_id, "typing"):
            await asyncio.sleep(2)
            lead_cat = lead.get("category", "")
            try:
                objection_prompt = (
                    f"Mijozning biznesi: '{target_name}' (sohasi: '{lead_cat or 'biznes'}').\n"
                    f"Mijoz shunday e'tiroz / ikkilanish bildirdi: '{text}'.\n"
                    f"Sening vazifang — tirik mutaxassis Muhammadrizo nomidan xushmuomala, professional va e'tirozni yopuvchi javob yozish:\n"
                    f"1. Uning fikrini to'g'ri deb qabul qil (empatiya bildir).\n"
                    f"2. Saytning aynan shu muammoga yechim ekanini tushuntir (agar Instagram bo'lsa — sayt Instagram bilan birga qanday qilib buyurtmalarni 2x oshirishini; agar qimmat desa — sayt 24/7 ishlovchi virtual sotuvchi ekanini; agar vaqt bo'lmasa — barcha ishni sen o'zing tayyorlab berishingni).\n"
                    f"3. Hech qanday majburiyat yuklamaydigan yumshoq taklif ber (masalan: bitta bepul namunasini ko'rsatishni).\n"
                    f"Maksimal 3-4 gap bo'lsin, tabiiy o'zbek tilida."
                )
                reply_text = await call_gemini(objection_prompt, chat_id=None, system_instruction=CLIENT_SALES_SYSTEM_PROMPT)
            except Exception:
                reply_text = (
                    "Fikringizni juda yaxshi tushunaman.\n\n"
                    "Lekin qarang, bu sizga hech qanday majburiyat yuklamaydi. Sizdan ortiqcha vaqt yoki katta mablag' ham talab qilinmaydi. "
                    "Men shunchaki ishingizga mos bitta bepul namuna tayyorlab ko'rsataman — yoqsa gaplashamiz, yoqmasa hech qisi yo'q. Qani, bitta ko'rib chiqing?"
                )

            await event.reply(reply_text)
            lead["objection_handled"] = True
            save_ad_leads(ad_leads)

            alert_msg = (
                f"💬 **MIJOZ E'TIROZ / IKKILANISH BILDIRDI:**\n"
                f"👤 **Mijoz:** `{lead.get('target', sender_id)}` ({target_name})\n"
                f"🗣️ **Xabari:** \"{text}\"\n"
                f"✅ **AI professional javob berdi va e'tirozni yopdi!**"
            )
            await client.send_message('me', alert_msg)
            if bot_ctx.get("notify_bot_owner"):
                await bot_ctx["notify_bot_owner"](alert_msg)
            log_event("💬 E'TIROZ YOPILDI", str(event.chat_id), "[bold bright_green]AI JAVOB ✅[/bold bright_green]", f"'{text[:22]}...'")
        return

    # 4-HOLAT: Mijoz rad etsa ("kerakmas", "yo'q", "rahmat")
    if config_state.get("auto_reply", True) and not lead.get("followup_sent") and is_refusal_message(text):
        async with client.action(event.chat_id, "typing"):
            await asyncio.sleep(2)
            followup_text = generate_followup_ad(business_title=lead.get("title", ""))
            await event.reply(followup_text)
            lead["followup_sent"] = True
            save_ad_leads(ad_leads)

            log_event("🔄 E'TIROZGA JAVOB", str(event.chat_id), "[bold bright_green]YUBORILDI ✅[/bold bright_green]", f"Mijoz: '{text[:20]}...' | Qayta tushuntirildi")
        return

    # 5-HOLAT: Mijoz boshqa oddiy matn/salom yozsa ham javobsiz qolmasin
    if config_state.get("auto_reply", True) and text and not lead.get("general_replied"):
        async with client.action(event.chat_id, "typing"):
            await asyncio.sleep(2)
            lead_cat = lead.get("category", "")
            try:
                prompt = (
                    f"Mijozning biznesi/joyi: '{target_name}' (sohasi: '{lead_cat or 'biznes'}').\n"
                    f"Mijoz bizning taklifimizga shunday javob yozdi: '{text}'.\n"
                    f"Unga tirik inson Muhammadrizo nomidan qisqa, samimiy javob ber va bepul sayt namunasini tayyorlab ko'rsatishni taklif qil."
                )
                reply_text = await call_gemini(prompt, chat_id=None, system_instruction=CLIENT_SALES_SYSTEM_PROMPT)
            except Exception:
                reply_text = (
                    f"Assalomu alaykum! Men Muhammadrizoman.\n"
                    f"Sizning biznesingizga mos chiroyli veb-sayt va reklama tayyorlab berishni taklif qilgan edim.\n"
                    f"Xohlasangiz avval hech qanday to'lovsiz bitta namuna tayyorlab ko'rsataman, yoqsa keyin kelishamiz. Ko'raylikmi?"
                )
            await event.reply(reply_text)
            lead["general_replied"] = True
            save_ad_leads(ad_leads)
            if bot_ctx.get("notify_bot_owner"):
                await bot_ctx["notify_bot_owner"](
                    f"💬 **MIJOZ XABAR YOZDI (AVTO-JAVOB BERILDI)**\n👤 **Mijoz:** {target_name}\n💬 **Xabari:** `{text[:150]}`",
                    buttons=[[Button.inline("👤 Mijozni ko'rish", f"ld:{sender_id}".encode()), Button.inline("👥 CRM Baza", b"m:crm")]]
                )
            log_event("💬 MIJOZGA JAVOB", str(event.chat_id), "[bold cyan]YUBORILDI ✅[/bold cyan]", f"Mijoz: '{text[:20]}...'")
        return


# ==============================================================================
# 💬 9. SAQLANGAN XABARLAR (GEMINI AI SHAXSIY ASISTENT)
# ==============================================================================
@client.on(events.NewMessage(chats="me", outgoing=True))
async def handle_saved_messages(event):
    if event.id in sent_message_ids:
        return

    text = (event.message.message or "").strip()

    # O'zimizning tizim xabarlari va buyruqlarni o'tkazib yuborish
    skip_prefixes = ("✨ **Gemini:**", ".reklama", ".start", ".stop", ".mijoz", ".lead", ".papka", ".setbot", ".setkanal",
                     "🔥 **TABRIKLAYMIZ", "🔥 **KLIENT HA DEDI", "📁 **[MIJOZ", "💡 **MIJOZ", "🏁 **Google Maps",
                     "🔍 **Google Maps", "✅ **Google Maps", "⚠️ **DIQQAT", "🤖 **Tugmali Bot")
    if text.startswith(skip_prefixes):
        return

    if text in [".clear", ".tozala"]:
        chat_sessions.pop(event.chat_id, None)
        sent = await event.reply("🧹 **[Gemini] Muloqot konteksti tozalandi!**")
        sent_message_ids.add(sent.id)
        log_event("🧹 .CLEAR", "Saved Messages", "[cyan]TOZALANDI[/cyan]", "Kontekst xotirasi yangilandi")
        return

    if text in [".help", ".yordam"]:
        help_msg = (
            "✨ **GEMINI TELEGRAM USERBOT IMKONIYATLARI**\n\n"
            "🗺️ **1. Google Maps Avto-Reklama:**\n"
            "• `.start reklama` yoki `.start reklama restoran` — Veb-sayti yo'q restoranlarni topib reklama yuboradi.\n"
            "• `.start reklama stomatologiya` / `kafe` / `go'zallik saloni` / `avtoservis` — Istalgan soha bo'yicha topish.\n"
            "• `.start reklama turli xil` (yoki `.start reklama turli xil 10`) — Turli xil sohalardan aralash mijozlar topib yuborish.\n"
            "• `.start reklama restoran, kafe, klinika 9` — Bir nechta sohani vergul bilan berish.\n"
            "• `.stop reklama` — Jarayonni to'xtatish.\n\n"
            "🎯 **2. Qo'lda Reklama & Mijozlar:**\n"
            "• `.reklama +998951025599 Abduxoliq aka` — Bitta odamga samimiy taklif yuborish.\n"
            "• `.mijoz` — Chatni mijoz sifatida belgilab, fayllarini Saqlangan xabarlarga yig'ish.\n"
            "• `.mijozlar` yoki `.papka` — Barcha mijozlarni Telegramdagi alohida **'Mijozlar'** papkasiga yig'ish.\n\n"
            "🤖 **3. Tugmali Boshqaruv Boti:**\n"
            "• `.setbot <BOT_TOKEN>` — `@BotFather` tokeni orqali tugmali Telegram botni ulash.\n"
            "• `.setkanal <@kanal | off>` — Klient `HA` deganda xabarnoma boradigan Telegram kanal/guruhni ulash.\n\n"
            "🧠 **4. Gemini AI Muloqoti:**\n"
            "• **Saqlangan xabarlar**da savol yozing yoki rasm/PDF fayl tashlang.\n"
            "• `.ai <savol>` — Istalgan chatda Gemini javobini olish.\n"
            "• `.ping` — Tezlikni tekshirish."
        )
        sent = await event.reply(help_msg)
        sent_message_ids.add(sent.id)
        return

    if event.message.media:
        async with client.action("me", "document"):
            log_event("📁 MEDIA KELDI", "Saved Messages", "[bright_cyan]TAHLIL...[/bright_cyan]", "Fayl yuklanmoqda")
            try:
                file_bytes = await event.message.download_media(file=bytes)
                if file_bytes:
                    mime = "image/jpeg" if event.message.photo else "application/octet-stream"
                    if event.message.document and event.message.document.mime_type:
                        mime = event.message.document.mime_type
                    part = types.Part.from_bytes(data=file_bytes, mime_type=mime)
                    prompt = text if text else "Ushbu faylni batafsil tahlil qilib, professional xulosa ber."
                    answer = await call_gemini([part, prompt])
                    await reply_or_edit(event, f"{BOT_TAG}{answer}", edit=False)
                    log_event("📁 MEDIA YECHIMI", "Saved Messages", "[bright_green]BAJARILDI[/bright_green]", f"Fayl turi: {mime}")
            except Exception as e:
                await event.reply(f"⚠️ Faylni tahlil qilishda xato: {e}")
        return

    if not text:
        return

    async with client.action("me", "typing"):
        log_event("💡 SAVOL", "Saved Messages", "[bright_cyan]O'YLANMOQDA[/bright_cyan]", text[:30] + "...")
        try:
            answer = await call_gemini(text, chat_id=event.chat_id)
        except Exception as e:
            answer = f"⚠️ Gemini API xatolik qaytardi:\n`{e}`"
        await reply_or_edit(event, f"{BOT_TAG}{answer}", edit=False)
        log_event("💡 JAVOB", "Saved Messages", "[bright_green]YUBORILDI[/bright_green]", f"{len(answer)} belgi")


# ==============================================================================
# ⚡ 10. ISTALGAN CHATDA .ai VA .ping BUYRUQLARI
# ==============================================================================
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.ai(?:\s+([\s\S]+)|$)"))
async def handle_ai_inline(event):
    query = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()

    contents = []
    if reply and reply.media:
        await event.edit("⏳ **[Gemini] Fayl tahlil qilinmoqda...**")
        file_bytes = await reply.download_media(file=bytes)
        mime = reply.document.mime_type if (reply.document and reply.document.mime_type) else "image/jpeg"
        part = types.Part.from_bytes(data=file_bytes, mime_type=mime)
        contents = [part, query if query else "Ushbu media faylni tahlil qil."]
    elif reply and reply.message:
        contents = f"Quyidagi xabar bo'yicha vazifa: '{query}'\n\nXabar:\n{reply.message}" if query else reply.message
    elif query:
        contents = query
    else:
        await event.edit("⚠️ **Foydalanish:** `.ai <savol>` yoki xabarga reply qilib `.ai`")
        return

    await event.edit("⏳ **[Gemini] O'ylamoqda...**")
    try:
        answer = await call_gemini(contents)
    except Exception as e:
        answer = f"⚠️ Xato: {e}"
    await reply_or_edit(event, f"{BOT_TAG}{answer}", edit=True)
    log_event("⚡ .AI BUYRUQ", str(event.chat_id), "[bright_green]BAJARILDI[/bright_green]", "Javob xabarga joylandi")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.ping$"))
async def handle_ping(event):
    start = time.time()
    await event.edit("🏓 Pinging...")
    latency = (time.time() - start) * 1000
    await event.edit(f"✨ **Gemini Online!**\n⚡ **Ping:** `{latency:.2f} ms`\n🧠 **Model:** `{config_state['model']}`")
    log_event("🏓 .PING", str(event.chat_id), "[bright_green]OK[/bright_green]", f"{latency:.2f}ms")


async def start_controller_bot(token: str, me):
    """Tugmali Telegram Controller Botni ishga tushiradi va egasiga Bosh menyuni yuboradi."""
    token = (token or "").strip()
    if not token or ":" not in token:
        return None

    _bot_session = StringSession(BOT_SESSION) if BOT_SESSION else os.path.join(BASE_DIR, "gemini_bot_session")
    bot_client = TelegramClient(
        _bot_session,
        API_ID,
        API_HASH,
        connection_retries=-1,
        retry_delay=5,
        auto_reconnect=True,
    )
    await bot_client.start(bot_token=token)
    bot_me = await bot_client.get_me()

    # Telegram Bot Commands menyusini o'rnatish ('/' bosganda barcha buyruqlar avtomatik ko'rinadi)
    try:
        from telethon.tl.functions.bots import SetBotCommandsRequest
        from telethon.tl.types import BotCommand, BotCommandScopeDefault
        await bot_client(SetBotCommandsRequest(
            scope=BotCommandScopeDefault(),
            lang_code="",
            commands=[
                BotCommand(command="start", description="🚀 Asosiy boshqaruv paneli"),
                BotCommand(command="reklama", description="📢 Google Maps qidiruv & reklama"),
                BotCommand(command="mijozlar", description="👥 Mijozlar CRM bazasi"),
                BotCommand(command="export", description="📥 Excel / CSV bazani yuklash"),
                BotCommand(command="followup", description="🔄 Javob bermaganlarga eslatma"),
                BotCommand(command="proposal", description="💼 Tijoriy taklif & narxlar"),
                BotCommand(command="status", description="📊 Tizim va server holati"),
                BotCommand(command="sozlamalar", description="⚙️ Hudud va oraliq sozlamalari"),
                BotCommand(command="stop", description="🛑 Faol qidiruvni to'xtatish"),
                BotCommand(command="help", description="❓ Botdan foydalanish qo'llanmasi"),
            ]
        ))
    except Exception as _e:
        log_event("⚠️ BOT COMMANDS", getattr(bot_me, "username", "Bot"), "[yellow]WARN[/yellow]", str(_e))

    ctx = {
        "owner_id": me.id,
        "config_state": config_state,
        "ad_leads": ad_leads,
        "save_ad_leads": save_ad_leads,
        "save_settings": save_settings,
        "parse_location_input": parse_location_input,
        "generate_web_ad": generate_web_ad,
        "send_to_recipient": send_to_recipient,
        "move_chat_to_mijozlar": move_chat_to_mijozlar,
        "sync_all_leads_to_mijozlar": sync_all_leads_to_mijozlar,
        "run_outreach_campaign": run_outreach_campaign,
        "call_gemini": call_gemini,
        "genai_types": types,
        "chat_sessions": chat_sessions,
        "log_event": log_event,
        "CLIENT_FILES_DIR": CLIENT_FILES_DIR,
    }
    register_bot_handlers(bot_client, client, ctx)
    bot_ctx["bot_client"] = bot_client
    bot_ctx["notify_bot_owner"] = ctx.get("notify_bot_owner")

    bot_uname = f"@{bot_me.username}" if bot_me and bot_me.username else "Bot"
    log_event("🤖 CONTROLLER BOT", bot_uname, "[bold bright_green]TAYYOR ✅[/bold bright_green]", "Tugmali Telegram Bot ishga tushdi!")

    try:
        await bot_client.send_message(me.id, "🎛️ **Tugmali boshqaruv botingiz ishga tushdi!**", buttons=main_reply_keyboard())
        dash_text, dash_btns = _build_dashboard(ctx)
        await bot_client.send_message(me.id, dash_text, buttons=dash_btns)
    except Exception:
        # Ega hali botga /start bosmagan bo'lsa, Saqlangan xabarlarga havola yuboramiz
        if bot_me and bot_me.username:
            await client.send_message(
                'me',
                f"🤖 **Tugmali Bot tayyor!** Boshqarish uchun botga kirib **/start** bosing:\n👉 https://t.me/{bot_me.username}"
            )
    return bot_client


@client.on(events.NewMessage(outgoing=True, pattern=r"^\.setkanal(?:\s+([^\s]+))?$"))
async def handle_setkanal_command(event):
    kanal = (event.pattern_match.group(1) or "").strip()
    if not kanal:
        cur = config_state.get("alert_channel") or "O'rnatilmagan"
        await event.edit(
            f"📢 **Xabarnoma Kanali:** `{cur}`\n\n"
            "O'rnatish: `.setkanal @kanal_username` (yoki `-100...` ID)\n"
            "O'chirish: `.setkanal off`"
        )
        return
    if kanal.lower() in ("off", "yoq", "none", "o'chir"):
        config_state["alert_channel"] = ""
        save_settings()
        await event.edit("✅ Xabarnoma kanali o'chirildi (xabarlar faqat botga keladi).")
        return
    config_state["alert_channel"] = kanal
    save_settings()
    await event.edit(f"✅ **Xabarnoma kanali o'rnatildi:** `{kanal}`\nEndi klient 'HA' desa botga ham, shu kanalga ham xabar boradi!")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.setbot(?:\s+([^\s]+))?$"))
async def handle_setbot_command(event):
    token = (event.pattern_match.group(1) or "").strip()
    if not token or ":" not in token:
        await event.edit(
            "⚠️ **Foydalanish:** `.setbot <BOT_TOKEN>`\n\n"
            "Tokenni olish uchun Telegramda `@BotFather` ga kirib `/newbot` bosing va berilgan tokenni shu yerga yozing!"
        )
        return

    await event.edit("⏳ Tugmali Telegram Bot ulanmoqda...")
    try:
        if bot_ctx.get("bot_client"):
            try:
                await bot_ctx["bot_client"].disconnect()
            except Exception:
                pass
        save_env_key("BOT_TOKEN", token)
        me = await client.get_me()
        bc = await start_controller_bot(token, me)
        if bc:
            asyncio.create_task(bc.run_until_disconnected())
            bot_me = await bc.get_me()
            bot_link = f"https://t.me/{bot_me.username}" if bot_me and bot_me.username else "bot"
            await event.edit(
                f"✅ **Tugmali Bot muvaffaqiyatli ulandi va `.env` ga saqlandi!**\n"
                f"👉 Botni ochib `/start` bosing: {bot_link}"
            )
        else:
            await event.edit("❌ Token noto'g'ri ko'rinadi, tekshirib qayta kiriting.")
    except Exception as e:
        await event.edit(f"❌ Botni ulashda xatolik:\n`{e}`")


# ==============================================================================
# 🚀 11. ASOSIY ISHGA TUSHIRISH & RENDER / BULUT ENTRYPOINT
# ==============================================================================
import threading

_bot_thread_started = False
_bot_thread_lock = threading.Lock()

def _run_telethon_bot():
    try:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        new_loop.run_until_complete(main())
    except Exception as exc:
        print(f"[Cloud Background] Bot xatosi: {exc}")

def _ensure_bot_thread():
    global _bot_thread_started
    with _bot_thread_lock:
        if not _bot_thread_started:
            _bot_thread_started = True
            t = threading.Thread(target=_run_telethon_bot, daemon=True, name="TelethonBotThread")
            t.start()

def start_flask_server():
    """Render/Koyeb uchun Flask web-server — UptimeRobot ping'lari uchun."""
    try:
        from flask import Flask, jsonify
    except ImportError:
        print("[Flask] flask o'rnatilmagan, web-server o'tkazib yuborildi")
        return

    flask_app = Flask(__name__)

    @flask_app.route("/")
    def health_check():
        return jsonify({
            "status": "online",
            "bot": "@mrizosreklama_bot",
            "system": "JARVIS Telegram Automation Suite",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    @flask_app.route("/health")
    def health():
        return "OK", 200

    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

# Vercel serverless uchun (agar kerak bo'lsa)
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        _ensure_bot_thread()
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        resp = {
            "status": "online",
            "bot": "@mrizosreklama_bot",
            "system": "JARVIS Telegram Automation Suite",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))

    def do_POST(self):
        _ensure_bot_thread()
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

app = handler
application = handler


async def main():
    try:
        console.clear()
    except Exception:
        pass
    print_banner()

    console.print("[bold bright_cyan]⚡ Telegram tarmog'iga ulanmoqda...[/bold bright_cyan]")
    console.print("[grey50](Agar birinchi marta bo'lsa, quyida telefon raqamingiz va Telegram kodini kiriting)[/grey50]\n")

    await client.start()
    me = await client.get_me()

    global BOT_TOKEN
    if not BOT_TOKEN and sys.stdin.isatty():
        console.print("\n[bold bright_cyan]🤖 TUGMALI TELEGRAM BOT SOZLAMASI[/bold bright_cyan]")
        console.print("[grey70]@BotFather'dan olingan BOT_TOKEN kiritsangiz, to'liq tugmali bot ham birga ochiladi.[/grey70]")
        entered = console.input("[bright_yellow]BOT_TOKEN (yoki o'tkazib yuborish uchun Enter bosing): [/bright_yellow]").strip()
        if entered and ":" in entered:
            BOT_TOKEN = entered
            save_env_key("BOT_TOKEN", BOT_TOKEN)

    bot_client = None
    if BOT_TOKEN:
        try:
            bot_client = await start_controller_bot(BOT_TOKEN, me)
        except Exception as be:
            console.print(f"[bold red]⚠️ Controller Botni ulashda xatolik:[/bold red] {be}")

    console.clear()
    print_banner()
    print_user_info(me, config_state["model"])

    bot_status_line = (
        "[bold bright_green]🤖 Tugmali Controller Bot: FAOL (Telegramda /start bosing!)[/bold bright_green]"
        if bot_client else
        "[yellow]🤖 Tugmali Bot ulanmagan: Telegramda [bold].setbot <TOKEN>[/bold] yozing yoki .env ga BOT_TOKEN qo'shing.[/yellow]"
    )

    console.print(Panel(
        "[bold bright_green]🚀 GEMINI TAYYOR VA XABARLARNI KUTMOQDA![/bold bright_green]\n"
        "[bright_cyan]Google Maps avto-reklama uchun Telegramda: [bold].start reklama[/bold] deb yozing![/bright_cyan]\n"
        f"{bot_status_line}",
        border_style="bright_green",
        box=box.ROUNDED
    ))
    console.print()
    console.print("[bold bright_blue]─── JONLI HODISALAR JURNALI (LIVE LOGS) ──────────────────────────────────[/bold bright_blue]")

    if not bot_client:
        try:
            await client.send_message(
                'me',
                "🤖 **Tugmali Telegram Botni ulash uchun:**\n"
                "1. `@BotFather` ga kirib `/newbot` orqali token oling.\n"
                "2. Shu yerga `.setbot <TOKEN>` deb yuboring — darrov tugmali bot ishga tushadi!"
            )
        except Exception:
            pass
        await client.run_until_disconnected()
    else:
        await asyncio.gather(
            client.run_until_disconnected(),
            bot_client.run_until_disconnected()
        )

if __name__ == "__main__":
    # Bulutda (Render/Docker) ishga tushadigan bo'lsa Flask web-serverni ham yoqamiz
    is_cloud = os.environ.get("RENDER") or os.environ.get("PORT") or os.environ.get("DOCKER_ENV")
    if is_cloud:
        # 1) Flask web-serverni alohida threadda ishga tushiramiz (UptimeRobot ping'lari uchun)
        flask_thread = threading.Thread(target=start_flask_server, daemon=True, name="FlaskHealthServer")
        flask_thread.start()

    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]🛑 Gemini Userbot to'xtatildi.[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Kritik xatolik:[/bold red] {e}")
