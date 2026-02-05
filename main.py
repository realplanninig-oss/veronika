# File: main.py — прогрев-бот: компактное меню, FAQ с URL-кнопками, видео/статьи, диагностика, кейсы, оплата с URL-кнопкой, "я оплатила" с кнопкой в чат.
# Python 3.8+ | python-telegram-bot v20+

import os
import sys
import re
from typing import Tuple, Dict, List, Optional

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# -------------------------
# .env loader
# -------------------------

def load_env_file(env_path: str) -> None:
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if len(value) >= 2 and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
                    value = value[1:-1]
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception as e:
        print(f"Ошибка чтения .env: {e}")
        sys.exit(1)


def require_env_vars() -> Tuple[str, int]:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_env_file(env_path)

    token = (os.getenv("TELEGRAM_TOKEN") or "").strip()
    admin_chat_id_raw = (os.getenv("ADMIN_CHAT_ID") or "").strip()

    if not token or not admin_chat_id_raw:
        print(
            "Не найдены TELEGRAM_TOKEN и/или ADMIN_CHAT_ID в .env рядом с main.py.\n"
            "Пример:\nTELEGRAM_TOKEN=...\nADMIN_CHAT_ID=123456789\n"
        )
        sys.exit(1)

    try:
        admin_chat_id = int(admin_chat_id_raw)
    except ValueError:
        print("ADMIN_CHAT_ID должен быть числом.")
        sys.exit(1)

    return token, admin_chat_id


# -------------------------
# Кнопки/меню
# -------------------------

MENU_BACK = "⬅️ В меню"

MENU_START = "🚀 Начать (видео)"
MENU_FAQ = "🎥 Вопросы (FAQ)"
MENU_DIAG = "🔎 Подойдёт ли мне?"
MENU_CASES = "📌 Кейсы"
MENU_PAY = "💳 Оплатить"
MENU_HUMAN = "🤝 Поддержка"

MENU_PAID = "✅ Я оплатила"

PAY_URL = "https://expertsblog.tb.ru/zapusk/plan"
MINI_COURSE_CHAT_URL = "https://t.me/+7cKQ7WhXxU9kMWNi"

MAIN_MENU_KB = ReplyKeyboardMarkup(
    [
        [MENU_START, MENU_FAQ],
        [MENU_DIAG, MENU_CASES],
        [MENU_PAY, MENU_HUMAN],
    ],
    resize_keyboard=True,
)

BACK_ONLY_KB = ReplyKeyboardMarkup([[MENU_BACK]], resize_keyboard=True)


# -------------------------
# Видео (внутри "Начать")
# -------------------------

VID_1 = "1️⃣ Выгода"
VID_2 = "2️⃣ 3 ошибки запуска"
VID_3 = "3️⃣ 100 тр без блога за неделю"

VIDEOS_MENU_KB = ReplyKeyboardMarkup(
    [
        [VID_1],
        [VID_2],
        [VID_3],
        [MENU_BACK],
    ],
    resize_keyboard=True,
)

VIDEOS_INTRO = (
    "Ок, без долгих вступлений.\n"
    "Хочешь продажи — смотри видео. Потом думаешь.\n\n"
    "Выбирай 👇"
)

VIDEO_URLS = {
    VID_1: "https://t.me/YourProducerOnline/405",
    VID_2: "https://t.me/YourProducerOnline/415",
    VID_3: "https://t.me/YourProducerOnline/424",
}

VIDEOS_TEXTS = {
    VID_1: (
        "🔥 *Выгода*\n"
        "С этого начинаем.\n\n"
        "🎥 https://t.me/YourProducerOnline/405"
    ),
    VID_2: (
        "🚫 *3 ошибки запуска продаж*\n"
        "Чтобы не слить запуск.\n\n"
        "🎥 https://t.me/YourProducerOnline/415"
    ),
    VID_3: (
        "💰 *100 тр без блога за неделю*\n"
        "Смотри разбор.\n\n"
        "🎥 https://t.me/YourProducerOnline/424"
    ),
}

def video_inline_button_for(video_key: str) -> Optional[InlineKeyboardMarkup]:
    url = VIDEO_URLS.get(video_key)
    if not url:
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Смотреть", url=url)]])


# -------------------------
# FAQ — ссылки в тексте + inline-кнопки
# -------------------------

FAQ_Q1 = "1️⃣ Бюджет"
FAQ_Q2 = "2️⃣ Доверие"
FAQ_Q3 = "3️⃣ Гарантии"
FAQ_Q4 = "4️⃣ Подойдёт ли"
FAQ_Q5 = "5️⃣ Заработок"

FAQ_MENU_KB = ReplyKeyboardMarkup(
    [
        [FAQ_Q1, FAQ_Q2],
        [FAQ_Q3, FAQ_Q4],
        [FAQ_Q5],
        [MENU_BACK],
    ],
    resize_keyboard=True,
)

FAQ_INTRO = (
    "Скорее всего, ты не тупишь. Ты просто не хочешь купить ерунду.\n"
    "И правильно делаешь.\n\n"
    "Выбирай вопрос — отвечаю (и даю ссылки) 👇"
)

FAQ_LINKS = {
    FAQ_Q1: ["https://t.me/YourProducerOnline/429"],
    FAQ_Q2: ["https://t.me/YourProducerOnline/432", "https://t.me/YourProducerOnline/433"],
    FAQ_Q3: ["https://t.me/YourProducerOnline/430"],
    FAQ_Q4: ["https://t.me/YourProducerOnline/428"],
    FAQ_Q5: ["https://t.me/YourProducerOnline/417", "https://t.me/YourProducerOnline/420"],
}

def faq_inline_buttons_for(question: str) -> Optional[InlineKeyboardMarkup]:
    links = FAQ_LINKS.get(question, [])
    if not links:
        return None

    if len(links) == 1:
        return InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Смотреть", url=links[0])]])

    rows = []
    for i, url in enumerate(links, start=1):
        rows.append([InlineKeyboardButton(f"▶️ Видео {i}", url=url)])
    return InlineKeyboardMarkup(rows)

def faq_links_as_text(question: str) -> str:
    links = FAQ_LINKS.get(question, [])
    if not links:
        return ""
    if len(links) == 1:
        return f"\n\nСсылка: {links[0]}"
    return "\n\n" + "\n".join([f"Ссылка {i}: {u}" for i, u in enumerate(links, start=1)])

FAQ_TEXTS = {
    FAQ_Q1: "💸 *Какой бюджет нужен для запуска продаж?*\n\nБюджет = 0 рублей.",
    FAQ_Q2: "📌 *Какие у меня реализованные проекты и почему мне можно доверять?*\n\n50+ проектов в разных нишах.",
    FAQ_Q3: "🛡 *Какие гарантии ты получаешь?*\n\nВозврат денег, если не запустим тебя.",
    FAQ_Q4: "⚙️ *Подойдёт ли тебе эта технология?*\n\nЛучшую технологию подберем на разборе твоей ситуации.",
    FAQ_Q5: "📈 *Сколько ты реально сможешь заработать?*\n\nСмотри кейсы и механику — там реальность.",
}


# -------------------------
# Диагностика + 3 статьи
# -------------------------

DIAG_Q1 = 20
DIAG_Q2 = 21

DIAG_Q1_TEXT = "У тебя уже есть блог?"
DIAG_Q1_A = "Да"
DIAG_Q1_B = "Нет / начинаю"

DIAG_Q2_TEXT = "Твоя цель на ближайшие 7–14 дней?"
DIAG_Q2_A = "Первые продажи"
DIAG_Q2_B = "Стабильность"
DIAG_Q2_C = "Автоматизация"

DIAG_Q1_KB = ReplyKeyboardMarkup([[DIAG_Q1_A, DIAG_Q1_B], [MENU_BACK]], resize_keyboard=True)
DIAG_Q2_KB = ReplyKeyboardMarkup([[DIAG_Q2_A], [DIAG_Q2_B], [DIAG_Q2_C], [MENU_BACK]], resize_keyboard=True)

DIAG_ARTICLES_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("📄 Как устроена воронка?", url="https://salebot.site/md/voronka_Reels")],
    [InlineKeyboardButton("📄 Как запустить быстро продажи?", url="https://salebot.site/md/zapuskblog")],
    [InlineKeyboardButton("📄 Волшебная таблетка", url="https://salebot.site/md/tabletkinet")],
])


# -------------------------
# Кейсы + кнопка “100 тр без блога за неделю”
# -------------------------

CASE_STATE = 30
CASE_NEXT = "➡️ Дальше"

CASE_100_WEEK = "💰 100 тр без блога за неделю"

CASE_JULIA = "Юлия — 2 млн"
CASE_ELENA = "Елена — 1 млн"
CASE_DARYA = "Дарья — 700k"

CASES_MENU_KB = ReplyKeyboardMarkup(
    [
        [CASE_100_WEEK],
        [CASE_JULIA],
        [CASE_ELENA],
        [CASE_DARYA],
        [MENU_BACK],
    ],
    resize_keyboard=True,
)

CASE_KB = ReplyKeyboardMarkup([[CASE_NEXT], [MENU_BACK]], resize_keyboard=True)

CASES_STEPS: Dict[str, List[str]] = {
    CASE_JULIA: [
        "📌 *Кейс Юлии (коучинг)*\n\n10 лет блог работал сам. Потом рынок сказал: «а теперь плати или страдай».",
        "Мы сделали не «больше контента», а *умнее контент*:\n• смысл\n• боль\n• воронка\n• система\n\nБез цирка и выгорания.",
        "Результат: *2 000 000 ₽ за 14 дней*.",
        "Хочешь так же — жми *«Оплатить»*.",
    ],
    CASE_ELENA: [
        "📌 *Кейс Елены*\n\nПродажи были как погода — то солнце, то дождь.",
        "Собрали: упаковка + прогрев + воронка.",
        "Результат: *1 000 000 ₽*.",
        "Хочешь повторяемость — жми *«Оплатить»*.",
    ],
    CASE_DARYA: [
        "📌 *Кейс Дарьи (маникюр)*\n\nБлог был, роста не было.",
        "Сделали: упаковка + контент + автоворонка.",
        "Результат: *700 000 ₽*.",
        "Хочешь так же — жми *«Оплатить»*.",
    ],
}

CASE_100_WEEK_INLINE = InlineKeyboardMarkup([
    [InlineKeyboardButton("▶️ Смотреть кейс", url="https://t.me/YourProducerOnline/424")]
])


# -------------------------
# Хелперы
# -------------------------

def user_identity(update: Update) -> Tuple[int, str]:
    u = update.effective_user
    return (u.id if u else 0), ((u.username or "").strip() if u else "")


async def show_menu(update: Update, text: str = "Выбирай 👇") -> None:
    await update.message.reply_text(text, reply_markup=MAIN_MENU_KB)


# -------------------------
# Команды
# -------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет.\n"
        "Я — короткий путь к продажам без выгорания.\n\n"
        "С чего начнём?",
        reply_markup=MAIN_MENU_KB,
    )


async def menu_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await show_menu(update)
    return ConversationHandler.END


# -------------------------
# Видео flow
# -------------------------

VIDEOS_STATE = 11

async def videos_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(VIDEOS_INTRO, reply_markup=VIDEOS_MENU_KB)
    return VIDEOS_STATE


async def videos_handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text == MENU_BACK:
        await show_menu(update)
        return ConversationHandler.END

    ans = VIDEOS_TEXTS.get(text)
    if ans:
        inline_kb = video_inline_button_for(text)
        await update.message.reply_text(ans, reply_markup=inline_kb, parse_mode="Markdown")
        await update.message.reply_text("Выбирай следующее 👇", reply_markup=VIDEOS_MENU_KB)
        return VIDEOS_STATE

    await update.message.reply_text("Выбери пункт кнопкой 👇", reply_markup=VIDEOS_MENU_KB)
    return VIDEOS_STATE


# -------------------------
# FAQ flow
# -------------------------

FAQ_STATE = 10

async def faq_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(FAQ_INTRO, reply_markup=FAQ_MENU_KB)
    return FAQ_STATE


async def faq_handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text == MENU_BACK:
        await show_menu(update)
        return ConversationHandler.END

    answer = FAQ_TEXTS.get(text)
    if not answer:
        await update.message.reply_text("Выбери вопрос кнопкой 👇", reply_markup=FAQ_MENU_KB)
        return FAQ_STATE

    answer_with_links = answer + faq_links_as_text(text)
    inline_kb = faq_inline_buttons_for(text)

    await update.message.reply_text(answer_with_links, reply_markup=inline_kb, parse_mode="Markdown")
    await update.message.reply_text("Хочешь — выбери следующий вопрос 👇", reply_markup=FAQ_MENU_KB)
    return FAQ_STATE


# -------------------------
# Диагностика flow
# -------------------------

async def diag_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("diag_blog", None)
    context.user_data.pop("diag_goal", None)

    await update.message.reply_text(f"🔎 Быстро и честно.\n\n{DIAG_Q1_TEXT}", reply_markup=DIAG_Q1_KB)
    return DIAG_Q1


async def diag_q1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text == MENU_BACK:
        return await menu_back(update, context)

    if text not in (DIAG_Q1_A, DIAG_Q1_B):
        await update.message.reply_text("Выбери вариант кнопкой 👇", reply_markup=DIAG_Q1_KB)
        return DIAG_Q1

    context.user_data["diag_blog"] = text
    await update.message.reply_text(DIAG_Q2_TEXT, reply_markup=DIAG_Q2_KB)
    return DIAG_Q2


async def diag_q2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text == MENU_BACK:
        return await menu_back(update, context)

    if text not in (DIAG_Q2_A, DIAG_Q2_B, DIAG_Q2_C):
        await update.message.reply_text("Выбери вариант кнопкой 👇", reply_markup=DIAG_Q2_KB)
        return DIAG_Q2

    await update.message.reply_text(
        "✅ *Подойдёт ли тебе это?*\n\nДержи 3 статьи — по делу 👇",
        reply_markup=DIAG_ARTICLES_KB,
        parse_mode="Markdown",
    )
    await show_menu(update, "Возвращаю в меню 👇")
    return ConversationHandler.END


# -------------------------
# Кейсы flow
# -------------------------

async def cases_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("📌 Выбирай кейс 👇", reply_markup=CASES_MENU_KB)
    return CASE_STATE


async def cases_handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text == MENU_BACK:
        return await menu_back(update, context)

    if text == CASE_100_WEEK:
        await update.message.reply_text(
            "💰 *100 тр без блога за неделю*\n\nСмотри по кнопке 👇",
            reply_markup=CASE_100_WEEK_INLINE,
            parse_mode="Markdown",
        )
        await update.message.reply_text("Выбирай следующий кейс 👇", reply_markup=CASES_MENU_KB)
        return CASE_STATE

    if text in CASES_STEPS:
        context.user_data["case_name"] = text
        context.user_data["case_step"] = 0
        await update.message.reply_text(CASES_STEPS[text][0], reply_markup=CASE_KB, parse_mode="Markdown")
        return CASE_STATE

    if text == CASE_NEXT:
        case_name = context.user_data.get("case_name")
        if not case_name or case_name not in CASES_STEPS:
            await update.message.reply_text("Сначала выбери кейс 👇", reply_markup=CASES_MENU_KB)
            return CASE_STATE

        idx = int(context.user_data.get("case_step", 0)) + 1
        context.user_data["case_step"] = idx

        steps = CASES_STEPS[case_name]
        if idx >= len(steps):
            await show_menu(update, "Возвращаю в меню.")
            return ConversationHandler.END

        await update.message.reply_text(steps[idx], reply_markup=CASE_KB, parse_mode="Markdown")
        return CASE_STATE

    await update.message.reply_text("Нажми кнопку 👇", reply_markup=CASES_MENU_KB)
    return CASE_STATE


# -------------------------
# Оплата / Я оплатила
# -------------------------

async def pay_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inline = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Перейти к оплате", url=PAY_URL)],
    ])

    pay_kb = ReplyKeyboardMarkup([[MENU_PAID], [MENU_BACK]], resize_keyboard=True)

    await update.message.reply_text(
        "Жми кнопку 👇",
        reply_markup=inline,
    )
    await update.message.reply_text(
        "После оплаты нажми *«✅ Я оплатила»* — дам доступ в чат мини-курса.",
        reply_markup=pay_kb,
        parse_mode="Markdown",
    )


async def paid_notify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inline = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎓 Войти в чат мини-курса", url=MINI_COURSE_CHAT_URL)],
    ])
    await update.message.reply_text(
        "✅ Принято.\nВот чат мини-курса — заходи 👇",
        reply_markup=inline,
    )
    await show_menu(update, "Выбирай 👇")

    admin_chat_id = context.application.bot_data.get("ADMIN_CHAT_ID")
    if not admin_chat_id:
        return

    tg_user_id, tg_username = user_identity(update)
    chat = update.effective_chat
    chat_id = chat.id if chat else None

    msg = "\n".join([
        "✅ Нажатие: «Я оплатила»",
        f"• TG user id: {tg_user_id}",
        f"• Username: @{tg_username}" if tg_username else "• Username: (не указан)",
        f"• Chat id: {chat_id}",
        f"• Оплата: {PAY_URL}",
        f"• Чат мини-курса: {MINI_COURSE_CHAT_URL}",
    ])

    try:
        await context.bot.send_message(chat_id=admin_chat_id, text=msg)
    except Exception:
        pass


# -------------------------
# Поддержка
# -------------------------

async def call_human(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Ок. Человека позвала.",
        reply_markup=MAIN_MENU_KB,
    )

    admin_chat_id = context.application.bot_data.get("ADMIN_CHAT_ID")
    if not admin_chat_id:
        return

    tg_user_id, tg_username = user_identity(update)
    chat = update.effective_chat
    chat_id = chat.id if chat else None
    text = update.effective_message.text if update.effective_message else ""

    msg = "\n".join([
        "🙋 Запрос: «Поддержка»",
        f"• TG user id: {tg_user_id}",
        f"• Username: @{tg_username}" if tg_username else "• Username: (не указан)",
        f"• Chat id: {chat_id}",
        f"• Сообщение: {text}",
    ])

    try:
        await context.bot.send_message(chat_id=admin_chat_id, text=msg)
    except Exception:
        pass


# -------------------------
# Error handler
# -------------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"❌ Ошибка: {context.error}")


# -------------------------
# Роутер меню (только то, что НЕ ConversationHandler)
# -------------------------

async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()

    if text == MENU_PAY:
        await pay_link(update, context)
        return

    if text == MENU_PAID:
        await paid_notify(update, context)
        return

    if text == MENU_HUMAN:
        await call_human(update, context)
        return

    if text == MENU_BACK:
        await show_menu(update)
        return

    await update.message.reply_text("Жми кнопки. Я тут не для переписки 😉", reply_markup=MAIN_MENU_KB)


# -------------------------
# main
# -------------------------

def main() -> None:
    token, admin_chat_id = require_env_vars()

    app = Application.builder().token(token).build()
    app.bot_data["ADMIN_CHAT_ID"] = admin_chat_id

    app.add_handler(CommandHandler("start", cmd_start))

    videos_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^{}$".format(re.escape(MENU_START))), videos_entry)],
        states={VIDEOS_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, videos_handle)]},
        fallbacks=[MessageHandler(filters.Regex(r"^{}$".format(re.escape(MENU_BACK))), menu_back)],
        allow_reentry=True,
    )
    app.add_handler(videos_conv)

    faq_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^{}$".format(re.escape(MENU_FAQ))), faq_entry)],
        states={FAQ_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, faq_handle)]},
        fallbacks=[MessageHandler(filters.Regex(r"^{}$".format(re.escape(MENU_BACK))), menu_back)],
        allow_reentry=True,
    )
    app.add_handler(faq_conv)

    diag_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^{}$".format(re.escape(MENU_DIAG))), diag_entry)],
        states={
            DIAG_Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, diag_q1)],
            DIAG_Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, diag_q2)],
        },
        fallbacks=[MessageHandler(filters.Regex(r"^{}$".format(re.escape(MENU_BACK))), menu_back)],
        allow_reentry=True,
    )
    app.add_handler(diag_conv)

    cases_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^{}$".format(re.escape(MENU_CASES))), cases_entry)],
        states={CASE_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cases_handle)]},
        fallbacks=[MessageHandler(filters.Regex(r"^{}$".format(re.escape(MENU_BACK))), menu_back)],
        allow_reentry=True,
    )
    app.add_handler(cases_conv)

    app.add_handler(MessageHandler(filters.Regex(r"^{}$".format(re.escape(MENU_PAY))), pay_link))
    app.add_handler(MessageHandler(filters.Regex(r"^{}$".format(re.escape(MENU_PAID))), paid_notify))
    app.add_handler(MessageHandler(filters.Regex(r"^{}$".format(re.escape(MENU_HUMAN))), call_human))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_router))

    app.add_error_handler(error_handler)

    print("Бот запущен (polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()