import asyncio
import json
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from image_service import create_generation_task, query_task_status

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

BTN_CREATE = "🖼 Создать изображение"

def main_menu() -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=BTN_CREATE)]],
        resize_keyboard=True,
    )

WAITING_PROMPT: set[int] = set() # user_id, от которого ждем промпт
TASK_CHAT: dict[str, int] = {}   # task_id -> chat_id

async def check_access(message: types.Message) -> bool:
    if message.from_user.id != ADMIN_USER_ID:
        logging.warning("Access denied for user_id=%s", message.from_user.id)
        await message.answer("⛔ У вас нет доступа к этому боту!")
        return False
    return True


async def poll_tasks(bot: Bot) -> None:
    while True:
        await asyncio.sleep(3)

        for task_id in list(TASK_CHAT.keys()):
            chat_id = TASK_CHAT.get(task_id)
            if chat_id is None:
                TASK_CHAT.pop(task_id, None)
                continue

            try:
                status = await query_task_status(task_id)
            except Exception:
                logging.exception("query_task_status failed task_id=%s", task_id)
                continue

            if status.get("code") != 200:
                continue

            data = status.get("data") or {}
            state = data.get("state")

            if state in ("waiting", "queuing", "generating"):
                continue

            if state == "fail":
                fail_msg = data.get("failMsg") or "Unknown error"
                logging.error("Task failed task_id=%s msg=%s", task_id, fail_msg)
                await bot.send_message(chat_id, f"❌ Ошибка: <code>{fail_msg}</code>", parse_mode="HTML")

            elif state == "success":
                try:
                    result_json = json.loads(data.get("resultJson") or "{}")
                except json.JSONDecodeError:
                    result_json = {}

                urls = result_json.get("resultUrls") or []
                if urls:
                    logging.info("Task success task_id=%s url=%s", task_id, urls[0])
                    await bot.send_photo(chat_id, urls[0], caption="Готово! ✅")
                else:
                    logging.error("Task success but not resultUrls task_id=%s", task_id)
                    await bot.send_message(chat_id, "❌ Готово, но не пришел URL результата.")

            TASK_CHAT.pop(task_id, None)


def setup(dp: Dispatcher) -> None:
    @dp.message(CommandStart())
    async def start(message: types.Message) -> None:
        if not await check_access(message):
            return
        logging.info("Start user_id:%s", message.from_user.id)
        WAITING_PROMPT.discard(message.from_user.id)
        await message.answer("Нажми кнопку и отправь промпт 👇", reply_markup=main_menu())

    @dp.message(F.text == BTN_CREATE)
    async def on_create(message: types.Message) -> None:
        if not await check_access(message):
            return
        logging.info("Create clicked user_id=%s", message.from_user.id)
        WAITING_PROMPT.add(message.from_user.id)
        await message.answer("📝 Напиши промпт для генерации изображения.")

    @dp.message(F.text)
    async def on_text(message: types.Message) -> None:
        if not await check_access(message):
            return
        
        user_id = message.from_user.id
        text = (message.text or "").strip()

        if user_id not in WAITING_PROMPT:
            return await message.answer("Нажми кнопку ниже 👇", reply_markup=main_menu())
        
        if not text:
            return await message.answer("Промпт пустой. Напиши текстом, что генерируем.")
        
        WAITING_PROMPT.discard(user_id)

        logging.info("Prompt received user_id=%s prompt=%r", user_id, text)
        await message.answer("⏳ Запускаю генерацию…")

        try:
            task_id = await create_generation_task(prompt=text, image_size="1:1")
        except Exception as e:
            return await message.answer(f"❌ Ошибка: <code>{e}</code>", parse_mode="HTML")

        logging.info("Task created task_id=%s chat_id=%s", task_id, message.chat.id)
        TASK_CHAT[task_id] = message.chat.id
        await message.answer("✅ Задача создана. Как будет готово - пришлю изображение.")

async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    logging.info("Bot starting...")

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    setup(dp)

    asyncio.create_task(poll_tasks(bot))

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
