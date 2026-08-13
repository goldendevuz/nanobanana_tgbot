"""Aiogram bot wired to the Django ORM."""

import asyncio
import logging
from html import escape

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils import timezone

from bot.i18n import (
    DEFAULT_LANGUAGE,
    LANGUAGE_NAMES,
    LANGUAGES,
    detect_language,
    t,
    variants,
)
from bot.models import GenerationTask, TelegramUser
from bot.services.image_service import (
    close_session,
    create_generation_task,
    extract_result_url,
    query_task_status,
)

logger = logging.getLogger(__name__)

# user ids the bot is currently expecting a prompt from
WAITING_PROMPT: set[int] = set()

LANG_CALLBACK_PREFIX = "lang:"


def main_menu(lang: str) -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text=t(lang, "btn_create"))],
            [types.KeyboardButton(text=t(lang, "btn_language"))],
        ],
        resize_keyboard=True,
    )


def language_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=LANGUAGE_NAMES[code],
                    callback_data=f"{LANG_CALLBACK_PREFIX}{code}",
                )
            ]
            for code in LANGUAGES
        ]
    )


# --------------------------------------------------------------------------- #
# ORM helpers
# --------------------------------------------------------------------------- #
@sync_to_async
def touch_user(tg_user: types.User) -> TelegramUser:
    """Create or refresh the TelegramUser row for an incoming update."""
    user, created = TelegramUser.objects.update_or_create(
        telegram_id=tg_user.id,
        defaults={
            "username": tg_user.username or "",
            "first_name": tg_user.first_name or "",
            "last_name": tg_user.last_name or "",
            "language_code": tg_user.language_code or "",
            "last_seen_at": timezone.now(),
        },
    )
    if created:
        user.is_allowed = tg_user.id == settings.ADMIN_USER_ID
        user.language = detect_language(tg_user.language_code)
        user.save(update_fields=["is_allowed", "language"])
        logger.info(
            "New Telegram user registered: %s (%s), language=%s",
            user.display_name,
            user.telegram_id,
            user.language,
        )
    return user


def has_access(user: TelegramUser) -> bool:
    if user.is_blocked:
        return False
    return (
        user.is_allowed
        or settings.BOT_ALLOW_EVERYONE
        or user.telegram_id == settings.ADMIN_USER_ID
    )


@sync_to_async
def set_language(user: TelegramUser, language: str) -> None:
    user.language = language
    user.save(update_fields=["language"])


@sync_to_async
def save_task(user: TelegramUser, task_id: str, chat_id: int, prompt: str, image_size: str) -> None:
    GenerationTask.objects.create(
        task_id=task_id,
        user=user,
        chat_id=chat_id,
        prompt=prompt,
        image_size=image_size,
        model=settings.KIE_MODEL,
    )


@sync_to_async
def pending_tasks() -> list[GenerationTask]:
    # select_related keeps task.user available without a query inside the async loop
    return list(
        GenerationTask.objects.filter(
            state__in=GenerationTask.PENDING_STATES,
            delivered=False,
        ).select_related("user")
    )


@sync_to_async
def update_task(task: GenerationTask, **fields) -> None:
    for name, value in fields.items():
        setattr(task, name, value)
    task.save(update_fields=[*fields, "updated_at"])


def task_language(task: GenerationTask) -> str:
    return task.user.language if task.user_id else DEFAULT_LANGUAGE


# --------------------------------------------------------------------------- #
# Background poller
# --------------------------------------------------------------------------- #
async def poll_tasks(bot: Bot) -> None:
    """Poll Kie.ai for unfinished tasks and deliver results to Telegram."""
    while True:
        await asyncio.sleep(settings.BOT_POLL_INTERVAL)

        for task in await pending_tasks():
            lang = task_language(task)

            try:
                status = await query_task_status(task.task_id)
            except Exception:
                logger.exception("query_task_status failed task_id=%s", task.task_id)
                continue

            if status.get("code") != 200:
                continue

            data = status.get("data") or {}
            state = data.get("state")

            if state in GenerationTask.PENDING_STATES:
                if state != task.state:
                    await update_task(task, state=state)
                continue

            if state == GenerationTask.State.FAIL:
                fail_message = data.get("failMsg") or "Unknown error"
                logger.error("Task failed task_id=%s msg=%s", task.task_id, fail_message)
                await update_task(
                    task,
                    state=GenerationTask.State.FAIL,
                    fail_message=fail_message,
                    finished_at=timezone.now(),
                    delivered=True,
                )
                await bot.send_message(
                    task.chat_id, t(lang, "error", error=escape(fail_message))
                )

            elif state == GenerationTask.State.SUCCESS:
                url = extract_result_url(data)
                if url:
                    logger.info("Task success task_id=%s url=%s", task.task_id, url)
                    await update_task(
                        task,
                        state=GenerationTask.State.SUCCESS,
                        result_url=url,
                        finished_at=timezone.now(),
                        delivered=True,
                    )
                    await bot.send_photo(task.chat_id, url, caption=t(lang, "done"))
                else:
                    logger.error("Task succeeded without a result URL task_id=%s", task.task_id)
                    await update_task(
                        task,
                        state=GenerationTask.State.SUCCESS,
                        fail_message="No result URL returned",
                        finished_at=timezone.now(),
                        delivered=True,
                    )
                    await bot.send_message(task.chat_id, t(lang, "no_result_url"))


# --------------------------------------------------------------------------- #
# Handlers
# --------------------------------------------------------------------------- #
def setup(dp: Dispatcher) -> None:
    @dp.message(CommandStart())
    async def start(message: types.Message) -> None:
        user = await touch_user(message.from_user)
        if not has_access(user):
            return await deny(message, user)
        WAITING_PROMPT.discard(user.telegram_id)
        await message.answer(
            t(user.language, "welcome"),
            reply_markup=main_menu(user.language),
        )

    @dp.message(Command("language"))
    @dp.message(F.text.in_(variants("btn_language")))
    async def on_language(message: types.Message) -> None:
        user = await touch_user(message.from_user)
        if not has_access(user):
            return await deny(message, user)
        WAITING_PROMPT.discard(user.telegram_id)
        await message.answer(
            t(user.language, "choose_language"),
            reply_markup=language_keyboard(),
        )

    @dp.callback_query(F.data.startswith(LANG_CALLBACK_PREFIX))
    async def on_language_chosen(callback: types.CallbackQuery) -> None:
        user = await touch_user(callback.from_user)
        if not has_access(user):
            return await callback.answer(t(user.language, "denied"), show_alert=True)

        language = callback.data.removeprefix(LANG_CALLBACK_PREFIX)
        if language not in LANGUAGES:
            return await callback.answer()

        await set_language(user, language)
        logger.info("Language changed user_id=%s language=%s", user.telegram_id, language)

        await callback.answer()
        await callback.message.edit_text(
            f"{t(language, 'language_set')} {LANGUAGE_NAMES[language]}"
        )
        await callback.message.answer(
            t(language, "welcome"),
            reply_markup=main_menu(language),
        )

    @dp.message(F.text.in_(variants("btn_create")))
    async def on_create(message: types.Message) -> None:
        user = await touch_user(message.from_user)
        if not has_access(user):
            return await deny(message, user)
        WAITING_PROMPT.add(user.telegram_id)
        await message.answer(t(user.language, "ask_prompt"))

    @dp.message(F.text)
    async def on_text(message: types.Message) -> None:
        user = await touch_user(message.from_user)
        if not has_access(user):
            return await deny(message, user)

        lang = user.language
        text = (message.text or "").strip()

        if user.telegram_id not in WAITING_PROMPT:
            return await message.answer(t(lang, "use_button"), reply_markup=main_menu(lang))

        if not text:
            return await message.answer(t(lang, "empty_prompt"))

        WAITING_PROMPT.discard(user.telegram_id)
        logger.info("Prompt received user_id=%s prompt=%r", user.telegram_id, text)
        await message.answer(t(lang, "generating"))

        try:
            task_id = await create_generation_task(prompt=text, image_size="1:1")
        except Exception as exc:
            logger.exception("create_generation_task failed user_id=%s", user.telegram_id)
            return await message.answer(t(lang, "error", error=escape(str(exc))))

        await save_task(user, task_id, message.chat.id, text, "1:1")
        logger.info("Task created task_id=%s chat_id=%s", task_id, message.chat.id)
        await message.answer(t(lang, "task_created"))


async def deny(message: types.Message, user: TelegramUser) -> None:
    logger.warning("Access denied for user_id=%s", user.telegram_id)
    await message.answer(t(user.language, "denied"))


async def set_commands(bot: Bot) -> None:
    """Publish the localized command menu for each supported language."""
    for language in LANGUAGES:
        commands = [
            types.BotCommand(command="start", description=t(language, "cmd_start")),
            types.BotCommand(command="language", description=t(language, "cmd_language")),
        ]
        await bot.set_my_commands(commands, language_code=language)
        if language == DEFAULT_LANGUAGE:
            # clients reporting an unsupported locale fall back to this list
            await bot.set_my_commands(commands)


# --------------------------------------------------------------------------- #
# Entrypoint
# --------------------------------------------------------------------------- #
async def run() -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    if not settings.KIE_API_KEY:
        raise RuntimeError("KIE_API_KEY is not set")

    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    setup(dp)

    poller = asyncio.create_task(poll_tasks(bot))
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await set_commands(bot)
        logger.info("Bot polling started")
        await dp.start_polling(bot)
    finally:
        poller.cancel()
        await close_session()
        await bot.session.close()
