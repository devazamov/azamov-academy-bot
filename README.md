"""
BAXMAL O'QUV MARKAZI IT YO'NALISHI TO'GARAGI — Ro'yxatdan o'tish Telegram boti
=================================================

Oqim:
1. /start -> chiroyli salomlashish
2. Ism familiya so'raladi
3. Qiziqish (kurs) tanlanadi -> tugmalar orqali
4. Telefon raqam so'raladi -> tugma orqali yuboriladi
5. Majburiy kanallarga obuna tekshiriladi (Firebase'dan dinamik olinadi)
6. Obuna tasdiqlansa -> maxfiy kanal linki yuboriladi
7. Barcha ma'lumot Firebase'ga yoziladi

Admin panel (faqat ADMIN_IDS ro'yxatidagilar uchun):
/admin       -> admin menyu (animatsiyali tugmalar)
/stats       -> statistika
/users       -> oxirgi foydalanuvchilar ro'yxati
Kanal qo'shish/o'chirish va maxfiy kanal linkini sozlash ham shu menyudan.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

import firebase_config as fb

load_dotenv()

# ============================ SOZLAMALAR ============================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation bosqichlari
FULL_NAME, INTEREST, PHONE, CHECK_SUB = range(4)
# Admin conversation bosqichlari
ADD_CHANNEL_ID, ADD_CHANNEL_TITLE, ADD_CHANNEL_URL, SET_PRIVATE_LINK = range(10, 14)

INTERESTS = [
    "💻 Kompyuter savodxonligi",
    "🎨 Grafik dizayn",
    "🤖 Sun'iy intellekt",
    "👨‍💻 Dasturlash (Frontend)",
    "✈️ Telegram bot yaratish",
]


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ============================ FOYDALANUVCHI OQIMI ============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if fb.is_registered(user.id):
        link = fb.get_private_channel_link()
        link_display = link if link else "Tez orada admin tomonidan qo'shiladi."
        await update.message.reply_text(
            "✅ Siz allaqachon ro'yxatdan o'tgansiz!\n\n"
            f"🔐 Maxfiy kanal: {link_display}"
        )
        return ConversationHandler.END

    await context.bot.send_chat_action(chat_id=user.id, action=ChatAction.TYPING)
    await asyncio.sleep(0.5)

    await update.message.reply_text(
        "🎓✨ <b>BAXMAL O'QUV MARKAZI — IT yo'nalishi to'garagi</b>ga xush kelibsiz!\n\n"
        "Kelajagingizni IT bilan quring! 🚀\n\n"
        "Ro'yxatdan o'tish uchun bir nechta savolga javob bering.\n\n"
        "👇 Avval <b>ism va familiyangizni</b> yozing:",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove(),
    )
    return FULL_NAME


async def get_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    full_name = update.message.text.strip()
    if len(full_name) < 3:
        await update.message.reply_text("⚠️ Iltimos, to'liq ism familyangizni kiriting.")
        return FULL_NAME

    context.user_data["full_name"] = full_name
    fb.save_user_step(
        update.effective_user.id,
        {
            "user_id": update.effective_user.id,
            "username": update.effective_user.username,
            "full_name": full_name,
        },
    )

    keyboard = [[InlineKeyboardButton(i, callback_data=f"interest::{i}")] for i in INTERESTS]
    await update.message.reply_text(
        f"Rahmat, <b>{full_name}</b>! 👋\n\n"
        "🎯 Endi qaysi yo'nalish sizni qiziqtiradi?",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return INTEREST


async def get_interest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ Tanlandi!")
    interest = query.data.split("::", 1)[1]

    context.user_data["interest"] = interest
    fb.save_user_step(update.effective_user.id, {"interest": interest})

    contact_button = KeyboardButton("📱 Raqamni yuborish", request_contact=True)
    await query.edit_message_text(
        f"Tanlandi: <b>{interest}</b> ✅", parse_mode=ParseMode.HTML
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="📞 Endi telefon raqamingizni yuboring (tugma orqali):",
        reply_markup=ReplyKeyboardMarkup(
            [[contact_button]], resize_keyboard=True, one_time_keyboard=True
        ),
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()
        if not phone.replace("+", "").isdigit() or len(phone) < 9:
            await update.message.reply_text(
                "⚠️ Iltimos, to'g'ri telefon raqam kiriting yoki tugmadan foydalaning."
            )
            return PHONE

    context.user_data["phone"] = phone
    fb.save_user_step(update.effective_user.id, {"phone": phone})

    await update.message.reply_text(
        "✅ Raqam qabul qilindi!", reply_markup=ReplyKeyboardRemove()
    )

    return await check_subscription(update, context)


async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channels = fb.get_required_channels()
    user_id = update.effective_user.id

    if not channels:
        # Majburiy kanal yo'q bo'lsa, to'g'ridan to'g'ri yakunlash
        return await finish_registration(update, context)

    not_subscribed = []
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(chat_id=ch["chat_id"], user_id=user_id)
            if member.status in ("left", "kicked"):
                not_subscribed.append(ch)
        except Exception as e:
            logger.warning(f"Kanal tekshirishda xato {ch['chat_id']}: {e}")
            not_subscribed.append(ch)

    if not_subscribed:
        keyboard = [
            [InlineKeyboardButton(f"📢 {ch['title']}", url=ch["url"])] for ch in not_subscribed
        ]
        keyboard.append(
            [InlineKeyboardButton("✅ Tekshirish / A'zo bo'ldim", callback_data="check_sub_again")]
        )
        text = (
            "🔒 <b>Davom etish uchun quyidagi kanallarga obuna bo'ling:</b>\n\n"
            "Har birini bosib o'ting, so'ng pastdagi tugma orqali tekshiring 👇"
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return CHECK_SUB

    return await finish_registration(update, context)


async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔍 Tekshirilmoqda...")
    return await check_subscription(update, context)


async def finish_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    fb.complete_registration(user_id)

    link = fb.get_private_channel_link()
    link_text = link if link else "Tez orada admin tomonidan yuboriladi."

    text = (
        "🎉✨ <b>Tabriklaymiz!</b> ✨🎉\n\n"
        "Siz muvaffaqiyatli ro'yxatdan o'tdingiz!\n\n"
        f"🔐 <b>Yopiq kanal:</b> {link_text}\n\n"
        "📚 Darslar haqida ma'lumot shu yopiq kanalda e'lon qilinadi.\n\n"
        "Kelajagingizni IT bilan quring! 🚀"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Ro'yxatdan o'tish bekor qilindi. Qaytadan boshlash uchun /start bosing.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# ============================ ADMIN PANEL ============================

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    keyboard = [
        [InlineKeyboardButton("📊 Statistika", callback_data="admin::stats")],
        [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin::users")],
        [InlineKeyboardButton("📢 Majburiy kanallar", callback_data="admin::channels")],
        [InlineKeyboardButton("🔐 Maxfiy kanal linkini sozlash", callback_data="admin::set_private")],
    ]
    text = "⚙️ <b>Admin panel</b>\n\nKerakli bo'limni tanlang 👇"

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    total = fb.count_users()
    registered = fb.count_registered_users()
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchi: <b>{total}</b>\n"
        f"✅ To'liq ro'yxatdan o'tgan: <b>{registered}</b>\n"
        f"⏳ Jarayonda: <b>{total - registered}</b>"
    )
    keyboard = [[InlineKeyboardButton("⬅️ Orqaga", callback_data="admin::back")]]
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    users = fb.get_all_users()
    users = [u for u in users if u.get("registered")][-15:]  # oxirgi 15 ta

    if not users:
        text = "👥 Hozircha ro'yxatdan o'tgan foydalanuvchi yo'q."
    else:
        lines = ["👥 <b>Oxirgi ro'yxatdan o'tganlar:</b>\n"]
        for u in users:
            uname = f"@{u['username']}" if u.get("username") else "—"
            lines.append(
                f"• <b>{u.get('full_name', '—')}</b> | {uname}\n"
                f"  📱 {u.get('phone', '—')} | 🎯 {u.get('interest', '—')}"
            )
        text = "\n".join(lines)

    keyboard = [[InlineKeyboardButton("⬅️ Orqaga", callback_data="admin::back")]]
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channels = fb.get_required_channels()

    lines = ["📢 <b>Majburiy kanallar</b>\n"]
    keyboard = []
    if not channels:
        lines.append("Hozircha kanal qo'shilmagan.")
    else:
        for ch in channels:
            lines.append(f"• {ch['title']} ({ch['chat_id']})")
            keyboard.append(
                [InlineKeyboardButton(f"🗑 O'chirish: {ch['title']}", callback_data=f"admin::del_ch::{ch['doc_id']}")]
            )

    keyboard.append([InlineKeyboardButton("➕ Yangi kanal qo'shish", callback_data="admin::add_channel")])
    keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="admin::back")])

    await query.edit_message_text(
        "\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_delete_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    doc_id = query.data.split("::", 2)[2]
    fb.remove_required_channel(doc_id)
    await query.answer("🗑 Kanal o'chirildi!")
    await admin_channels(update, context)


async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_menu(update, context)


# --- Yangi kanal qo'shish (mini conversation, animatsiyali) ---

async def admin_add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "➕ <b>Yangi majburiy kanal qo'shish</b>\n\n"
        "1️⃣ Kanal <b>chat_id</b> yoki <b>username</b>ini yuboring.\n"
        "Masalan: <code>@azamov_academy</code> yoki <code>-1001234567890</code>\n\n"
        "Bekor qilish uchun /cancel",
        parse_mode=ParseMode.HTML,
    )
    return ADD_CHANNEL_ID


async def admin_add_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_ch_id"] = update.message.text.strip()
    await update.message.reply_text("2️⃣ Endi kanal <b>nomini</b> yuboring (foydalanuvchi ko'radigan nom):", parse_mode=ParseMode.HTML)
    return ADD_CHANNEL_TITLE


async def admin_add_channel_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_ch_title"] = update.message.text.strip()
    await update.message.reply_text(
        "3️⃣ Endi kanal <b>havolasini</b> yuboring.\nMasalan: <code>https://t.me/azamov_academy</code>",
        parse_mode=ParseMode.HTML,
    )
    return ADD_CHANNEL_URL


async def admin_add_channel_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    chat_id = context.user_data["new_ch_id"]
    title = context.user_data["new_ch_title"]

    await update.message.chat.send_action(ChatAction.TYPING)
    fb.add_required_channel(chat_id, title, url)

    await update.message.reply_text(
        f"✅✨ <b>Kanal qo'shildi!</b>\n\n📢 {title}\n🔗 {url}",
        parse_mode=ParseMode.HTML,
    )
    await admin_menu(update, context)
    return ConversationHandler.END


# --- Maxfiy kanal linkini sozlash ---

async def admin_set_private_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    current = fb.get_private_channel_link() or "Hozircha o'rnatilmagan"
    await query.edit_message_text(
        f"🔐 <b>Maxfiy kanal linki</b>\n\nJoriy: {current}\n\n"
        "Yangi havolani yuboring (masalan: <code>https://t.me/+abcdEFGh</code>):\n\n"
        "Bekor qilish uchun /cancel",
        parse_mode=ParseMode.HTML,
    )
    return SET_PRIVATE_LINK


async def admin_set_private_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    fb.set_private_channel_link(link)
    await update.message.reply_text(f"✅ Maxfiy kanal linki saqlandi:\n{link}")
    await admin_menu(update, context)
    return ConversationHandler.END


async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Bekor qilindi.")
    await admin_menu(update, context)
    return ConversationHandler.END


# ============================ MAIN ============================

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN .env faylida topilmadi!")

    app = Application.builder().token(BOT_TOKEN).build()

    # --- Foydalanuvchi ro'yxatdan o'tish conversation ---
    reg_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
            INTEREST: [CallbackQueryHandler(get_interest, pattern=r"^interest::")],
            PHONE: [MessageHandler((filters.CONTACT | filters.TEXT) & ~filters.COMMAND, get_phone)],
            CHECK_SUB: [CallbackQueryHandler(check_sub_callback, pattern=r"^check_sub_again$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # --- Admin: kanal qo'shish conversation ---
    add_channel_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_channel_start, pattern=r"^admin::add_channel$")],
        states={
            ADD_CHANNEL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_channel_id)],
            ADD_CHANNEL_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_channel_title)],
            ADD_CHANNEL_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_channel_url)],
        },
        fallbacks=[CommandHandler("cancel", admin_cancel)],
    )

    # --- Admin: maxfiy link sozlash conversation ---
    set_private_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_set_private_start, pattern=r"^admin::set_private$")],
        states={
            SET_PRIVATE_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_set_private_save)],
        },
        fallbacks=[CommandHandler("cancel", admin_cancel)],
    )

    app.add_handler(reg_conv)
    app.add_handler(add_channel_conv)
    app.add_handler(set_private_conv)

    app.add_handler(CommandHandler("admin", admin_menu))
    app.add_handler(CallbackQueryHandler(admin_stats, pattern=r"^admin::stats$"))
    app.add_handler(CallbackQueryHandler(admin_users, pattern=r"^admin::users$"))
    app.add_handler(CallbackQueryHandler(admin_channels, pattern=r"^admin::channels$"))
    app.add_handler(CallbackQueryHandler(admin_delete_channel, pattern=r"^admin::del_ch::"))
    app.add_handler(CallbackQueryHandler(admin_back, pattern=r"^admin::back$"))

    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
