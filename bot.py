import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8407680010:AAGnGWwH7ufhqx_acI6k-gdPndC5Knd7ajg" 
ADMIN_ID = 932894269  # Твой личный ID
# -----------------

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Создаем объекты бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Храним временные данные (кто на какое место жалуется)
user_reports = {} 

# 1. Хендлер на команду /start
@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    args = command.args
    
    if args and args.startswith("error_"):
        # Если пришли с жалобой
        place_name = args.replace("error_", "").replace("_", " ")
        user_reports[message.from_user.id] = place_name
        
        # Создаем клавиатуру с кнопками
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔴 Закрылось навсегда", callback_data="report_closed")],
            [InlineKeyboardButton(text="⛔ Не пускают с собакой", callback_data="report_not_allowed")],
            [InlineKeyboardButton(text="📍 Неверная геолокация", callback_data="report_location")],
            [InlineKeyboardButton(text="✏️ Ошибка в описании", callback_data="report_info")],
            [InlineKeyboardButton(text="📝 Другое (написать текстом)", callback_data="report_other")]
        ])
        
        await message.answer(
            f"Вы хотите сообщить об ошибке в <b>{place_name}</b>.\nВыберите проблему из списка:", 
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        # Если просто нажали /start
        await message.answer("Привет! Нажмите кнопку меню, чтобы открыть карту 🗺️")

# 2. Обработка нажатия на кнопки
@dp.callback_query(F.data.startswith("report_"))
async def handle_report_click(callback: CallbackQuery):
    user_id = callback.from_user.id
    reason_code = callback.data
    place_name = user_reports.get(user_id, "Неизвестное место")
    
    # Расшифровка причин
    reasons = {
        "report_closed": "🔴 Закрылось навсегда",
        "report_not_allowed": "⛔ Не пускают с собакой",
        "report_location": "📍 Неверная геолокация",
        "report_info": "✏️ Ошибка в описании"
    }

    # Если выбрали "Другое"
    if reason_code == "report_other":
        await callback.message.edit_text(f"Напишите текстом, что не так с <b>{place_name}</b>:", parse_mode="HTML")
        # Не удаляем из словаря, ждем текст
        return

    # Если выбрали готовую причину
    reason_text = reasons.get(reason_code, "Ошибка")
    
    # Отправляем админу
    admin_text = (
        f"📩 <b>НОВАЯ ЖАЛОБА</b>\n"
        f"📍 Место: <b>{place_name}</b>\n"
        f"⚠️ Причина: {reason_text}\n"
        f"👤 От: {callback.from_user.full_name} (@{callback.from_user.username})"
    )
    await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
    
    # Отвечаем юзеру
    await callback.message.edit_text(f"✅ Спасибо! Мы приняли жалобу по <b>{place_name}</b>:\n<i>{reason_text}</i>", parse_mode="HTML")
    await callback.answer()

# 3. Обработка текста (только если выбрали "Другое")
@dp.message()
async def handle_text(message: Message):
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
        
        del user_reports[user_id]

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
