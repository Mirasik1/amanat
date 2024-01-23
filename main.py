import telebot
from telebot import types, custom_filters
import folium
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
from config import TELEGRAM_BOT_TOKEN
import func
from messages import messages as msg

state_storage = StateMemoryStorage()
func.create_db()
func.create_reports_table()
admin_id = "894349873"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, state_storage=state_storage)


class AllStates(StatesGroup):
    language = State()
    geo = State()
    photo = State()
    report = State()
    choice = State()
    additional_info = State()
    send = State()
    additional_info_1 = State()


@bot.message_handler(commands=["start"])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton(text="Русский")
    btn2 = types.KeyboardButton(text="Қазақша")
    markup.add(btn1, btn2)
    bot.send_message(message.chat.id, "Выберите язык👇🏻 / Тілді таңдаңыз👇🏻", reply_markup=markup)
    bot.set_state(message.from_user.id, AllStates.language, message.chat.id)


@bot.message_handler(content_types=["text"],
                     func=lambda message: message.text in ["Русский", "Қазақша"],state=AllStates.language)
def callback_inline(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['language'] = 0 if message.text == "Русский" else 1
    print(data)
    menu(message)


def menu(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        language = data['language']
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton(msg["btn_ad"][language])
    btn2 = types.KeyboardButton(msg["btn_manu"][language])
    markup.add(btn1, btn2)
    bot.send_message(
        message.chat.id,
        msg["text_welcome"][language],
        reply_markup=markup,
    )


@bot.message_handler(content_types=["text"],
                     func=lambda message: message.text in ["Незаконная реклама📰", "Заңсыз жарнама📰", "Незаконное производство🏭", "Заңсыз өндіріс🏭"])
def report(message):

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['report_type'] = message.text
        language = data['language']
    markup_remove = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, msg["text_photo"][language],reply_markup=markup_remove)
    bot.set_state(message.from_user.id, AllStates.photo, message.chat.id)


@bot.message_handler(content_types=["text"],
                     func=lambda message: message.text in ["Нет", "Да", "Жоқ", "Иә"], state=AllStates.additional_info)
def send(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        language = data['language']
    markup_remove = types.ReplyKeyboardRemove()
    if message.text == "Да" or message.text == "Иә":
        bot.set_state(message.from_user.id, AllStates.additional_info_1, message.chat.id)
        bot.send_message(message.chat.id, msg["text_add_info_1"][language],reply_markup=markup_remove)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['ad_info'] = message.text

    else:
        bot.send_message(message.chat.id, msg["report_end"][language], reply_markup=markup_remove)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['ad_info'] = message.text
            data['ad_info_text'] = "No"
            func.add_response(message.chat.id, data)


@bot.message_handler(state=AllStates.additional_info_1)
def ask_ad_info(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['ad_info_text'] = message.text
        language = data['language']

    bot.send_message(message.chat.id,msg["report_end"][language])
    func.add_response(message.chat.id, data)

    bot.set_state(message.from_user.id,AllStates.send,message.chat.id)


@bot.message_handler(content_types=["photo"], state=AllStates.photo)
def handle_photo(message):
    photo_id = message.photo[-1].file_id
    file_info = bot.get_file(photo_id)
    photo_url = (
        f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info.file_path}"
    )
    url = photo_url
    response = "skip"
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        language = data['language']
        data['response'] = response
        data['photo_url'] = url

    bot.set_state(message.from_user.id, AllStates.geo, message.chat.id)
    bot.send_message(message.chat.id,msg["text_geo"][language])


@bot.message_handler(content_types=["location"], state=AllStates.geo)
def handle_location(message):
    longitude = message.location.longitude
    latitude = message.location.latitude
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        language = data['language']
        data['longitude'] = longitude
        data['latitude'] = latitude

    try:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_yes = types.KeyboardButton(
            msg['yes'][language]
        )
        btn_no = types.KeyboardButton(
            msg['no'][language]
        )
        markup.add(btn_yes, btn_no)
        bot.send_message(message.chat.id,
                         msg["text_add_info"][language],
                         reply_markup=markup)
        bot.set_state(message.from_user.id,AllStates.additional_info,message.chat.id)

    except Exception as e:
        bot.send_message(message.chat.id, "Ошибка: фотография не найдена.")


@bot.message_handler(commands=["map"])
def show_map(message):
    center_latitude = 51.1694
    center_longitude = 71.4491
    m = folium.Map(location=[center_latitude, center_longitude], zoom_start=12)

    data = func.get_all_reports()
    for report in data:
        _, _, report_type, _, ad_info, _, longitude, latitude, ad_info_text = report
        folium.Marker(
            location=[latitude, longitude],
            popup=f"Type: {report_type}, Description: {ad_info_text}",
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(m)

    m.save("index.html")
    m.options['clickable'] = False
    m.save("index.html")


@bot.message_handler(state="*", commands=['cancel'])
def any_state(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        language = data['language']
    bot.send_message(message.chat.id, msg["text_cancel"][language])
    bot.delete_state(message.from_user.id, message.chat.id)


@bot.message_handler(commands=['excel'])
def send_excel(message):
    func.create_excel("reports")
    file_path = "reports.xlsx"
    with open(file_path, 'rb') as file:
        bot.send_document(message.chat.id, document=file)


@bot.message_handler(commands=['list'])
def send_admin(message):
    admin_text=[]
    reports = func.get_all_reports()
    if reports is not None:
        for report in reports:
            admin_text.append(report)
    admin_text = str(admin_text)
    bot.send_message(admin_id, admin_text)


bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling(skip_pending=True)