import asyncio
import logging
import os
import base64
import html
import json
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    CallbackQuery,
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    WebAppInfo
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Memory storage for tracking user reports in progress
user_reports = {}

# --- LOCALIZATION ---
LOCALIZATION = {
    'en': {
        'welcome': "Hello! Press the menu button to open the map 🗺️",
        'report_intro': "You want to report an issue in <b>{place}</b>.\nChoose the problem:",
        'btn_closed': "Closed forever",
        'btn_notallowed': "Dogs not allowed",
        'btn_location': "Wrong location",
        'btn_info': "Wrong info/desc",
        'btn_other': "Other (write text)",
        'write_text': "Please write what is wrong with <b>{place}</b>:",
        'thanks': "Thank you! We accepted the report for <b>{place}</b>\n<i>{reason}</i>",
        'msg_sent': "Your message has been sent to the admin. Thank you!",
        'err_decoding': "Error processing the link.",
        'reason_closed': "Closed forever",
        'reason_notallowed': "Dogs not allowed",
        'reason_location': "Wrong location",
        'reason_info': "Wrong info",
        'admin_new_place': "📍 <b>New Place Suggested</b>\nName: {name}\nCategory: {category}\nComment: {comment}\nUser: @{username} ({user_id})\nCoords: <code>{lat}, {lon}</code>"
    },
    'ru': {
        'welcome': "Привет! Нажми кнопку меню, чтобы открыть карту 🗺️",
        'report_intro': "Вы хотите сообщить об ошибке в <b>{place}</b>.\nВыберите проблему:",
        'btn_closed': "Закрыто навсегда",
        'btn_notallowed': "С собакой не пускают",
        'btn_location': "Неверная локация",
        'btn_info': "Неверное описание",
        'btn_other': "Другое (написать)",
        'write_text': "Пожалуйста, напишите, что не так с <b>{place}</b>:",
        'thanks': "Спасибо! Мы приняли репорт по <b>{place}</b>\n<i>{reason}</i>",
        'msg_sent': "Сообщение отправлено администратору. Спасибо!",
        'err_decoding': "Ошибка обработки ссылки.",
        'reason_closed': "Закрыто навсегда",
        'reason_notallowed': "С собакой не пускают",
        'reason_location': "Неверная локация",
        'reason_info': "Неверное описание",
        'admin_new_place': "📍 <b>Предложено новое место</b>\nНазвание: {name}\nКатегория: {category}\nКомментарий: {comment}\nПользователь: @{username} ({user_id})\nКоординаты: <code>{lat}, {lon}</code>"
    },
    'lv': {
        'welcome': "Sveiki! Nospiediet izvēlnes pogu, lai atvērtu karti 🗺️",
        'report_intro': "Jūs vēlaties ziņot par kļūdu vietā <b>{place}</b>.\nIzvēlieties problēmu:",
        'btn_closed': "Slēgts uz visiem laikiem",
        'btn_notallowed': "Ar suni neielaiž",
        'btn_location': "Nepareiza atrašanās vieta",
        'btn_info': "Kļūda aprakstā",
        'btn_other': "Cits (uzrakstīt)",
        'write_text': "Lūdzu, uzrakstiet, kas nav kārtībā ar <b>{place}</b>:",
        'thanks': "Paldies! Mēs pieņēmām ziņojumu par <b>{place}</b>\n<i>{reason}</i>",
        'msg_sent': "Jūsu ziņojums nosūtīts administratoram. Paldies!",
        'err_decoding': "Kļūda saites apstrādē.",
        'reason_closed': "Slēgts uz visiem laikiem",
        'reason_notallowed': "Ar suni neielaiž",
        'reason_location': "Nepareiza atrašanās vieta",
        'reason_info': "Kļūda aprakstā",
        'admin_new_place': "📍 <b>Ieteikta jauna vieta</b>\nNosaukums: {name}\nKategorija: {category}\nKomentārs: {comment}\nLietotājs: @{username} ({user_id})\nKoordinātas: <code>{lat}, {lon}</code>"
    }
}

def get_text(user_lang_code, key):
    lang = user_lang_code[:2].lower() if user_lang_code else 'en'
    if lang not in LOCALIZATION:
        lang = 'en'
    return LOCALIZATION.get(lang, LOCALIZATION['en']).get(key, key)

# --- TELEGRAM BOT HANDLERS ---
@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    args = command.args
    lang = message.from_user.language_code
    
    if args and args.startswith("error_"):
        try:
            encoded_payload = args.replace("error_", "")
            # Pad Base64 string if necessary
            padding = len(encoded_payload) % 4
            if padding:
                encoded_payload += "=" * (4 - padding)
            
            decoded_bytes = base64.urlsafe_b64decode(encoded_payload)
            decoded_str = decoded_bytes.decode('utf-8')
            
            place_name = decoded_str
            place_address = ""
            if '|' in decoded_str:
                place_name, place_address = decoded_str.split('|', 1)
                
            user_reports[message.from_user.id] = {
                "name": place_name,
                "address": place_address
            }
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=get_text(lang, 'btn_closed'), callback_data="report_closed")],
                [InlineKeyboardButton(text=get_text(lang, 'btn_notallowed'), callback_data="report_notallowed")],
                [InlineKeyboardButton(text=get_text(lang, 'btn_location'), callback_data="report_location"),
                 InlineKeyboardButton(text=get_text(lang, 'btn_info'), callback_data="report_info")],
                [InlineKeyboardButton(text=get_text(lang, 'btn_other'), callback_data="report_other")]
            ])
            
            safe_place_name = html.escape(place_name)
            text = get_text(lang, 'report_intro').format(place=safe_place_name)
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logging.error(f"CRITICAL ERROR decoding payload: {e}")
            await message.answer(get_text(lang, 'err_decoding'))
    else:
        await message.answer(get_text(lang, 'welcome'))

@dp.callback_query(F.data.startswith("report_"))
async def handle_report_click(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = callback.from_user.language_code
    reason_code = callback.data
    
    report_data = user_reports.get(user_id, {"name": "Unknown Place", "address": ""})
    place_name = report_data.get("name", "Unknown Place")
    
    safe_user_place_name = html.escape(place_name)
    
    reason_keys = {
        "report_closed": "reason_closed",
        "report_notallowed": "reason_notallowed",
        "report_location": "reason_location",
        "report_info": "reason_info"
    }
    
    if reason_code == "report_other":
        text = get_text(lang, 'write_text').format(place=safe_user_place_name)
        await callback.message.edit_text(text, parse_mode="HTML")
        return
        
    user_reason_text = get_text(lang, reason_keys.get(reason_code, "err_decoding"))
    admin_reason_text = get_text("ru", reason_keys.get(reason_code, "err_decoding")) # Admin sees RU by default
    
    place_block = f"<b>{html.escape(place_name)}</b>"
    
    admin_text = (
        f"🚨 <b>Быстрый репорт</b>\n"
        f"Место: {place_block}\n"
        f"Проблема: <b>{admin_reason_text}</b>\n\n"
        f"От: {callback.from_user.full_name} (@{callback.from_user.username})\n"
        f"Язык юзера: {lang}"
    )
    
    try:
        if ADMIN_ID != 0:
            await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
        
        user_response = get_text(lang, 'thanks').format(place=safe_user_place_name, reason=user_reason_text)
        await callback.message.edit_text(user_response, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Failed to send report to admin: {e}")
        await callback.message.answer("Error.")
        
    await callback.answer()

@dp.message()
async def handle_text_message(message: Message):
    if message.text and message.text.lower().strip() in ["/start", "start"]:
        return
        
    user_id = message.from_user.id
    lang = message.from_user.language_code
    
    if user_id in user_reports:
        report_data = user_reports[user_id]
        place_name = report_data.get("name", "Unknown")
        
        place_block = f"<b>{html.escape(place_name)}</b>"
        
        admin_text = (
            f"📝 <b>Репорт текстом</b>\n"
            f"Место: {place_block}\n"
            f"Сообщение: <i>{html.escape(message.text)}</i>\n\n"
            f"От: {message.from_user.full_name} (@{message.from_user.username})\n"
            f"Язык юзера: {lang}"
        )
        
        if ADMIN_ID != 0:
            await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
            
        await message.answer(get_text(lang, 'msg_sent'))
        del user_reports[user_id]
    else:
        # Если пишут просто так - предлагаем карту
        await message.answer(get_text(lang, "welcome"))



# --- AIOHTTP WEB SERVER & API ---

# Add CORS headers so frontend can POST from anywhere during dev
def get_cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }

async def health_check_request(request):
    return web.Response(text="Bot is running!", headers=get_cors_headers())

async def handle_options(request):
    # Preflight request handler for CORS
    return web.Response(headers=get_cors_headers())

async def api_add_place(request):
    try:
        data = await request.json()
        name     = html.escape(data.get('name', 'Unknown'))
        category = html.escape(data.get('category', 'none'))
        comment  = html.escape(data.get('comment', ''))
        lat      = data.get('lat', 0.0)
        lon      = data.get('lon', 0.0)
        username = html.escape(data.get('username', 'anonymous'))
        user_id  = data.get('user_id', 0)

        # Notify admin
        admin_msg = get_text("ru", "admin_new_place").format(
            name=name, category=category, comment=comment,
            username=username, user_id=user_id, lat=lat, lon=lon
        )

        if ADMIN_ID != 0:
            markup = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Mark as Reviewed", callback_data="admin_reviewed")
            ]])
            await bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML", reply_markup=markup)

        # Notify user in chat — send confirmation back to the person who submitted
        if user_id and user_id != 0:
            user_confirm = {
                'en': f"✅ <b>Your submission has been received!</b>\n\nPlace: <b>{name}</b>\nWe'll review it and add to the map soon. Thank you! 🐾",
                'ru': f"✅ <b>Заявка принята!</b>\n\nМесто: <b>{name}</b>\nМы проверим и скоро добавим на карту. Спасибо! 🐾",
                'lv': f"✅ <b>Pieteikums saņemts!</b>\n\nVieta: <b>{name}</b>\nMēs to pārbaudīsim un drīz pievienosim kartei. Paldies! 🐾"
            }
            # We don't know user lang here, send in all? No — default to RU as target audience
            # Better: frontend can pass lang in payload (future improvement)
            msg_text = user_confirm.get('ru')
            try:
                await bot.send_message(user_id, msg_text, parse_mode="HTML")
            except Exception as e:
                logging.warning(f"Could not notify user {user_id}: {e}")

        return web.json_response({"status": "success"}, headers=get_cors_headers())

    except Exception as e:
        logging.error(f"API Error: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=400, headers=get_cors_headers())


# Simple callback for admin review button
@dp.callback_query(F.data == "admin_reviewed")
async def admin_review_cb(callback: CallbackQuery):
    await callback.message.edit_text(callback.message.text + "\n\n<b>✅ REVIEWED</b>", parse_mode="HTML")
    await callback.answer()

async def start_web_server():
    app = web.Application()
    app.router.add_options('/api/add_place', handle_options)
    app.router.add_post('/api/add_place', api_add_place)
    app.router.add_get('/', health_check_request)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Web server started on port {port}")

async def main():
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
