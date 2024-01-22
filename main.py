import telebot
from telebot import types, custom_filters
import folium
from branca.colormap import LinearColormap
import geopandas as gpd
from telebot.handler_backends import State, StatesGroup
from telebot.custom_filters import SimpleCustomFilter
from telebot.storage import StateMemoryStorage
from config import TELEGRAM_BOT_TOKEN
from func import openai
import func

from shapely.geometry import shape, Point
from messages import messages as msg

state_storage = StateMemoryStorage()
func.create_db()
func.create_reports_table()
admin_id = "894349873"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, state_storage=state_storage)


class Allstates(StatesGroup):
    language = State()
    menu = State()
    photo = State()
    geo = State()
    additional_info = State()
    report = State()
    choice = State()
    send = State()


@bot.message_handler(commands=["start"])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(text="Русский", callback_data="ru")
    btn2 = types.InlineKeyboardButton(text="Қазақша", callback_data="kz")
    markup.add(btn1, btn2)
    bot.send_message(
        message.chat.id, "Выберите язык👇🏻 / Тілді таңдаңыз👇🏻", reply_markup=markup
    )
    bot.set_state(message.from_user.id, Allstates.language, message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data in ["ru", "kz"], state=Allstates.language)
def callback_inline(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Выберите язык👇🏻 / Тілді таңдаңыз👇🏻",
        reply_markup=None
    )
    language = 0 if call.data == "ru" else 1
    if func.get_language_by_telegram_id(call.message.from_user.id) == None:
        func.insert_user(call.message.from_user.id, language)
    else:
        func.change_language_by_telegram_id(call.message.from_user.id, language)
    menu(call.message)


def menu(message):
    language = func.get_language_by_telegram_id(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(msg["btn_ad"][language], callback_data="ad")
    btn2 = types.InlineKeyboardButton(msg["btn_manu"][language], callback_data="manu")
    
    markup.add(btn1, btn2)
    bot.send_message(
        message.chat.id,
        msg["text_welcome"][language],
        reply_markup=markup,
    )
    bot.set_state(message.from_user.id, Allstates.menu, message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data in ["ad", "manu"], state=Allstates.language)
def report(call):
    language = func.get_language_by_telegram_id(call.message.from_user.id)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=msg["text_welcome"][language],
        reply_markup=None
    )
    with bot.retrieve_data(call.message.from_user.id, call.message.chat.id) as data:
        data['report_type'] = call.data
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_skip = types.KeyboardButton(
        msg['skip'][language]
    )
    markup.add(btn_skip)
    bot.set_state(call.message.from_user.id, Allstates.photo, call.message.chat.id)
    bot.send_message(call.message.chat.id, msg["text_photo"][language], reply_markup=markup)



@bot.message_handler(content_types=["photo"], state=Allstates.photo)
def handle_photo(message):
    photo_id = message.photo[-1].file_id
    file_info = bot.get_file(photo_id)
    photo_url = (
        f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info.file_path}"
    )
    bot.send_message(message.chat.id,msg["loading"][language])
    response = openai(url)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['response'] = response
        data['photo_url'] = photo_url

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_skip = types.KeyboardButton(
        msg['skip'][language]
    )
    markup.add(btn_skip)
    bot.set_state(message.from_user.id, Allstates.geo, message.chat.id)
    bot.send_message(message.chat.id,msg["text_geo"][language], reply_markup=markup)


@bot.message_handler(content_types=["location"], state=Allstates.geo)
def handle_location(message):
    language = func.get_language_by_telegram_id(message.from_user.id)


    longitude = message.location.longitude
    latitude = message.location.latitude

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['longitude'] = longitude
        data['latitude'] = latitude

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_no = types.KeyboardButton(
        msg['no'][language]
    )
    markup.add(btn_no)
    
    bot.send_message(message.chat.id,
                     msg["text_add_info"][language],
                     reply_markup=markup)
    bot.set_state(message.from_user.id, Allstates.additional_info, message.chat.id)

@bot.message_handler(content_types=["text"], state=Allstates.additional_info)
def send(message):
    markup_remove = types.ReplyKeyboardRemove()
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['ad_info'] = message.text
    
    bot.send_message(message.chat.id,msg["report_end"][language])
    bot.set_state(message.from_user.id, Allstates.send, message.chat.id)


    bot.send_message(admin_id, str(data))




@bot.message_handler(state="*", commands=['cancel'])
def any_state(message):
    language = func.get_language_by_telegram_id(message.from_user.id)
    bot.send_message(message.chat.id, msg["text_cancel"][language])
    bot.delete_state(message.from_user.id, message.chat.id)



@bot.message_handler(commands=["map"])
def show_map(message):
    center_latitude = 51.1694
    center_longitude = 71.4491
    m = folium.Map(location=[center_latitude, center_longitude], zoom_start=12)

    data = func.get_all_reports()

    for report in data:
        _, report_type, ad_info, response, _, longitude, latitude, ad_info_text = report
        folium.Marker(
            location=[lat, lon],
            popup=f"Type: {report_type}, Description: { ad_info_text }",
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(map)

    m.save("index.html")

    m.options['clickable'] = False

    m.save("index.html")

@bot.message_handler(func=lambda message: message.text in ["Пропустить", "Өткізіп жіберу"], state=Allstates.photo)
def skip_photo(message):
    language = func.get_language_by_telegram_id(message.from_user.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['response'] = None
        data['photo_url'] = None

    bot.send_message(message.chat.id, msg["text_geo"][0])
    bot.set_state(message.from_user.id, Allstates.geo, message.chat.id)

@bot.message_handler(func=lambda message: message.text in ["Пропустить", "Өткізіп жіберу"], state=Allstates.geo)
def skip_geo(message):
    language = func.get_language_by_telegram_id(message.from_user.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['longitude'] = None
        data['latitude'] = None

    bot.send_message(message.chat.id, msg["text_add_info"][0])
    bot.set_state(message.from_user.id, Allstates.additional_info, message.chat.id)
    

@bot.message_handler(commands=['list'])
def send_admin(message):

    if message.chat.id == admin_id:
        admin_text = func.get_all_reports()
        bot.send_message(admin_id, admin_text)
    else:
        pass

@bot.message_handler(commands=['excel'])
def send_excel(message):
    func.create_excel("reports")
    file_path = "./reports.xlsx"
    with open(file_path, 'rb') as file:
        bot.send_document(message.chat.id, document=file)


bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling(skip_pending=True)