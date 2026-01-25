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

# Теперь будем хранить словарь: {user_id: {"name": "Place", "address": "Street 1"}}
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
    if not user_lang_code:
        lang = "en"
    else:
        lang = user_lang_code[:2].lower()
    return LOCALIZATION.get(lang, LOCALIZATION["en"]).get(key, key)


# --- ХЕНДЛЕРЫ ---

@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    args = command.args
    lang = message.from_user.language_code
    
    logging.info(f"DEBUG: User {message.from_user.id} ({lang}) pressed start with args: '{args}'")

    if args and args.startswith("error_"):
        try:
            encoded_payload = args.replace("error_", "")
            padding = len(encoded_payload) % 4
            if padding:
                encoded_payload += "=" * (4 - padding)
            
            decoded_bytes = base64.urlsafe_b64decode(encoded_payload)
            decoded_str = decoded_bytes.decode('utf-8')

            # --- ИЗМЕНЕНИЕ 1: Парсинг адреса ---
            # Ожидаем формат: "Название места|Адрес"
            if "|" in decoded_str:
                place_name, place_address = decoded_str.split("|", 1)
            else:
                place_name = decoded_str
                place_address = ""
            
            # Сохраняем и имя, и адрес
            user_reports[message.from_user.id] = {
                "name": place_name, 
                "address": place_address
            }
            # -----------------------------------
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=get_text(lang, "btn_closed"), callback_data="report_closed")],
                [InlineKeyboardButton(text=get_text(lang, "btn_not_allowed"), callback_data="report_not_allowed")],
                [InlineKeyboardButton(text=get_text(lang, "btn_location"), callback_data="report_location")],
                [InlineKeyboardButton(text=get_text(lang, "btn_info"), callback_data="report_info")],
                [InlineKeyboardButton(text=get_text(lang, "btn_other"), callback_data="report_other")]
            ])
            
            # Формируем красивое название для пользователя (с адресом, если есть)
            display_name = place_name
            if place_address:
                display_name = f"{place_name} ({place_address})"

            safe_place_name = html.escape(display_name)
            text = get_text(lang, "report_intro").format(place=safe_place_name)
            
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logging.error(f"CRITICAL ERROR decoding payload: {e}")
            await message.answer(get_text(lang, "err_decoding"))
    else:
        await message.answer(get_text(lang, "welcome"))


@dp.callback_query(F.data.startswith("report_"))
async def handle_report_click(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = callback.from_user.language_code
    reason_code = callback.data
    
    # --- ИЗМЕНЕНИЕ 2: Получение данных из новой структуры ---
    report_data = user_reports.get(user_id, {"name": "Unknown Place", "address": ""})
    
    # Защита от старых данных (если вдруг в памяти осталась строка)
    if isinstance(report_data, str):
        place_name = report_data
        place_address = ""
    else:
        place_name = report_data.get("name", "Unknown Place")
        place_address = report_data.get("address", "")
    
    # Полное название для отображения пользователю
    full_display_name = f"{place_name} ({place_address})" if place_address else place_name
    safe_user_place_name = html.escape(full_display_name)
    # --------------------------------------------------------

    reason_keys = {
        "report_closed": "reason_closed",
        "report_not_allowed": "reason_not_allowed",
        "report_location": "reason_location",
        "report_info": "reason_info"
    }

    if reason_code == "report_other":
        text = get_text(lang, "write_text").format(place=safe_user_place_name)
        await callback.message.edit_text(text, parse_mode="HTML")
        return

    user_reason_text = get_text(lang, reason_keys.get(reason_code, "err_decoding"))
    admin_reason_text = get_text("ru", reason_keys.get(reason_code, "err_decoding"))
    
    # --- ФОРМИРОВАНИЕ ОТЧЕТА ДЛЯ АДМИНА ---
    safe_name_only = html.escape(place_name)
    place_block = f"📍 Место: <b>{safe_name_only}</b>"
    
    # Если адрес есть, добавляем его отдельной строкой
    if place_address:
        place_block += f"\n🏢 Адрес: <b>{html.escape(place_address)}</b>"

    admin_text = (
        f"📩 <b>НОВАЯ ЖАЛОБА</b>\n"
        f"{place_block}\n"
        f"⚠️ Причина: {admin_reason_text}\n"
        f"👤 От: {callback.from_user.full_name} (@{callback.from_user.username}) [{lang}]"
    )
    # --------------------------------------
    
    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
        
        user_response = get_text(lang, "thanks").format(place=safe_user_place_name, reason=user_reason_text)
        await callback.message.edit_text(user_response, parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"Failed to send report to admin: {e}")
        await callback.message.answer("Error.")
        
    await callback.answer()


@dp.message()
async def handle_text(message: Message):
    if message.text and message.text.lower().strip() in ["start", "/start"]: return
    
    user_id = message.from_user.id
    lang = message.from_user.language_code
    
    if user_id in user_reports:
        # --- ИЗМЕНЕНИЕ 3: Аналогично для текстовой жалобы ---
        report_data = user_reports[user_id]
        if isinstance(report_data, str):
            place_name = report_data
            place_address = ""
        else:
            place_name = report_data.get("name", "Unknown")
            place_address = report_data.get("address", "")

        safe_name_only = html.escape(place_name)
        place_block = f"📍 Место: <b>{safe_name_only}</b>"
        if place_address:
            place_block += f"\n🏢 Адрес: <b>{html.escape(place_address)}</b>"

        admin_text = (
            f"📩 <b>ЖАЛОБА (ТЕКСТ)</b>\n"
            f"{place_block}\n"
            f"💬 Текст: {html.escape(message.text)}\n"
            f"👤 От: {message.from_user.full_name} (@{message.from_user.username}) [{lang}]"
        )
        # ----------------------------------------------------
        
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
        await message.answer(get_text(lang, "msg_sent"))
        
        del user_reports[user_id]

# --- ВЕБ-СЕРВЕР (без изменений) ---
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
