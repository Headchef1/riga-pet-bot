import asyncio
import logging
import os
from aiohttp import web # Добавляем веб-сервер
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from dotenv import load_dotenv

# --- НАСТРОЙКИ ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
# -----------------

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_reports = {} 

# --- (ТВОИ ХЕНДЛЕРЫ ОСТАЮТСЯ ТЕМИ ЖЕ) ---
# Скопируй сюда свои функции cmd_start, handle_report_click, handle_text
# Или просто вставь этот код, если он у тебя такой же как был:

@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    args = command.args
    if args and args.startswith("error_"):
        place_name = args.replace("error_", "").replace("_", " ")
        user_reports[message.from_user.id] = place_name
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔴 Закрылось навсегда", callback_data="report_closed")],
            [InlineKeyboardButton(text="⛔ Не пускают с собакой", callback_data="report_not_allowed")],
            [InlineKeyboardButton(text="📍 Неверная геолокация", callback_data="report_location")],
            [InlineKeyboardButton(text="✏️ Ошибка в описании", callback_data="report_info")],
            [InlineKeyboardButton(text="📝 Другое (написать текстом)", callback_data="report_other")]
        ])
        await message.answer(f"Вы хотите сообщить об ошибке в <b>{place_name}</b>.\nВыберите проблему из списка:", reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer("Привет! Нажмите кнопку меню, чтобы открыть карту 🗺️")

@dp.callback_query(F.data.startswith("report_"))
async def handle_report_click(callback: CallbackQuery):
    user_id = callback.from_user.id
    reason_code = callback.data
    place_name = user_reports.get(user_id, "Неизвестное место")
    reasons = {
        "report_closed": "🔴 Закрылось навсегда",
        "report_not_allowed": "⛔ Не пускают с собакой",
        "report_location": "📍 Неверная геолокация",
        "report_info": "✏️ Ошибка в описании"
    }
    if reason_code == "report_other":
        await callback.message.edit_text(f"Напишите текстом, что не так с <b>{place_name}</b>:", parse_mode="HTML")
        return
    reason_text = reasons.get(reason_code, "Ошибка")
    admin_text = f"📩 <b>НОВАЯ ЖАЛОБА</b>\n📍 Место: <b>{place_name}</b>\n⚠️ Причина: {reason_text}\n👤 От: {callback.from_user.full_name} (@{callback.from_user.username})"
    await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
    await callback.message.edit_text(f"✅ Спасибо! Мы приняли жалобу по <b>{place_name}</b>:\n<i>{reason_text}</i>", parse_mode="HTML")
    await callback.answer()

@dp.message()
async def handle_text(message: Message):
    if message.text.lower().strip() in ["start", "/start"]: return
    user_id = message.from_user.id
    if user_id in user_reports:
        place_name = user_reports[user_id]
        admin_text = f"📩 <b>ЖАЛОБА (ТЕКСТ)</b>\n📍 Место: <b>{place_name}</b>\n💬 Текст: {message.text}\n👤 От: {message.from_user.full_name} (@{message.from_user.username})"
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
        await message.answer("✅ Ваше сообщение отправлено админу. Спасибо!")
        del user_reports[user_id]

# --- НОВАЯ ФУНКЦИЯ ДЛЯ RENDER ---
async def health_check(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    # Создаем мини-сайт
    app = web.Application()
    app.router.add_get('/', health_check) # На главной странице пишем "Bot is running"
    
    # Запускаем его на порту, который выдал Render (или 8080)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080)) # Render сам положит сюда нужный порт
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server started on port {port}")

# --- ОБНОВЛЕННЫЙ ЗАПУСК ---
async def main():
    # Запускаем и веб-сервер (чтобы Render был доволен), и бота
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
