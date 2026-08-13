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
        "error": "❌ Xatolik: <code>{error}</code>",
        "no_result_url": "❌ Tayyor, lekin natija havolasi kelmadi.",
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
        "error": "❌ Ошибка: <code>{error}</code>",
        "no_result_url": "❌ Готово, но не пришёл URL результата.",
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
        "error": "❌ Error: <code>{error}</code>",
        "no_result_url": "❌ Finished, but no result URL was returned.",
        "denied": "⛔ You don't have access to this bot!",
        "choose_language": "🌐 Choose your language:",
        "language_set": "✅ Language updated.",
        "cmd_start": "Start the bot",
        "cmd_language": "Change language",
    },
}

LANGUAGES = tuple(TEXTS)


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
