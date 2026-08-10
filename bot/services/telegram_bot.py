"""Aiogram bot wired to the Django ORM."""

import asyncio
import logging

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils import timezone

from bot.models import GenerationTask, TelegramUser
from bot.services.image_service import (
    close_session,
    create_generation_task,
    extract_result_url,
    query_task_status,
)

logger = logging.getLogger(__name__)

BTN_CREATE = "🖼 Создать изображение"

# user ids the bot is currently expecting a prompt from
WAITING_PROMPT: set[int] = set()


def main_menu() -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=BTN_CREATE)]],
        resize_keyboard=True,
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
        user.save(update_fields=["is_allowed"])
        logger.info("New Telegram user registered: %s (%s)", user.display_name, user.telegram_id)
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
    return list(
        GenerationTask.objects.filter(
            state__in=GenerationTask.PENDING_STATES,
            delivered=False,
        )
    )


@sync_to_async
def update_task(task: GenerationTask, **fields) -> None:
    for name, value in fields.items():
        setattr(task, name, value)
    task.save(update_fields=[*fields, "updated_at"])


# --------------------------------------------------------------------------- #
# Background poller
# --------------------------------------------------------------------------- #
async def poll_tasks(bot: Bot) -> None:
    """Poll Kie.ai for unfinished tasks and deliver results to Telegram."""
    while True:
        await asyncio.sleep(settings.BOT_POLL_INTERVAL)

        for task in await pending_tasks():
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
                await bot.send_message(task.chat_id, f"❌ Ошибка: <code>{fail_message}</code>")

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
                    await bot.send_photo(task.chat_id, url, caption="Готово! ✅")
                else:
                    logger.error("Task succeeded without a result URL task_id=%s", task.task_id)
                    await update_task(
                        task,
                        state=GenerationTask.State.SUCCESS,
                        fail_message="No result URL returned",
                        finished_at=timezone.now(),
                        delivered=True,
                    )
                    await bot.send_message(task.chat_id, "❌ Готово, но не пришел URL результата.")


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
        await message.answer("Нажми кнопку и отправь промпт 👇", reply_markup=main_menu())

    @dp.message(F.text == BTN_CREATE)
    async def on_create(message: types.Message) -> None:
        user = await touch_user(message.from_user)
        if not has_access(user):
            return await deny(message, user)
        WAITING_PROMPT.add(user.telegram_id)
        await message.answer("📝 Напиши промпт для генерации изображения.")

    @dp.message(F.text)
    async def on_text(message: types.Message) -> None:
        user = await touch_user(message.from_user)
        if not has_access(user):
            return await deny(message, user)

        text = (message.text or "").strip()

        if user.telegram_id not in WAITING_PROMPT:
            return await message.answer("Нажми кнопку ниже 👇", reply_markup=main_menu())

        if not text:
            return await message.answer("Промпт пустой. Напиши текстом, что генерируем.")

        WAITING_PROMPT.discard(user.telegram_id)
        logger.info("Prompt received user_id=%s prompt=%r", user.telegram_id, text)
        await message.answer("⏳ Запускаю генерацию…")

        try:
            task_id = await create_generation_task(prompt=text, image_size="1:1")
        except Exception as exc:
            logger.exception("create_generation_task failed user_id=%s", user.telegram_id)
            return await message.answer(f"❌ Ошибка: <code>{exc}</code>")

        await save_task(user, task_id, message.chat.id, text, "1:1")
        logger.info("Task created task_id=%s chat_id=%s", task_id, message.chat.id)
        await message.answer("✅ Задача создана. Как будет готово - пришлю изображение.")


async def deny(message: types.Message, user: TelegramUser) -> None:
    logger.warning("Access denied for user_id=%s", user.telegram_id)
    await message.answer("⛔ У вас нет доступа к этому боту!")


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
        logger.info("Bot polling started")
        await dp.start_polling(bot)
    finally:
        poller.cancel()
        await close_session()
        await bot.session.close()
