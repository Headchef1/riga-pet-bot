import asyncio
import logging
import os
import base64
from aiohttp import web
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

# --- ХЕНДЛЕРЫ ---

@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    args = command.args
    
    # Логируем для отладки
    logging.info(f"DEBUG: User {message.from_user.id} pressed start with args: '{args}'")

    if args and args.startswith("error_"):
        try:
            # 1. Получаем зашифрованную строку (payload)
            encoded_payload = args.replace("error_", "")
            
            # 2. Восстанавливаем padding (знаки =), если они были обрезаны
            # Base64 требует, чтобы длина строки делилась на 4
            padding = len(encoded_payload) % 4
            if padding:
                encoded_payload += "=" * (4 - padding)
            
            # 3. Декодируем из Base64 -> bytes -> utf-8 строка
            decoded_bytes = base64.urlsafe_b64decode(encoded_payload)
            place_name = decoded_bytes.decode('utf-8')
            
            logging.info(f"DEBUG: Decoded place name: {place_name}")

            # Сохраняем место в память (временный кэш)
            user_reports[message.from_user.id] = place_name
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔴 Закрылось навсегда", callback_data="report_closed")],
                [InlineKeyboardButton(text="⛔ Не пускают с собакой", callback_data="report_not_allowed")],
                [InlineKeyboardButton(text="📍 Неверная геолокация", callback_data="report_location")],
                [InlineKeyboardButton(text="✏️ Ошибка в описании", callback_data="report_info")],
                [InlineKeyboardButton(text="📝 Другое (написать текстом)", callback_data="report_other")]
            ])
            
            # Экранируем HTML спецсимволы в названии места (на всякий случай)
            import html
            safe_place_name = html.escape(place_name)
            
            await message.answer(
                f"Вы хотите сообщить об ошибке в <b>{safe_place_name}</b>.\nВыберите проблему из списка:", 
                reply_markup=keyboard, 
                parse_mode="HTML"
            )
            
        except Exception as e:
            logging.error(f"CRITICAL ERROR decoding payload: {e}")
            await message.answer("Произошла ошибка при обработке ссылки. Попробуйте еще раз.")
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
        # Мы не удаляем user_reports[user_id], чтобы запомнить место для следующего текстового сообщения
        return

    reason_text = reasons.get(reason_code, "Ошибка")
    
    # Отправляем отчет админу
    admin_text = (
        f"📩 <b>НОВАЯ ЖАЛОБА</b>\n"
        f"📍 Место: <b>{place_name}</b>\n"
        f"⚠️ Причина: {reason_text}\n"
        f"👤 От: {callback.from_user.full_name} (@{callback.from_user.username})"
    )
    
    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
        await callback.message.edit_text(f"✅ Спасибо! Мы приняли жалобу по <b>{place_name}</b>:\n<i>{reason_text}</i>", parse_mode="HTML")
    except Exception as e:
        logging.error(f"Failed to send report to admin: {e}")
        await callback.message.answer("Ошибка отправки репорта.")
    
    # Очищаем память
    if user_id in user_reports:
        del user_reports[user_id]
        
    await callback.answer()

@dp.message()
async def handle_text(message: Message):
    if message.text and message.text.lower().strip() in ["start", "/start"]: return
    
    user_id = message.from_user.id
    if user_id in user_reports:
        place_name = user_reports[user_id]
        
        admin_text = (
            f"📩 <b>ЖАЛОБА (ТЕКСТ)</b>\n"
            f"📍 Место: <b>{place_name}</b>\n"
            f"💬 Текст: {message.text}\n"
            f"👤 От: {message.from_user.full_name} (@{message.from_user.username})"
        )
        
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
        await message.answer("✅ Ваше сообщение отправлено админу. Спасибо!")
        
        # Очищаем память
        del user_reports[user_id]

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def health_check(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server started on port {port}")

# --- ЗАПУСК ---
async def main():
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
