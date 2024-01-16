import telebot
from telebot import types, custom_filters
import folium
from branca.colormap import LinearColormap
import geopandas as gpd
from telebot.handler_backends import State, StatesGroup
from telebot.custom_filters import SimpleCustomFilter
from telebot.storage import StateMemoryStorage
from config import TELEGRAM_BOT_TOKEN
from func import get_user_data, update_user_data, openai, create_db

from shapely.geometry import shape, Point
import context

state_storage = StateMemoryStorage()
context.create_db()
context.create_reports_table()
admin_id = "894349873"
bot = telebot.TeleBot("6811743988:AAEYlMWjrZIVbCvNxQ1YHBfyG7JhpyFkSOU", state_storage=state_storage)
url = ""
response=''
longitude=0
latitude=0

class Allstates(StatesGroup):
    language = State()
    geo = State()
    photo = State()
    report = State()
    choice = State()
    additional_info = State()
    send = State()
    additional_info_1=State()


def increment_report(latitude, longitude):
    gdf = gpd.read_file("data.geojson")
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
    bot.set_state(message.from_user.id, Allstates.language, message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data in ["ru", "kz"], state=Allstates.language)
def callback_inline(call):

    # Русский-0, Казахский-1
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Выберите язык👇🏻 / Тілді таңдаңыз👇🏻",
        reply_markup=None
    )
    language = 0 if call.data == "ru" else 1
    if context.get_language_by_telegram_id(call.message.from_user.id) == None:
        context.insert_user(call.message.from_user.id, language)
        menu(call.message)
    else:
        context.change_language_by_telegram_id(call.message.from_user.id, language)
        menu(call.message)


def menu(message):

    language = context.get_language_by_telegram_id(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if language == 0:
        btn1 = types.KeyboardButton("Незаконной реклама📰")
        btn2 = types.KeyboardButton("Незаконное производство🏭")
    elif language == 1:
        btn1 = types.KeyboardButton("Заңсыз жарнама📰")
        btn2 = types.KeyboardButton("Заңсыз өндіріс🏭")
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


@bot.message_handler(content_types=["text"],
                     func=lambda message: message.text in ["Незаконной реклама📰", "Незаконное производство🏭", "Заңсыз жарнама📰",
                                                           "Заңсыз өндіріс🏭"])
def report(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['report_type'] = message.text
    markup_remove = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, 'Отправьте фотографию',reply_markup=markup_remove)

    bot.set_state(message.from_user.id, Allstates.photo, message.chat.id)
@bot.message_handler(content_types=["text"],
                     func=lambda message: message.text in ["Нет", "Да"],state=Allstates.additional_info)
def send(message):
    markup_remove = types.ReplyKeyboardRemove()
    if message.text =="Да":
        bot.set_state(message.from_user.id, Allstates.additional_info_1, message.chat.id)
        bot.send_message(message.chat.id, "Напишите допольнительную информацию",reply_markup=markup_remove)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['ad_info'] = message.text
            data['response'] = response
            data['photo_url'] = url
            data['longitude'] = longitude
            data['latitude'] = latitude
    else:
        bot.send_message(message.chat.id, "Хорошо", reply_markup=markup_remove)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['ad_info'] = message.text
            data['response']=response
            data['photo_url'] = url
            data['longitude'] = longitude
            data['latitude'] = latitude
            data['ad_info_text']=""
            context.add_response(message.chat.id, data)
            admin_text = context.get_all_reports()
            bot.send_message(admin_id, str(data))

            increment_report(data['latitude'], data['longitude'])




@bot.message_handler(commands=['list'])
def send_admin(message):
    if message.chat.id == admin_id:
        admin_text = context.get_all_reports()
        bot.send_message(admin_id, admin_text)
    else:
        pass
@bot.message_handler(state=Allstates.additional_info_1)
def ask_ad_info(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['ad_info_text'] = message.text

    bot.send_message(message.chat.id,"Спасибо за ваше сообщение мы его рассмотрим")
    context.add_response(message.chat.id, data)
    bot.set_state(message.from_user.id,Allstates.send,message.chat.id)

    bot.send_message(admin_id, str(data))


    increment_report(data['latitude'], data['longitude'])




@bot.message_handler(content_types=["photo"], state=Allstates.photo)
def handle_photo(message):
    photo_id = message.photo[-1].file_id
    file_info = bot.get_file(photo_id)
    photo_url = (
        f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info.file_path}"
    )

    global url,response
    url = photo_url

    response = openai(url)


    bot.set_state(message.from_user.id, Allstates.geo, message.chat.id)
    bot.send_message(message.chat.id, "Теперь, пожалуйста отправьте геолокацию через меню телеграмма")


@bot.message_handler(content_types=["location"], state=Allstates.geo)
def handle_location(message):
    global longitude,latitude
    longitude = message.location.longitude
    latitude = message.location.latitude
    markup_remove = types.ReplyKeyboardRemove()

    try:


        bot.send_message(
            message.chat.id, "Спасибо за ваше сообщение! Мы его рассмотрим.",
            reply_markup=markup_remove
        )

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_yes = types.KeyboardButton(
            "Да"
        )
        btn_no = types.KeyboardButton(
            "Нет"
        )
        markup.add(btn_yes, btn_no)
        bot.send_message(message.chat.id,
                         "Знаете ли вы, кто может там проживать/кто способен вести данное производство?",
                         reply_markup=markup)
        bot.set_state(message.from_user.id,Allstates.additional_info,message.chat.id)
    except Exception as e:
        bot.send_message(message.chat.id, "Ошибка: фотография не найдена.")

@bot.message_handler(state="*", commands=['cancel'])
def any_state(message):
    bot.send_message(message.chat.id, "Вы отменили")
    bot.delete_state(message.from_user.id, message.chat.id)
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


@bot.message_handler(commands=['excel'])
def send_excel(message):
    file_path = "C:/Users/Admin/PycharmProjects/amanat/reports.xlsx"
    with open(file_path, 'rb') as file:
        bot.send_document(message.chat.id, document=file)



bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling(skip_pending=True)