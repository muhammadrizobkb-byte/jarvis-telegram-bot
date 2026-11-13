"""
================================================================================
  🤖 TUGMALI TELEGRAM BOT BOSHQARUV PANELI (CONTROLLER BOT UI)
================================================================================
Userbot (Telethon shaxsiy akkaunt) bilan birgalikda ishlaydigan to'liq tugmali
Telegram Bot interfeysi:
  • 🗺️ Google Maps Avto-Reklama (Soha -> Hudud -> Miqdor -> Jonli Progress)
  • 🎯 Qo'lda Reklama Usta (Raqam/@username -> Ism/Soha -> Ko'rib chiqish -> Yuborish)
  • 👥 Mini-CRM Mijozlar Bazasi (Rozi bo'lganlar, Kutilmoqda, Fayllarni yuklash)
  • 📊 Real-vaqt Statistika va 'Mijozlar' papkasini sinxronlash
  • ⚙️ Bot Sozlamalari (Tanaffus tezligi, Avto-javob, Model, Hudud koordinatasi)
  • 🧠 Multimodal Gemini AI Chat
================================================================================
"""

import os
import asyncio
from datetime import datetime
from telethon import events, Button

CATEGORY_PRESETS = [
    ("🦷 Stomatologiya", "stomatologiya"),
    ("🏥 Klinika", "klinika"),
    ("🍽️ Restoran", "restoran"),
    ("☕ Kafe", "kafe"),
    ("💇 Go'zallik saloni", "go'zallik saloni"),
    ("💈 Sartaroshxona", "sartaroshxona"),
    ("🚗 Avtoservis", "avtoservis"),
    ("🎓 O'quv markaz", "o'quv markaz"),
    ("🛋️ Mebel", "mebel"),
    ("🏨 Mehmonxona", "mehmonxona"),
    ("🏋️ Fitnes / Sport", "fitnes"),
    ("💐 Gul do'koni", "gul do'koni"),
    ("📸 Foto / Video", "foto studiya"),
    ("🛍️ Do'kon", "do'kon"),
    ("🌐 Har xillari (Aralash)", "turli xil"),
]

CITY_PRESETS = [
    ("📍 Hozirgi hudud (Default)", ""),
    ("🏙️ Toshkent", "toshkent"),
    ("🏛️ Samarqand", "samarqand"),
    ("🌿 Farg'ona", "farg'ona"),
    ("🌄 Namangan", "namangan"),
    ("🍎 Andijon", "andijon"),
]

DELAY_PROFILES = [
    ("Tezkor (10-16s)", 10.0, 16.0),
    ("Xavfsiz (14-24s)", 14.0, 24.0),
    ("Sekin (25-40s)", 25.0, 40.0),
]

MODEL_CHOICES = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
]


def main_reply_keyboard():
    return [
        [Button.text("📢 Reklama", resize=True), Button.text("🎯 Qo'lda Yuborish", resize=True)],
        [Button.text("👥 Mijozlar CRM", resize=True), Button.text("📊 Statistika", resize=True)],
        [Button.text("⚙️ Sozlamalar", resize=True), Button.text("🧠 Gemini AI", resize=True)],
    ]


async def safe_edit(event, text: str, buttons=None, parse_mode="md"):
    try:
        return await event.edit(text, buttons=buttons, parse_mode=parse_mode)
    except Exception as e:
        err_l = str(e).lower()
        if "not modified" in err_l:
            return None
        try:
            return await event.respond(text, buttons=buttons, parse_mode=parse_mode)
        except Exception:
            return await event.respond(text, buttons=buttons, parse_mode=None)


def _compute_stats(ad_leads: dict) -> dict:
    total_leads = 0
    agreed = 0
    explained = 0
    refused_followed = 0
    waiting = 0
    for k, v in ad_leads.items():
        if k == "contacted_phones" or not isinstance(v, dict):
            continue
        total_leads += 1
        if v.get("agreed"):
            agreed += 1
        elif v.get("followup_sent"):
            refused_followed += 1
        else:
            waiting += 1
        if v.get("details_explained"):
            explained += 1
    contacted_phones = len(ad_leads.get("contacted_phones", []))
    return {
        "total_leads": total_leads,
        "contacted_phones": contacted_phones,
        "agreed": agreed,
        "explained": explained,
        "refused_followed": refused_followed,
        "waiting": waiting,
    }


def _build_dashboard(ctx: dict):
    config_state = ctx["config_state"]
    ad_leads = ctx["ad_leads"]
    stats = _compute_stats(ad_leads)
    status_badge = "🟢 FAOL ISHLAMOQDA" if config_state.get("campaign_running") else "⚪ KUTISH REJIMIDA"

    text = (
        f"🎛️ **BOSH BOSHQARUV PANELI**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ **Holat:** {status_badge}\n"
        f"📍 **Hudud:** `{config_state.get('location_label', 'Andijon')}`\n"
        f"📊 **Yuborilgan chatlar:** `{stats['total_leads']}` ta (`{stats['contacted_phones']}` raqam)\n"
        f"🔥 **Rozi bo'lgan mijozlar:** `{stats['agreed']}` ta\n"
        f"⏳ **Javob kutilayotgan:** `{stats['waiting']}` ta\n"
        f"🧠 **AI Model:** `{config_state.get('model')}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Quyidagi tugmalardan kerakli bo'limni tanlang:"
    )

    buttons = []
    if config_state.get("campaign_running"):
        buttons.append([Button.inline("🛑 Reklamani Darhol To'xtatish", b"m:stop")])
    buttons.extend([
        [Button.inline("📢 Reklama (Google Maps'dan izlash)", b"m:maps")],
        [Button.inline("🎯 Bitta Odamga Yuborish", b"m:manual"), Button.inline("👥 Mijozlar CRM", b"m:crm")],
        [Button.inline("💼 'Mijozlar' Papkasini Yangilash", b"m:sync")],
        [Button.inline("📊 Batafsil Statistika", b"m:stats"), Button.inline("⚙️ Sozlamalar", b"m:settings")],
        [Button.inline("🧠 Gemini AI Bilan Suhbat", b"m:ai")],
    ])
    return text, buttons


def register_bot_handlers(bot_client, user_client, ctx: dict):
    """
    Controller bot uchun barcha tugma va menyu handlerlarini ro'yxatdan o'tkazadi.
    """
    owner_id = ctx["owner_id"]
    config_state = ctx["config_state"]
    ad_leads = ctx["ad_leads"]

    # Foydalanuvchi holatlari (wizard & settings & AI mode)
    user_state = {
        "mode": None,  # custom_cat | custom_city | man_target | man_title | set_loc | ai
        "maps_cat": "restoran",
        "maps_city": "",
        "maps_count": 5,
        "man_target": "",
        "man_title": "",
    }
    bot_chat_id_key = -999999  # Bot AI suhbati uchun alohida sessiya kaliti

    def is_owner(event) -> bool:
        return event.sender_id == owner_id

    async def notify_owner_event(message_text: str, buttons=None):
        """Userbot muhim mijoz hodisalarini egasiga va xabarnoma kanaliga yuboradi."""
        try:
            await bot_client.send_message(owner_id, message_text, buttons=buttons, parse_mode="md")
        except Exception:
            pass

        alert_channel = str(config_state.get("alert_channel", "") or "").strip()
        if alert_channel:
            target = int(alert_channel) if alert_channel.lstrip("-").isdigit() else alert_channel
            try:
                await bot_client.send_message(target, message_text, buttons=buttons, parse_mode="md")
            except Exception:
                try:
                    # Inline bot tugmalarini oddiy userbot yubora olmaydi, shuning uchun matnni o'zini yuboramiz
                    await user_client.send_message(target, message_text, parse_mode="md")
                except Exception:
                    pass

    ctx["notify_bot_owner"] = notify_owner_event

    # --------------------------------------------------------------------------
    # /start va Asosiy Reply tugmalar
    # --------------------------------------------------------------------------
    @bot_client.on(events.NewMessage(pattern=r"^/start$"))
    async def bot_start(event):
        if not is_owner(event):
            await event.reply("⛔ Kechirasiz, bu shaxsiy boshqaruv boti faqat egasi uchun ishlaydi.")
            return
        user_state["mode"] = None
        await event.respond("🎛️ **Tizim paneli faollashtirildi!** Pastdagi doimiy tugmalardan ham foydalanishingiz mumkin.", buttons=main_reply_keyboard())
        text, buttons = _build_dashboard(ctx)
        await event.respond(text, buttons=buttons)

    @bot_client.on(events.NewMessage(incoming=True))
    async def bot_text_router(event):
        if not is_owner(event):
            return

        text = (event.raw_text or "").strip()
        if text == "/start":
            return

        # Pastki doimiy Reply Keyboard tugmalarini tekshirish
        if text in ("📢 Reklama", "🗺️ Avto-Reklama"):
            user_state["mode"] = None
            await _show_category_picker(event, is_edit=False)
            return
        if text == "🎯 Qo'lda Yuborish":
            user_state["mode"] = "man_target"
            await event.respond(
                "🎯 **Bitta odamga samimiy taklif yuborish**\n\n"
                "1-qadam: Mijozning **telefon raqamini** (`+998901234567`) yoki **@username** ini yuboring:",
                buttons=[[Button.inline("❌ Bekor qilish", b"m:home")]]
            )
            return
        if text == "👥 Mijozlar CRM":
            user_state["mode"] = None
            await _show_crm_list(event, filter_type="all", page=0, is_edit=False)
            return
        if text == "📊 Statistika":
            user_state["mode"] = None
            await _show_stats_screen(event, is_edit=False)
            return
        if text == "⚙️ Sozlamalar":
            user_state["mode"] = None
            await _show_settings_screen(event, is_edit=False)
            return
        if text == "🧠 Gemini AI":
            user_state["mode"] = "ai"
            await event.respond(
                f"🧠 **Gemini AI Rejimi Faollashdi** (`{config_state.get('model')}`)\n\n"
                "Istalgan savolingizni yozing yoki rasm/hujjat tashlang!\n"
                "Chiqish uchun **🏠 Bosh menyu** tugmasini bosing.",
                buttons=[
                    [Button.inline("🧹 Suhbat xotirasini tozalash", b"ai:clear")],
                    [Button.inline("🏠 Bosh menyu", b"m:home")],
                ]
            )
            return

        # Wizard / Interactive holatlarni boshqarish
        mode = user_state.get("mode")

        if mode == "custom_cat":
            if not text:
                await event.reply("⚠️ Iltimos, soha nomini matn ko'rinishida yuboring.")
                return
            user_state["maps_cat"] = text
            user_state["maps_count"] = 8 if "xil" in text.lower() else 5
            user_state["mode"] = None
            await _show_maps_confirm(event, is_edit=False)
            return

        if mode == "custom_city":
            user_state["maps_city"] = text
            user_state["mode"] = None
            await _show_maps_confirm(event, is_edit=False)
            return

        if mode == "man_target":
            if not text:
                await event.reply("⚠️ Iltimos, raqam yoki @username yozing.")
                return
            user_state["man_target"] = text
            user_state["mode"] = "man_title"
            await event.respond(
                f"✅ Qabul qiluvchi: `{text}`\n\n"
                "2-qadam: Mijozning **ismi yoki kasbini** yozing (masalan: `Abduxoliq aka santexnik`), "
                "yoki nomsiz yuborish uchun pastdagi tugmani bosing:",
                buttons=[
                    [Button.inline("⏭️ Ismsiz davom etish", b"man:skip_title")],
                    [Button.inline("❌ Bekor qilish", b"m:home")],
                ]
            )
            return

        if mode == "man_title":
            user_state["man_title"] = text
            user_state["mode"] = None
            await _show_manual_preview(event, is_edit=False)
            return

        if mode == "set_loc":
            # Koordinata yoki Google Maps havolasidan lat/lon ajratib olishga urinamiz
            lat, lon, label = ctx["parse_location_input"](text)
            if lat is not None and lon is not None:
                config_state["lat"] = lat
                config_state["lon"] = lon
                config_state["location_label"] = label
                ctx["save_settings"]()
                user_state["mode"] = None
                await event.respond(
                    f"✅ **Default hudud yangilandi!**\n📍 Manzil: `{label}` (`{lat}, {lon}`)",
                    buttons=[[Button.inline("⚙️ Sozlamalarga qaytish", b"m:settings")]]
                )
            else:
                await event.reply(
                    "⚠️ Koordinata topilmadi. Masalan: `40.7639, 72.3623` yoki Google Maps URL (`https://www.google.com/maps/@40.76,72.36...`) yuboring."
                )
            return

        if mode == "set_kanal":
            kanal_input = text.strip()
            if kanal_input.lower() in {"off", "ochir", "o'chir", "yoq", "yo'q", "clear", "none"}:
                config_state["alert_channel"] = ""
                save_settings()
                user_state["mode"] = "ai"
                await event.reply("🔕 Xabarnoma kanali o'chirildi. Endi xabarlar faqat botning o'ziga keladi.")
                await _show_settings_screen(event, is_edit=False)
                return

            target_chan = int(kanal_input) if kanal_input.lstrip("-").isdigit() else kanal_input
            test_ok = False
            via = ""
            try:
                await bot_client.send_message(target_chan, "✅ Xabarnoma kanali muvaffaqiyatli ulandi! Yangi klient `HA` desa shu yerga darhol keladi.")
                test_ok = True
                via = "Bot orqali"
            except Exception:
                try:
                    await user_client.send_message(target_chan, "✅ Xabarnoma kanali muvaffaqiyatli ulandi! Yangi klient `HA` desa shu yerga darhol keladi.")
                    test_ok = True
                    via = "Userbot orqali"
                except Exception as exc:
                    await event.reply(
                        f"❌ `{kanal_input}` kanal/guruhiga yozib bo'lmadi: `{exc}`\n\n"
                        "Botni (yoki akkauntingizni) o'sha kanalga Admin qilib qo'shing va qayta urinib ko'ring (`@kanal` yoki `-100...` ID)."
                    )
                    return

            if test_ok:
                config_state["alert_channel"] = str(target_chan)
                save_settings()
                user_state["mode"] = "ai"
                await event.reply(f"✅ Xabarnoma kanali saqlandi (`{target_chan}`, {via})!")
                await _show_settings_screen(event, is_edit=False)
            return

        if mode == "ai" or event.message.media or (text and not text.startswith("/")):
            # Agar AI rejimida bo'lsa yoki foydalanuvchi to'g'ridan-to'g'ri savol/rasm tashlasa
            await _handle_bot_ai_query(event, text)

    async def _handle_bot_ai_query(event, text: str):
        async with bot_client.action(event.chat_id, "typing"):
            try:
                if event.message.media:
                    file_bytes = await event.message.download_media(file=bytes)
                    mime = "image/jpeg" if event.message.photo else "application/octet-stream"
                    if event.message.document and event.message.document.mime_type:
                        mime = event.message.document.mime_type
                    part = ctx["genai_types"].Part.from_bytes(data=file_bytes, mime_type=mime)
                    prompt = text if text else "Ushbu faylni batafsil tahlil qilib, aniq xulosa ber."
                    answer = await ctx["call_gemini"]([part, prompt])
                else:
                    answer = await ctx["call_gemini"](text, chat_id=bot_chat_id_key)
            except Exception as e:
                answer = f"⚠️ Gemini API xatolik qaytardi:\n`{e}`"

        MAX_CHUNK = 3900
        chunks = [answer[i:i + MAX_CHUNK] for i in range(0, len(answer), MAX_CHUNK)] or [answer]
        for i, ch in enumerate(chunks):
            btns = [[Button.inline("🧹 Tozalash", b"ai:clear"), Button.inline("🏠 Menyu", b"m:home")]] if i == len(chunks) - 1 else None
            try:
                await event.reply(ch, buttons=btns, parse_mode="md")
            except Exception:
                await event.reply(ch, buttons=btns, parse_mode=None)

    # --------------------------------------------------------------------------
    # Yordamchi Ekran Render Funksiyalari
    # --------------------------------------------------------------------------
    async def _show_category_picker(event, is_edit: bool = True):
        text = (
            "📢 **QAYSI XILIGA REKLAMA QILAMIZ?**\n\n"
            "Kerakli sohani tanlang — Google Maps'dan veb-sayti yo'q joylarni izlab topib beraman:"
        )
        rows = []
        for i in range(0, len(CATEGORY_PRESETS) - 1, 2):
            rows.append([
                Button.inline(CATEGORY_PRESETS[i][0], f"c:{i}".encode()),
                Button.inline(CATEGORY_PRESETS[i + 1][0], f"c:{i + 1}".encode()),
            ])
        # Oxirgi "Har xillari" + "Boshqa soha"
        rows.append([
            Button.inline(CATEGORY_PRESETS[-1][0], f"c:{len(CATEGORY_PRESETS) - 1}".encode()),
            Button.inline("✏️ Boshqa soha yozish", b"c:custom"),
        ])
        rows.append([Button.inline("⬅️ Bosh menyu", b"m:home")])

        if is_edit:
            await safe_edit(event, text, buttons=rows)
        else:
            await event.respond(text, buttons=rows)

    async def _show_city_picker(event, is_edit: bool = True):
        text = (
            f"📍 **SHAHAR / HUDUDNI TANLANG**\n\n"
            f"Tanlangan soha: `{user_state['maps_cat']}`\n"
            f"Default hudud: `{config_state.get('location_label', 'Andijon')}`"
        )
        rows = []
        for i in range(0, len(CITY_PRESETS), 2):
            row = [Button.inline(CITY_PRESETS[i][0], f"l:{i}".encode())]
            if i + 1 < len(CITY_PRESETS):
                row.append(Button.inline(CITY_PRESETS[i + 1][0], f"l:{i + 1}".encode()))
            rows.append(row)
        rows.append([Button.inline("✏️ Boshqa shahar yozish", b"l:custom")])
        rows.append([Button.inline("⬅️ Orqaga", b"l:back_confirm"), Button.inline("🏠 Menyu", b"m:home")])

        if is_edit:
            await safe_edit(event, text, buttons=rows)
        else:
            await event.respond(text, buttons=rows)

    async def _show_count_picker(event, is_edit: bool = True):
        city_txt = user_state["maps_city"] or f"Default ({config_state.get('location_label', 'Andijon')})"
        text = (
            f"🔢 **NECHTA JOYGA YUBORILSIN?**\n\n"
            f"📌 **Soha:** `{user_state['maps_cat']}`\n"
            f"📍 **Hudud:** `{city_txt}`\n\n"
            f"Xavfsizlik uchun optimal limitni tanlang:"
        )
        buttons = [
            [Button.inline("3 ta", b"n:3"), Button.inline("5 ta", b"n:5"), Button.inline("8 ta", b"n:8")],
            [Button.inline("10 ta", b"n:10"), Button.inline("15 ta", b"n:15")],
            [Button.inline("⬅️ Orqaga", b"l:back_confirm"), Button.inline("🏠 Menyu", b"m:home")],
        ]
        if is_edit:
            await safe_edit(event, text, buttons=buttons)
        else:
            await event.respond(text, buttons=buttons)

    async def _show_maps_confirm(event, is_edit: bool = True):
        city_txt = user_state["maps_city"] or f"Default ({config_state.get('location_label', 'Andijon')})"
        full_q = f"{user_state['maps_city']} {user_state['maps_cat']}".strip() if user_state["maps_city"] else user_state["maps_cat"]
        text = (
            f"🗺️ **GOOGLE MAPS'DAN IZLASHGA TAYYOR!**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 **Tanlangan soha:** `{full_q}`\n"
            f"📍 **Hudud:** `{city_txt}`\n"
            f"🔢 **Miqdor:** `{user_state['maps_count']} ta` veb-saytsiz biznes\n"
            f"⏱️ **Tanaffus:** `{int(config_state['delay_min'])}–{int(config_state['delay_max'])} soniya`\n"
            f"💼 **Papka:** `Mijozlar` ga avtomatik yig'iladi\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        buttons = [
            [Button.inline("🚀 Google Maps'dan Izlash va Yuborish", b"go:maps")],
            [Button.inline("📍 Shahar Tanlash", b"c:pick_city"), Button.inline("🔢 Soni Tanlash", b"l:back_count")],
            [Button.inline("⬅️ Boshqa Soha", b"m:maps"), Button.inline("🏠 Bosh menyu", b"m:home")],
        ]
        if is_edit:
            await safe_edit(event, text, buttons=buttons)
        else:
            await event.respond(text, buttons=buttons)

    async def _show_manual_preview(event, is_edit: bool = True):
        me = await user_client.get_me()
        owner_name = me.first_name if (me and me.first_name) else "Muhammadrizo"
        preview = ctx["generate_web_ad"](
            owner_name=owner_name,
            recipient_title=user_state["man_title"] or None,
            username=me.username if me else None,
            phone=me.phone if me else None,
        )
        text = (
            f"👁️ **YUBORILADIGAN XABAR KO'RINISHI**\n"
            f"🎯 **Kimga:** `{user_state['man_target']}`\n"
            f"👤 **Ism/Kasb:** `{user_state['man_title'] or 'Kiritilmagan'}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{preview}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        buttons = [
            [Button.inline("✅ Tasdiqlash va Yuborish", b"man:send")],
            [Button.inline("❌ Bekor qilish", b"m:home")],
        ]
        if is_edit:
            await safe_edit(event, text, buttons=buttons)
        else:
            await event.respond(text, buttons=buttons)

    def _get_filtered_leads(filter_type: str):
        items = []
        for cid, v in ad_leads.items():
            if cid == "contacted_phones" or not isinstance(v, dict):
                continue
            if filter_type == "yes" and not v.get("agreed"):
                continue
            if filter_type == "wait" and v.get("agreed"):
                continue
            items.append((cid, v))
        items.sort(key=lambda x: x[1].get("sent_time", ""), reverse=True)
        return items

    async def _show_crm_list(event, filter_type: str = "all", page: int = 0, is_edit: bool = True):
        items = _get_filtered_leads(filter_type)
        per_page = 6
        total = len(items)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(0, min(page, total_pages - 1))
        chunk = items[page * per_page:(page + 1) * per_page]

        filter_names = {"all": "Barchasi", "yes": "Rozi bo'lganlar 🔥", "wait": "Kutilmoqda ⏳"}
        text = (
            f"👥 **MIJOZLAR CRM BAZASI** ({filter_names.get(filter_type, 'Barchasi')})\n"
            f"📌 Jami: `{total}` ta | Sahifa: `{page + 1}/{total_pages}`\n\n"
            f"Batafsil ko'rish va fayllarini ochish uchun mijoz ustiga bosing:"
        )
        if not chunk:
            text += "\n\nℹ️ *Ushbu bo'limda hozircha mijozlar yo'q.*"

        buttons = [
            [
                Button.inline("📋 Barchasi", b"crm:all:0"),
                Button.inline("🔥 Rozi", b"crm:yes:0"),
                Button.inline("⏳ Kutilmoqda", b"crm:wait:0"),
            ]
        ]

        for cid, lead in chunk:
            icon = "🔥" if lead.get("agreed") else ("🔄" if lead.get("followup_sent") else "⏳")
            title = (lead.get("title") or lead.get("target") or cid)[:26]
            buttons.append([Button.inline(f"{icon} {title}", f"ld:{cid}".encode())])

        nav = []
        if page > 0:
            nav.append(Button.inline("⬅️ Oldingi", f"crm:{filter_type}:{page - 1}".encode()))
        if page + 1 < total_pages:
            nav.append(Button.inline("Keyingi ➡️", f"crm:{filter_type}:{page + 1}".encode()))
        if nav:
            buttons.append(nav)

        buttons.append([Button.inline("💼 'Mijozlar' Papkasiga Sinxronlash", b"m:sync")])
        buttons.append([Button.inline("🏠 Bosh menyu", b"m:home")])

        if is_edit:
            await safe_edit(event, text, buttons=buttons)
        else:
            await event.respond(text, buttons=buttons)

    async def _show_lead_detail(event, cid: str):
        lead = ad_leads.get(cid)
        if not isinstance(lead, dict):
            await safe_edit(event, "⚠️ Bu mijoz bazadan topilmadi.", buttons=[[Button.inline("⬅️ CRM ga qaytish", b"m:crm")]])
            return

        client_dir = os.path.join(ctx["CLIENT_FILES_DIR"], f"mijoz_{cid}")
        files_count = 0
        has_notes = False
        if os.path.isdir(client_dir):
            for fn in os.listdir(client_dir):
                if fn == "talablar.txt":
                    has_notes = True
                else:
                    files_count += 1

        status_str = "🔥 ROZI BO'LGAN (Faol mijoz)" if lead.get("agreed") else (
            "🔄 Rad etgan (Qayta tushuntirilgan)" if lead.get("followup_sent") else "⏳ Javob kutilmoqda"
        )
        text = (
            f"👤 **MIJOZ TAFSILOTLARI**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷️ **Nomi:** {lead.get('title') or 'Nomsiz'}\n"
            f"📞 **Manzil:** `{lead.get('target', cid)}`\n"
            f"📂 **Soha:** `{lead.get('category', 'umumiy')}`\n"
            f"📌 **Holat:** {status_str}\n"
            f"🕒 **Yuborilgan:** `{lead.get('sent_time', '-')}`\n"
            f"💾 **Saqlangan fayllar:** `{files_count}` ta | Matnli talab: `{'Bor ✅' if has_notes else 'Yoq'}`\n"
        )

        buttons = []
        if lead.get("maps_url"):
            buttons.append([Button.url("🗺️ Google Maps'da ochish", lead["maps_url"])])
        if not lead.get("agreed"):
            buttons.append([Button.inline("🔥 Faol Mijoz (HA) Qilish", f"la:ok:{cid}".encode())])
        buttons.append([
            Button.inline("📁 Fayl & Talablarni Olish", f"la:files:{cid}".encode()),
            Button.inline("💼 Papkaga Qo'shish", f"la:fld:{cid}".encode()),
        ])
        buttons.append([
            Button.inline("🗑️ O'chirish", f"la:del:{cid}".encode()),
            Button.inline("⬅️ Orqaga", b"crm:all:0"),
        ])
        await safe_edit(event, text, buttons=buttons)

    async def _show_stats_screen(event, is_edit: bool = True):
        s = _compute_stats(ad_leads)
        conv = (s["agreed"] / s["total_leads"] * 100) if s["total_leads"] else 0.0
        text = (
            f"📊 **REKLAMA VA MIJOZLAR STATISTIKASI**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📞 **Tekshirilgan / yozilgan raqamlar:** `{s['contacted_phones']}` ta\n"
            f"💬 **Jami mijoz chatlari:** `{s['total_leads']}` ta\n"
            f"🔥 **Rozi bo'lgan (HA) mijozlar:** `{s['agreed']}` ta\n"
            f"💡 **Batafsil tushuntirilgan:** `{s['explained']}` ta\n"
            f"🔄 **Rad etishga javob olgan:** `{s['refused_followed']}` ta\n"
            f"⏳ **Hali javob bermagan:** `{s['waiting']}` ta\n"
            f"📈 **Konversiya:** `{conv:.1f}%`\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        buttons = [
            [Button.inline("🔄 Yangilash", b"m:stats"), Button.inline("👥 CRM ga o'tish", b"m:crm")],
            [Button.inline("🏠 Bosh menyu", b"m:home")],
        ]
        if is_edit:
            await safe_edit(event, text, buttons=buttons)
        else:
            await event.respond(text, buttons=buttons)

    async def _show_settings_screen(event, is_edit: bool = True):
        ar = "✅ YOQILGAN" if config_state.get("auto_reply", True) else "❌ O'CHIRILGAN"
        af = "✅ YOQILGAN" if config_state.get("auto_folder", True) else "❌ O'CHIRILGAN"
        dmin = int(config_state.get("delay_min", 14))
        dmax = int(config_state.get("delay_max", 24))
        ak = config_state.get("alert_channel") or "Ulanmagan (faqat botga)"
        text = (
            f"⚙️ **TIZIM SOZLAMALARI**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 **Avto-javob (Mijoz yozsa):** {ar}\n"
            f"💼 **Avto 'Mijozlar' papkasi:** {af}\n"
            f"⏱️ **Tanaffus oralig'i:** `{dmin}–{dmax} soniya`\n"
            f"🧠 **Gemini AI Model:** `{config_state.get('model')}`\n"
            f"📍 **Default Hudud:** `{config_state.get('location_label', 'Andijon')}` (`{config_state.get('lat')}, {config_state.get('lon')}`)\n"
            f"📢 **Xabarnoma Kanali:** `{ak}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"O'zgartirish uchun kerakli tugmani bosing:"
        )
        buttons = [
            [Button.inline(f"🤖 Avto-javob: {ar}", b"s:autoreply")],
            [Button.inline(f"💼 Avto-Papka: {af}", b"s:autofolder")],
            [Button.inline(f"⏱️ Tanaffus: {dmin}-{dmax}s", b"s:delay"), Button.inline("🧠 AI Model", b"s:model")],
            [Button.inline("📍 Default Hudud / Maps Linkni O'zgartirish", b"s:loc")],
            [Button.inline("📢 Xabarnoma Kanali (Guruh/Kanal)", b"s:kanal")],
            [Button.inline("🏠 Bosh menyu", b"m:home")],
        ]
        if is_edit:
            await safe_edit(event, text, buttons=buttons)
        else:
            await event.respond(text, buttons=buttons)

    # --------------------------------------------------------------------------
    # Inline Callback Query Router
    # --------------------------------------------------------------------------
    @bot_client.on(events.CallbackQuery)
    async def bot_callback_handler(event):
        if not is_owner(event):
            await event.answer("⛔ Ruxsat yo'q!", alert=True)
            return

        data = event.data.decode("utf-8", errors="ignore")

        if data == "m:home":
            user_state["mode"] = None
            text, buttons = _build_dashboard(ctx)
            await safe_edit(event, text, buttons=buttons)
            await event.answer()
            return

        if data == "m:maps":
            user_state["mode"] = None
            await _show_category_picker(event, is_edit=True)
            await event.answer()
            return

        if data == "m:manual":
            user_state["mode"] = "man_target"
            await safe_edit(
                event,
                "🎯 **Bitta odamga samimiy taklif yuborish**\n\n"
                "1-qadam: Mijozning **telefon raqamini** (`+998901234567`) yoki **@username** ini yuboring:",
                buttons=[[Button.inline("❌ Bekor qilish", b"m:home")]]
            )
            await event.answer()
            return

        if data == "m:crm":
            user_state["mode"] = None
            await _show_crm_list(event, filter_type="all", page=0, is_edit=True)
            await event.answer()
            return

        if data == "m:stats":
            await _show_stats_screen(event, is_edit=True)
            await event.answer()
            return

        if data == "m:settings":
            await _show_settings_screen(event, is_edit=True)
            await event.answer()
            return

        if data == "m:ai":
            user_state["mode"] = "ai"
            await safe_edit(
                event,
                f"🧠 **Gemini AI Rejimi Faol** (`{config_state.get('model')}`)\n\n"
                "Istalgan savolingizni yozing yoki rasm/hujjat tashlang!",
                buttons=[
                    [Button.inline("🧹 Suhbatni tozalash", b"ai:clear")],
                    [Button.inline("🏠 Bosh menyu", b"m:home")],
                ]
            )
            await event.answer()
            return

        if data == "m:stop":
            if config_state.get("campaign_running"):
                config_state["campaign_running"] = False
                await event.answer("🛑 To'xtatish buyrug'i berildi!", alert=True)
            else:
                await event.answer("ℹ️ Faol reklama jarayoni yo'q.")
            text, buttons = _build_dashboard(ctx)
            await safe_edit(event, text, buttons=buttons)
            return

        if data == "m:sync":
            await event.answer("⏳ Mijozlar papkasi yangilanmoqda...")
            added, skipped = await ctx["sync_all_leads_to_mijozlar"]()
            await safe_edit(
                event,
                f"✅ **'Mijozlar' papkasi yangilandi!**\n"
                f"💼 **Jamlangan chatlar:** `{added}` ta\n"
                f"ℹ️ **O'tkazilgan (topilmagan):** `{skipped}` ta",
                buttons=[
                    [Button.inline("👥 CRM ga qaytish", b"m:crm"), Button.inline("🏠 Menyu", b"m:home")]
                ]
            )
            return

        # Soha tanlash
        if data.startswith("c:"):
            val = data[2:]
            if val == "custom":
                user_state["mode"] = "custom_cat"
                await safe_edit(
                    event,
                    "✏️ **O'zingiz istagan sohani yozing:**\nMasalan: `mebel`, `qurilish`, `dorixona`, `fast food, kafe`",
                    buttons=[[Button.inline("❌ Bekor qilish", b"m:maps")]]
                )
            elif val in ("back_city", "pick_city"):
                await _show_city_picker(event, is_edit=True)
            else:
                idx = int(val)
                cat_val = CATEGORY_PRESETS[idx][1]
                user_state["maps_cat"] = cat_val
                user_state["maps_count"] = 8 if cat_val == "turli xil" else 5
                await _show_maps_confirm(event, is_edit=True)
            await event.answer()
            return

        # Shahar tanlash
        if data.startswith("l:"):
            val = data[2:]
            if val == "custom":
                user_state["mode"] = "custom_city"
                await safe_edit(
                    event,
                    "✏️ **Shahar nomini yozing:**\nMasalan: `Buxoro`, `Qo'qon`, `Xorazm`",
                    buttons=[[Button.inline("❌ Orqaga", b"c:pick_city")]]
                )
            elif val == "back_count":
                await _show_count_picker(event, is_edit=True)
            elif val == "back_confirm":
                await _show_maps_confirm(event, is_edit=True)
            else:
                idx = int(val)
                user_state["maps_city"] = CITY_PRESETS[idx][1]
                await _show_maps_confirm(event, is_edit=True)
            await event.answer()
            return

        # Miqdor tanlash
        if data.startswith("n:"):
            user_state["maps_count"] = int(data[2:])
            await _show_maps_confirm(event, is_edit=True)
            await event.answer()
            return

        # Google Maps kampaniyani ishga tushirish
        if data == "go:maps":
            if config_state.get("campaign_running"):
                await event.answer("⚠️ Boshqa kampaniya allaqachon ishlamoqda!", alert=True)
                return

            full_q = f"{user_state['maps_city']} {user_state['maps_cat']}".strip() if user_state["maps_city"] else user_state["maps_cat"]
            limit = user_state["maps_count"]
            await event.answer("🚀 Jarayon boshlanmoqda...")

            status_msg = await safe_edit(
                event,
                f"🔍 **Google Maps tahlil qilinmoqda...**\n"
                f"📌 **So'rov:** `{full_q}` | 🎯 **Maqsad:** `{limit}` ta\n"
                f"⏳ Veb-sayti yo'q joylar izlanmoqda (15–40 soniya olishi mumkin)...",
                buttons=[[Button.inline("🛑 To'xtatish", b"m:stop")]]
            )

            async def _progress_cb(msg_text: str):
                if status_msg:
                    try:
                        await status_msg.edit(
                            msg_text,
                            buttons=[[Button.inline("🛑 To'xtatish", b"m:stop")]],
                            parse_mode="md"
                        )
                    except Exception:
                        pass

            async def _run_bg():
                res = await ctx["run_outreach_campaign"](
                    query=full_q,
                    max_targets=limit,
                    progress_cb=_progress_cb,
                )
                summary_text = res["summary_text"]
                end_buttons = [
                    [Button.inline("👥 Mijozlar CRM", b"m:crm"), Button.inline("💼 Papkani yangilash", b"m:sync")],
                    [Button.inline("🗺️ Yana qidirish", b"m:maps"), Button.inline("🏠 Bosh menyu", b"m:home")],
                ]
                if status_msg:
                    try:
                        await status_msg.edit(summary_text, buttons=end_buttons, parse_mode="md")
                        return
                    except Exception:
                        pass
                await bot_client.send_message(owner_id, summary_text, buttons=end_buttons, parse_mode="md")

            asyncio.create_task(_run_bg())
            return

        # Manual wizard callbacks
        if data == "man:skip_title":
            user_state["man_title"] = ""
            user_state["mode"] = None
            await _show_manual_preview(event, is_edit=True)
            await event.answer()
            return

        if data == "man:send":
            target = user_state["man_target"]
            title = user_state["man_title"]
            await event.answer("📤 Yuborilmoqda...")
            await safe_edit(event, f"⏳ `{target}` ga insoniy xabar yuborilmoqda...")
            try:
                me = await user_client.get_me()
                owner_name = me.first_name if (me and me.first_name) else "Muhammadrizo"
                ad_text = ctx["generate_web_ad"](
                    owner_name=owner_name,
                    recipient_title=title or None,
                    username=me.username if me else None,
                    phone=me.phone if me else None,
                )
                sent_msg = await ctx["send_to_recipient"](target, ad_text)
                if sent_msg and hasattr(sent_msg, "chat_id"):
                    rid = str(sent_msg.chat_id)
                    ad_leads[rid] = {
                        "target": target,
                        "title": title,
                        "sent_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "followup_sent": False,
                        "agreed": False,
                        "details_explained": False,
                    }
                    if target.startswith("+") and target not in ad_leads["contacted_phones"]:
                        ad_leads["contacted_phones"].append(target)
                    ctx["save_ad_leads"](ad_leads)
                    if config_state.get("auto_folder", True):
                        await ctx["move_chat_to_mijozlar"](sent_msg.input_chat or sent_msg.chat_id, archive=True)

                ctx["log_event"]("🤖 BOT->REKLAMA", target, "[bold bright_green]YUBORILDI ✅[/bold bright_green]", f"Kimga: {title or 'Mijoz'}")
                await safe_edit(
                    event,
                    f"✅ **Xabar muvaffaqiyatli yuborildi!**\n🎯 **Qabul qiluvchi:** `{target}`\n💼 Chat `'Mijozlar'` papkasiga joylandi.",
                    buttons=[[Button.inline("🎯 Yana yuborish", b"m:manual"), Button.inline("🏠 Menyu", b"m:home")]]
                )
            except Exception as err:
                await safe_edit(
                    event,
                    f"❌ **Yuborishda xatolik:**\n`{err}`",
                    buttons=[[Button.inline("🔄 Qayta urinish", b"m:manual"), Button.inline("🏠 Menyu", b"m:home")]]
                )
            return

        # CRM list pagination & filtering
        if data.startswith("crm:"):
            _, flt, pg = data.split(":")
            await _show_crm_list(event, filter_type=flt, page=int(pg), is_edit=True)
            await event.answer()
            return

        if data.startswith("ld:"):
            cid = data[3:]
            await _show_lead_detail(event, cid)
            await event.answer()
            return

        if data.startswith("la:"):
            parts = data.split(":", 2)
            action, cid = parts[1], parts[2]
            lead = ad_leads.get(cid)
            if not isinstance(lead, dict):
                await event.answer("Mijoz topilmadi", alert=True)
                return

            if action == "ok":
                lead["agreed"] = True
                lead["followup_sent"] = True
                ctx["save_ad_leads"](ad_leads)
                try:
                    await ctx["move_chat_to_mijozlar"](int(cid), archive=False)
                except Exception:
                    pass
                await event.answer("🔥 Faol mijoz sifatida belgilandi!", alert=True)
                await _show_lead_detail(event, cid)
                return

            if action == "fld":
                target_cand = int(cid) if cid.lstrip("-").isdigit() else lead.get("target")
                ok = await ctx["move_chat_to_mijozlar"](target_cand, archive=not lead.get("agreed"))
                await event.answer("💼 Mijozlar papkasiga qo'shildi!" if ok else "⚠️ Chat topilmadi", alert=True)
                return

            if action == "files":
                client_dir = os.path.join(ctx["CLIENT_FILES_DIR"], f"mijoz_{cid}")
                if not os.path.isdir(client_dir) or not os.listdir(client_dir):
                    await event.answer("ℹ️ Bu mijozdan hali fayl yoki matn kelmagan.", alert=True)
                    return
                await event.answer("📁 Fayllar yuborilmoqda...")
                talablar_path = os.path.join(client_dir, "talablar.txt")
                if os.path.isfile(talablar_path):
                    with open(talablar_path, "r", encoding="utf-8") as f:
                        notes = f.read().strip()
                    if notes:
                        await bot_client.send_message(
                            owner_id,
                            f"📝 **{lead.get('title', cid)} — Mijoz talablari:**\n\n{notes[:3800]}"
                        )
                sent_files = 0
                for fn in os.listdir(client_dir):
                    if fn == "talablar.txt":
                        continue
                    fp = os.path.join(client_dir, fn)
                    if os.path.isfile(fp):
                        try:
                            await bot_client.send_file(owner_id, fp, caption=f"📁 {lead.get('title', cid)}: `{fn}`")
                            sent_files += 1
                        except Exception:
                            pass
                if not os.path.isfile(talablar_path) and sent_files == 0:
                    await bot_client.send_message(owner_id, "ℹ️ Papkada ochiladigan fayllar topilmadi.")
                return

            if action == "del":
                ad_leads.pop(cid, None)
                ctx["save_ad_leads"](ad_leads)
                await event.answer("🗑️ Mijoz bazadan o'chirildi!", alert=True)
                await _show_crm_list(event, filter_type="all", page=0, is_edit=True)
                return

        # Sozlamalar
        if data == "s:autoreply":
            config_state["auto_reply"] = not config_state.get("auto_reply", True)
            ctx["save_settings"]()
            await _show_settings_screen(event, is_edit=True)
            await event.answer("✅ Saqlandi")
            return

        if data == "s:autofolder":
            config_state["auto_folder"] = not config_state.get("auto_folder", True)
            ctx["save_settings"]()
            await _show_settings_screen(event, is_edit=True)
            await event.answer("✅ Saqlandi")
            return

        if data == "s:delay":
            cur = (float(config_state.get("delay_min", 14.0)), float(config_state.get("delay_max", 24.0)))
            next_idx = 0
            for idx, (_, dmin, dmax) in enumerate(DELAY_PROFILES):
                if abs(cur[0] - dmin) < 1.0:
                    next_idx = (idx + 1) % len(DELAY_PROFILES)
                    break
            lbl, dmin, dmax = DELAY_PROFILES[next_idx]
            config_state["delay_min"] = dmin
            config_state["delay_max"] = dmax
            ctx["save_settings"]()
            await _show_settings_screen(event, is_edit=True)
            await event.answer(f"⏱️ {lbl}")
            return

        if data == "s:model":
            cur_m = config_state.get("model", MODEL_CHOICES[0])
            idx = (MODEL_CHOICES.index(cur_m) + 1) % len(MODEL_CHOICES) if cur_m in MODEL_CHOICES else 0
            config_state["model"] = MODEL_CHOICES[idx]
            ctx["save_settings"]()
            await _show_settings_screen(event, is_edit=True)
            await event.answer(f"🧠 {config_state['model']}")
            return

        if data == "s:loc":
            user_state["mode"] = "set_loc"
            await safe_edit(
                event,
                "📍 **Default hudud koordinatasini o'zgartirish**\n\n"
                "Google Maps havolasini (`https://www.google.com/maps/@40.76,72.36...`) "
                "yoki oddiy `40.7639, 72.3623` ko'rinishida koordinata yuboring:",
                buttons=[[Button.inline("❌ Bekor qilish", b"m:settings")]]
            )
            await event.answer()
            return

        if data == "s:kanal":
            user_state["mode"] = "set_kanal"
            current_k = config_state.get("alert_channel") or "Hozircha ulanmagan"
            await safe_edit(
                event,
                "📢 **Xabarnoma Kanalini / Guruhini Ulash**\n\n"
                f"Hozirgi kanal: `{current_k}`\n\n"
                "Mijoz `HA` deganda xabar boradigan kanal `@username` sini (yoki `-100...` ID sini) yuboring.\n"
                "⚠️ *Eslatma:* Botni o'sha kanal/guruhga Admin qilib qo'shib qo'ying.\n"
                "O'chirish uchun `off` deb yozing.",
                buttons=[[Button.inline("❌ Bekor qilish", b"m:settings")]]
            )
            await event.answer()
            return

        if data == "ai:clear":
            ctx["chat_sessions"].pop(bot_chat_id_key, None)
            await event.answer("🧹 Suhbat xotirasi tozalandi!", alert=True)
            return

        await event.answer()
