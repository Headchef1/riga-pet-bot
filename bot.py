import asyncio
import logging
import os
import base64
import html
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

# --- ЛОКАЛИЗАЦИЯ ---
LOCALIZATION = {
    "en": {
        "welcome": "Hello! Press the menu button to open the map 🗺️",
        "report_intro": "You want to report an issue in <b>{place}</b>.\nChoose the problem:",
        "btn_closed": "🔴 Closed forever",
        "btn_not_allowed": "⛔ Dogs not allowed",
        "btn_location": "📍 Wrong location",
        "btn_info": "✏️ Wrong info/desc",
        "btn_other": "📝 Other (write text)",
        "write_text": "Please write what is wrong with <b>{place}</b>:",
        "thanks": "✅ Thank you! We accepted the report for <b>{place}</b>:\n<i>{reason}</i>",
        "msg_sent": "✅ Your message has been sent to the admin. Thank you!",
        "err_decoding": "Error processing the link.",
        # Тексты причин для отображения пользователю
        "reason_closed": "Closed forever",
        "reason_not_allowed": "Dogs not allowed",
        "reason_location": "Wrong location",
        "reason_info": "Wrong info"
    },
    "ru": {
        "welcome": "Привет! Нажмите кнопку меню, чтобы открыть карту 🗺️",
        "report_intro": "Вы хотите сообщить об ошибке в <b>{place}</b>.\nВыберите проблему из списка:",
        "btn_closed": "🔴 Закрылось навсегда",
        "btn_not_allowed": "⛔ Не пускают с собакой",
        "btn_location": "📍 Неверная геолокация",
        "btn_info": "✏️ Ошибка в описании",
        "btn_other": "📝 Другое (написать текстом)",
        "write_text": "Напишите текстом, что не так с <b>{place}</b>:",
        "thanks": "✅ Спасибо! Мы приняли жалобу по <b>{place}</b>:\n<i>{reason}</i>",
        "msg_sent": "✅ Ваше сообщение отправлено админу. Спасибо!",
        "err_decoding": "Ошибка в ссылке на место.",
        "reason_closed": "Закрылось навсегда",
        "reason_not_allowed": "Не пускают с собакой",
        "reason_location": "Неверная геолокация",
        "reason_info": "Ошибка в описании"
    },
    "lv": {
        "welcome": "Sveiki! Nospiediet izvēlnes pogu, lai atvērtu karti 🗺️",
        "report_intro": "Jūs vēlaties ziņot par kļūdu vietā <b>{place}</b>.\nIzvēlieties problēmu:",
        "btn_closed": "🔴 Slēgts uz visiem laikiem",
        "btn_not_allowed": "⛔ Ar suni neielaiž",
        "btn_location": "📍 Nepareiza atrašanās vieta",
        "btn_info": "✏️ Kļūda aprakstā",
        "btn_other": "📝 Cits (uzrakstīt)",
        "write_text": "Lūdzu, uzrakstiet, kas nav kārtībā ar <b>{place}</b>:",
        "thanks": "✅ Paldies! Mēs pieņēmām ziņojumu par <b>{place}</b>:\n<i>{reason}</i>",
        "msg_sent": "✅ Jūsu ziņojums nosūtīts administratoram. Paldies!",
        "err_decoding": "Kļūda saites apstrādē.",
        "reason_closed": "Slēgts uz visiem laikiem",
        "reason_not_allowed": "Ar suni neielaiž",
        "reason_location": "Nepareiza atrašanās vieta",
        "reason_info": "Kļūda aprakstā"
    }
}

def get_text(user_lang_code, key):
    """Возвращает текст на нужном языке (дефолт = en)"""
    if not user_lang_code:
        lang = "en"
    else:
        # Берем первые 2 буквы (ru-RU -> ru)
        lang = user_lang_code[:2].lower()
    
    # Если языка нет в словаре, используем английский
    return LOCALIZATION.get(lang, LOCALIZATION["en"]).get(key, key)

# --- ХЕНДЛЕРЫ ---

@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    args = command.args
    lang = message.from_user.language_code # Получаем язык пользователя
    
    # Логируем для отладки
    logging.info(f"DEBUG: User {message.from_user.id} ({lang}) pressed start with args: '{args}'")

    if args and args.startswith("error_"):
        try:
            # Декодирование Base64 (как мы делали раньше)
            encoded_payload = args.replace("error_", "")
            padding = len(encoded_payload) % 4
            if padding:
                encoded_payload += "=" * (4 - padding)
            
            decoded_bytes = base64.urlsafe_b64decode(encoded_payload)
            place_name = decoded_bytes.decode('utf-8')
            
            # Сохраняем место
            user_reports[message.from_user.id] = place_name
            
            # Создаем клавиатуру с ПЕРЕВЕДЕННЫМИ кнопками
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=get_text(lang, "btn_closed"), callback_data="report_closed")],
                [InlineKeyboardButton(text=get_text(lang, "btn_not_allowed"), callback_data="report_not_allowed")],
                [InlineKeyboardButton(text=get_text(lang, "btn_location"), callback_data="report_location")],
                [InlineKeyboardButton(text=get_text(lang, "btn_info"), callback_data="report_info")],
                [InlineKeyboardButton(text=get_text(lang, "btn_other"), callback_data="report_other")]
            ])
            
            safe_place_name = html.escape(place_name)
            text = get_text(lang, "report_intro").format(place=safe_place_name)
            
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logging.error(f"CRITICAL ERROR decoding payload: {e}")
            await message.answer(get_text(lang, "err_decoding"))
    else:
        # Просто приветствие на языке пользователя
        await message.answer(get_text(lang, "welcome"))

@dp.callback_query(F.data.startswith("report_"))
async def handle_report_click(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = callback.from_user.language_code
    reason_code = callback.data
    place_name = user_reports.get(user_id, "Unknown Place")
    safe_place_name = html.escape(place_name)
    
    # Маппинг кодов к ключам перевода
    reason_keys = {
        "report_closed": "reason_closed",
        "report_not_allowed": "reason_not_allowed",
        "report_location": "reason_location",
        "report_info": "reason_info"
    }

    if reason_code == "report_other":
        text = get_text(lang, "write_text").format(place=safe_place_name)
        await callback.message.edit_text(text, parse_mode="HTML")
        return

    # Получаем текст причины на языке ПОЛЬЗОВАТЕЛЯ для ответа ему
    user_reason_text = get_text(lang, reason_keys.get(reason_code, "err_decoding"))
    
    # Получаем текст причины на РУССКОМ для админа (чтобы тебе было понятно)
    admin_reason_text = get_text("ru", reason_keys.get(reason_code, "err_decoding"))
    
    # Отправляем отчет админу
    admin_text = (
        f"📩 <b>НОВАЯ ЖАЛОБА</b>\n"
        f"📍 Место: <b>{safe_place_name}</b>\n"
        f"⚠️ Причина: {admin_reason_text}\n" # Админу всегда на понятном языке
        f"👤 От: {callback.from_user.full_name} (@{callback.from_user.username}) [{lang}]"
    )
    
    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
        
        # Ответ пользователю на ЕГО языке
        user_response = get_text(lang, "thanks").format(place=safe_place_name, reason=user_reason_text)
        await callback.message.edit_text(user_response, parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"Failed to send report to admin: {e}")
        await callback.message.answer("Error.")
    
    if user_id in user_reports:
        del user_reports[user_id]
        
    await callback.answer()

@dp.message()
async def handle_text(message: Message):
    if message.text and message.text.lower().strip() in ["start", "/start"]: return
    
    user_id = message.from_user.id
    lang = message.from_user.language_code
    
    if user_id in user_reports:
        place_name = user_reports[user_id]
        safe_place_name = html.escape(place_name)
        
        admin_text = (
            f"📩 <b>ЖАЛОБА (ТЕКСТ)</b>\n"
            f"📍 Место: <b>{safe_place_name}</b>\n"
            f"💬 Текст: {html.escape(message.text)}\n"
            f"👤 От: {message.from_user.full_name} (@{message.from_user.username}) [{lang}]"
        )
        
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
        await message.answer(get_text(lang, "msg_sent"))
        
        del user_reports[user_id]

# --- ВЕБ-СЕРВЕР ---
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

async def main():
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
