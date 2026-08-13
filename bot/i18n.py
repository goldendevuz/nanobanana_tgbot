"""Translation catalogue for the Telegram bot.

Bot copy is switched per user at runtime (from ``TelegramUser.language``), so the
strings live in a plain dict instead of gettext catalogues — no ``.mo`` compilation
step, and matching an incoming button press against every language is trivial.
"""

DEFAULT_LANGUAGE = "uz"

LANGUAGE_NAMES = {
    "uz": "🇺🇿 O'zbekcha",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}

TEXTS: dict[str, dict[str, str]] = {
    "uz": {
        "welcome": "Tugmani bosing va prompt yuboring 👇",
        "btn_create": "🖼 Rasm yaratish",
        "btn_language": "🌐 Til",
        "ask_prompt": "📝 Rasm uchun promptni yozing.",
        "use_button": "Quyidagi tugmani bosing 👇",
        "empty_prompt": "Prompt bo'sh. Nima yaratamiz — matn bilan yozing.",
        "generating": "⏳ Generatsiya boshlandi…",
        "task_created": "✅ Vazifa yaratildi. Tayyor bo'lishi bilan rasmni yuboraman.",
        "done": "Tayyor! ✅",
        "err_sensitive": (
            "🚫 Bu so'rov bo'yicha rasm yaratilmadi — matn yoki natija taqiqlangan "
            "mavzuga tegishli deb topildi.\n\nBoshqacha, yumshoqroq prompt yozib ko'ring."
        ),
        "err_rate_limit": (
            "⏳ Hozir so'rovlar juda ko'p.\n\nBir-ikki daqiqadan so'ng qayta urinib ko'ring."
        ),
        "err_balance": (
            "💳 Xizmat balansi tugagan, shuning uchun rasm yaratilmadi.\n\n"
            "Iltimos, admin bilan bog'laning."
        ),
        "err_service": (
            "🔌 Rasm yaratish xizmati javob bermayapti.\n\nBirozdan keyin qayta urinib ko'ring."
        ),
        "err_generic": (
            "😕 Nimadir xato ketdi va rasm yaratilmadi.\n\nQayta urinib ko'ring — "
            "takrorlansa, admin bilan bog'laning."
        ),
        "no_result_url": "😕 Rasm tayyor bo'ldi, lekin uni yuklab bo'lmadi. Qayta urinib ko'ring.",
        "denied": "⛔ Sizda ushbu botdan foydalanish huquqi yo'q!",
        "choose_language": "🌐 Tilni tanlang:",
        "language_set": "✅ Til o'zgartirildi.",
        "cmd_start": "Botni ishga tushirish",
        "cmd_language": "Tilni o'zgartirish",
    },
    "ru": {
        "welcome": "Нажми кнопку и отправь промпт 👇",
        "btn_create": "🖼 Создать изображение",
        "btn_language": "🌐 Язык",
        "ask_prompt": "📝 Напиши промпт для генерации изображения.",
        "use_button": "Нажми кнопку ниже 👇",
        "empty_prompt": "Промпт пустой. Напиши текстом, что генерируем.",
        "generating": "⏳ Запускаю генерацию…",
        "task_created": "✅ Задача создана. Как будет готово — пришлю изображение.",
        "done": "Готово! ✅",
        "err_sensitive": (
            "🚫 Изображение не создано — запрос или результат распознан как "
            "запрещённая тема.\n\nПопробуйте сформулировать промпт иначе."
        ),
        "err_rate_limit": (
            "⏳ Сейчас слишком много запросов.\n\nПопробуйте снова через пару минут."
        ),
        "err_balance": (
            "💳 На сервисе закончился баланс, изображение не создано.\n\n"
            "Пожалуйста, свяжитесь с админом."
        ),
        "err_service": (
            "🔌 Сервис генерации не отвечает.\n\nПопробуйте ещё раз чуть позже."
        ),
        "err_generic": (
            "😕 Что-то пошло не так, изображение не создано.\n\nПопробуйте ещё раз — "
            "если повторится, свяжитесь с админом."
        ),
        "no_result_url": "😕 Изображение готово, но его не удалось загрузить. Попробуйте ещё раз.",
        "denied": "⛔ У вас нет доступа к этому боту!",
        "choose_language": "🌐 Выберите язык:",
        "language_set": "✅ Язык изменён.",
        "cmd_start": "Запустить бота",
        "cmd_language": "Сменить язык",
    },
    "en": {
        "welcome": "Tap the button and send a prompt 👇",
        "btn_create": "🖼 Create image",
        "btn_language": "🌐 Language",
        "ask_prompt": "📝 Send the prompt for your image.",
        "use_button": "Use the button below 👇",
        "empty_prompt": "The prompt is empty. Describe what to generate.",
        "generating": "⏳ Starting generation…",
        "task_created": "✅ Task created. I'll send the image once it's ready.",
        "done": "Done! ✅",
        "err_sensitive": (
            "🚫 No image was created — the request or the result was flagged as a "
            "restricted topic.\n\nTry rewording your prompt."
        ),
        "err_rate_limit": (
            "⏳ There are too many requests right now.\n\nPlease try again in a minute or two."
        ),
        "err_balance": (
            "💳 The service is out of credit, so no image was created.\n\n"
            "Please contact the admin."
        ),
        "err_service": (
            "🔌 The image service is not responding.\n\nPlease try again shortly."
        ),
        "err_generic": (
            "😕 Something went wrong and no image was created.\n\nPlease try again — "
            "if it keeps happening, contact the admin."
        ),
        "no_result_url": "😕 The image was ready but could not be downloaded. Please try again.",
        "denied": "⛔ You don't have access to this bot!",
        "choose_language": "🌐 Choose your language:",
        "language_set": "✅ Language updated.",
        "cmd_start": "Start the bot",
        "cmd_language": "Change language",
    },
}

LANGUAGES = tuple(TEXTS)

# Raw upstream error text -> the message key the user actually sees. Checked in order,
# so put the specific matches first. Everything unmatched falls back to "err_generic";
# the original text is kept on the task and in the logs for staff.
ERROR_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "err_sensitive",
        (
            "flagged as sensitive",
            "sensitive",
            "content policy",
            "safety",
            "prohibited",
            "not allowed",
            "nsfw",
            "violat",
        ),
    ),
    ("err_rate_limit", ("rate limit", "too many requests", "429", "concurren")),
    ("err_balance", ("insufficient", "credit", "balance", "quota", "payment", "402")),
    (
        "err_service",
        ("timeout", "timed out", "unavailable", "gateway", "502", "503", "504", "connection"),
    ),
)


def classify_error(message: object) -> str:
    """Map an upstream failure message onto a plain, user-facing explanation."""
    text = str(message).lower()
    for key, needles in ERROR_PATTERNS:
        if any(needle in text for needle in needles):
            return key
    return "err_generic"


def t(lang: str | None, key: str, **kwargs) -> str:
    """Return the translated string for ``key``, falling back to the default language."""
    catalogue = TEXTS.get(lang or "", TEXTS[DEFAULT_LANGUAGE])
    text = catalogue.get(key) or TEXTS[DEFAULT_LANGUAGE][key]
    return text.format(**kwargs) if kwargs else text


def variants(key: str) -> set[str]:
    """Every translation of ``key`` — used to match button presses in any language."""
    return {catalogue[key] for catalogue in TEXTS.values() if key in catalogue}


def detect_language(telegram_code: str | None) -> str:
    """Pick a supported language from Telegram's client locale (e.g. ``en-US``)."""
    code = (telegram_code or "").split("-")[0].lower()
    return code if code in TEXTS else DEFAULT_LANGUAGE
