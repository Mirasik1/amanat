import telebot
from telebot import types, custom_filters
import folium
from branca.colormap import LinearColormap
import geopandas as gpd
from telebot.handler_backends import State, StatesGroup
from telebot.custom_filters import SimpleCustomFilter
from telebot.storage import StateMemoryStorage
from config import TELEGRAM_BOT_TOKEN
from func import get_user_data, update_user_data, openai, create_table, create_db
import requests
from io import BytesIO
import json
from shapely.geometry import shape, Point
import context
state_storage=StateMemoryStorage()
context.create_db()
admin_id = "894349873"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, state_storage=state_storage)
url=""


class Allstates(StatesGroup):
    language = State()
    geo = State()
    photo=State()
    report = State()
    choice = State()
    additional_info = State()
    send = State()

def increment_report(latitude, longitude):
    gdf = 
    point = Point(longitude, latitude)
    selected_object = gdf[gdf.geometry.contains(point)].iloc[0]
    selected_object['report'] += 1

    gdf.loc[gdf.index == selected_object.name] = selected_object


@bot.message_handler(commands=["start"])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(text="Русский", callback_data="ru")
    btn2 = types.InlineKeyboardButton(text="Қазақша", callback_data="kz")
    markup.add(btn1, btn2)
    bot.send_message(
        message.chat.id, "Выберите язык👇🏻 / Тілді таңдаңыз👇🏻", reply_markup=markup
    )
    bot.set_state(message.from_user.id,Allstates.language,message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data in ["ru", "kz"], state=Allstates.language)
def callback_inline(call):
    # Русский-0, Казахский-1
    language = 0 if call.data == "ru" else 1
    if context.get_language_by_telegram_id(call.message.from_user.id) ==None:
        context.insert_user(call.message.from_user.id, language)
        menu(call.message)
    else:
        context.change_language_by_telegram_id(call.message.from_user.id, language)
        menu(call.message)

def menu(message):
    
    language = context.get_language_by_telegram_id(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if language == 0:
        btn1 = types.KeyboardButton("рекламу_ру")
        btn2 = types.KeyboardButton("производство_ру")
    elif language == 1:
        btn1 = types.KeyboardButton("рекламу_Каз")
        btn2 = types.KeyboardButton("производство_каз")
    else:
        bot.send_message(
            message.chat.id, "Ошибка, язык не найден. Попробуйте еще раз: /start"
        )
        return

    markup.add(btn1, btn2)
    bot.send_message(
        message.chat.id,
        """Добро пожаловать в Sheker Emes Bot! 💚

В данном боте вы можете анонимно сообщить о:

- Случаях распространения и рекламы наркотических веществ💊
- Факте производства наркотических веществ❗️

Для выбора типа жалобы нажмите на соответствующую кнопку⬇️""",
        reply_markup=markup,
    )
    
   
@bot.message_handler(content_types=["text"],func=lambda message: message.text in ["рекламу_ру", "производство_ру", "рекламу_Каз", "производство_каз"])
def report(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['report_type'] = message.text
    bot.send_message(message.chat.id, 'Отправьте фотографию')
    bot.send_message(message.chat.id, data)
    bot.set_state(message.from_user.id, Allstates.photo, message.chat.id)
    
@bot.message_handler(content_types=["photo"],state=Allstates.photo)
def handle_photo(message):
    photo_id = message.photo[-1].file_id
    file_info = bot.get_file(photo_id)
    photo_url = (
        f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info.file_path}"
    )
    global url
    url=photo_url
    bot.send_message(message.chat.id,"Video")
    bot.set_state(message.from_user.id,Allstates.geo,message.chat.id)
    bot.send_message(message.chat.id,"Теперь, пожалуйста, отправьте геолокацию через меню телеграма")
    
@bot.message_handler(content_types=["location"],state=Allstates.geo)
def handle_location(message):
    markup_remove = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id,
        "Ваша геопозиция была принята",
        reply_markup=markup_remove
    )
    try:
        photo_url = url

        response = openai(photo_url)
        bot.send_message(
            message.chat.id, "Спасибо за ваше сообщение! Мы его рассмотрим."
        )
        bot.send_message(admin_id, response)
        markup = types.InlineKeyboardMarkup()
        btn_yes = types.InlineKeyboardButton(
            "Да", callback_data="Yes"
        )
        btn_no = types.InlineKeyboardButton(
            "Нет", callback_data="No"
        )
        markup.add(btn_yes, btn_no)
        bot.send_message(message.chat.id,
                         "Знаете ли вы, кто может там проживать/кто способен вести данное производство?",
                         reply_markup=markup)

    except Exception as e:
        bot.send_message(message.chat.id, "Ошибка: фотография не найдена.")


@bot.message_handler(commands=["info"])
def show_info(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    #    for district in districts:
       # markup.add(
       #     types.InlineKeyboardButton(district, callback_data="district_" + district)
       # )
    #bot.send_message(message.chat.id, "Выберите район:", reply_markup=markup)
    pass

@bot.message_handler(commands=["map"])
def show_map(message):
    center_latitude = 51.1694
    center_longitude = 71.4491
    m = folium.Map(location=[center_latitude, center_longitude], zoom_start=12)
    
    colormap = LinearColormap(['green', 'yellow', 'red'], vmin=0, vmax=50, index=[0, 25, 50])
    colormap.caption = 'Кол-во'

    gdf = gpd.read_file("data.geojson")
    gdf['report'] = gdf['report'].fillna(0)
    gdf = gdf.sort_values(by='report')
    
    for _, row in gdf.iterrows():
        color = colormap(row['report'])
        color = color[:-2]
        folium.GeoJson(row['geometry'],
                   style_function=lambda x, color=color: {'fillColor': color, 'color': 'none', 'weight': 0},
                   tooltip=f"{row['description']}<br>Репортов: {int(row['report'])}").add_to(m)
    
    m.options['clickable'] = False

    m.save("index.html")

bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling(skip_pending=True)
