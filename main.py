import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup
from telebot.custom_filters import SimpleCustomFilter
from telebot.storage import StateMemoryStorage
from config import TELEGRAM_BOT_TOKEN
from func import get_user_data, update_user_data, openai, create_table, create_db
import requests
from io import BytesIO
import json
from shapely.geometry import shape, Point

create_db()
create_table()
admin_id = "894349873"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, state_storage=StateMemoryStorage())



def download_image(url):
    response = requests.get(url)
    if response.status_code == 200:
        return BytesIO(response.content)
    return None


with open("data.geojson") as f:
    data = json.load(f)

for feature in data["features"]:
    if "description" in feature["properties"]:
        feature["properties"]["reports"] = 0

with open("upd_data.geojson", "w") as f:
    json.dump(data, f)


def get_location(latitude, longitude):
    try:
        point = Point(longitude, latitude)
        for feature in data["features"]:
            polygon = shape(feature["geometry"])
            if polygon.contains(point):
                return feature["properties"]["description"]
    except Exception as e:
        print(e)
        return None



def update_reports(latitude, longitude):
    point = Point(longitude, latitude)
    for feature in data["features"]:
        polygon = shape(feature["geometry"])
        if polygon.contains(point):
            feature["properties"]["reports"] += 1
            break


def get_user_state(message):
    user_data = get_user_data(message.chat.id)
    return user_data.get("state") if user_data else None


def send_report_to_admin(admin_id, photo_url, location, response_text):
    photo = download_image(photo_url)
    if photo:
        latitude, longitude = location
        caption = f"Получена фотография от пользователя.\n{response_text}\nГеолокация пользователя: {get_location(longitude=longitude, latitude=latitude)}"

        bot.send_photo(admin_id, photo, caption=caption)
    else:
        bot.send_message(admin_id, "Ошибка при загрузке фотографии.")


def find_district(latitude, longitude):
    point = Point(longitude, latitude)
    for feature in data["features"]:
        polygon = shape(feature["geometry"])
        if polygon.contains(point):
            return feature["properties"]["description"]
    return "Район не найден"


def update_user_state(message, state):
    update_user_data(telegram_id=message.chat.id, state=state)


def set_state(user_id, state):
    pass


@bot.message_handler(commands=["start"])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(text="Русский", callback_data="ru")
    btn2 = types.InlineKeyboardButton(text="Қазақша", callback_data="kz")
    markup.add(btn1, btn2)
    bot.send_message(
        message.chat.id, "Выберите язык👇🏻 / Тілді таңдаңыз👇🏻", reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data in ["ru", "kz"])
def callback_inline(call):
    language = "Русский" if call.data == "ru" else "Қазақша"
    update_user_data(telegram_id=call.message.chat.id, language=language)
    menu(call.message)


def menu(message):
    user_data = get_user_data(message.chat.id)
    if user_data:
        language = user_data["language"]
        markup = types.InlineKeyboardMarkup()
        if language == "Русский":
            btn1 = types.InlineKeyboardButton(
                "Сообщение о незаконной рекламе", callback_data="report_ad"
            )
            btn2 = types.InlineKeyboardButton(
                "Сообщение о незаконном производстве", callback_data="report_delivery"
            )
        elif language == "Қазақша":
            btn1 = types.InlineKeyboardButton(
                "Жалоба на рекламу", callback_data="report_ad"
            )
            btn2 = types.InlineKeyboardButton(
                "Жалоба на производство", callback_data="report_delivery"
            )
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
    else:
        bot.send_message(
            message.chat.id, "Ошибка, не удалось получить данные пользователя."
        )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    if call.data == "report_ad":
        update_user_data(call.message.chat.id, state="AWAITING_PHOTO")
        bot.send_message(
            call.message.chat.id, "Пожалуйста, отправьте фотографию незаконной рекламы."
        )
    elif call.data=="report_delivery":
        update_user_data(call.message.chat.id, state="AWAITING_REPORT")
        bot.send_message(
            call.message.chat.id, "Пожалуйста, отправьте фотографию о незаконном производстве(Прикрепите фото (не более двух). Не превышающее 10 МБ. Если нет, выберите Продолжить.)"
        )
    elif call.data=="Yes":
        bot.send_message(call.message.chat.id,"Укажите любую информацию о лице:Почему у вас это вызвало подозрения? Какие доказательства можно проверить на месте/увидеть на фото (кратко)?")
        update_user_data(call.message.chat.id,state="Text")
    elif call.data=="No":
        bot.send_message(call.message.chat.id,"Спасибо! ")


@bot.message_handler(
    content_types=["photo"],
    func=lambda message: get_user_state(message) == "AWAITING_REPORT",
)

def handle_report(message):
    photo_id = message.photo[-1].file_id
    file_info = bot.get_file(photo_id)
    photo_url = (
        f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info.file_path}"
    )


    bot.send_message(
        message.chat.id,
        "Фотография незаконной рекламы получена."
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    location_button = types.KeyboardButton("Отправить мою геолокацию", request_location=True)
    map_button = types.KeyboardButton("Выбрать точку на карте(Через меню телеграмма)")
    markup.add(location_button,map_button)
    update_user_data(message.chat.id, state="NEW_STATE_AFTER_REPORT", photo_url=photo_url)
    bot.send_message(
        message.chat.id,
        "Теперь, пожалуйста, отправьте геолокацию через меню телеграма",
        reply_markup=markup
    )




@bot.message_handler(
    content_types=["photo"],
    func=lambda message: get_user_state(message) == "AWAITING_PHOTO",
)
def handle_photo(message):
    photo_id = message.photo[-1].file_id
    file_info = bot.get_file(photo_id)
    photo_url = (
        f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info.file_path}"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    location_button = types.KeyboardButton("Отправить мою геолокацию", request_location=True)
    map_button = types.KeyboardButton("Выбрать точку на карте(Через меню телеграмма)")
    markup.add(location_button,map_button)
    update_user_data(message.chat.id, state="AWAITING_LOCATION", photo_url=photo_url)
    bot.send_message(
        message.chat.id,
        "Теперь, пожалуйста, отправьте геолокацию через меню телеграма",
        reply_markup=markup
    )

@bot.message_handler(
    content_types=["location"],
    func=lambda message: get_user_state(message) == "NEW_STATE_AFTER_REPORT",
)
def handle_location(message):
    markup_remove = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id,
        "Ваша геопозиция была принята",
        reply_markup=markup_remove
    )
    user_data = get_user_data(message.chat.id)
    if user_data and "photo_url" in user_data:
        photo_url = user_data["photo_url"]
        location = (message.location.latitude, message.location.longitude)
        response = openai(photo_url)

        send_report_to_admin(admin_id, photo_url, location, response)

        bot.send_message(
            message.chat.id, "Спасибо за ваше сообщение! Мы его рассмотрим."
        )
        markup=types.InlineKeyboardMarkup()
        btn_yes=types.InlineKeyboardButton(
                "Да", callback_data="Yes"
            )
        btn_no = types.InlineKeyboardButton(
            "Нет", callback_data="No"
        )
        markup.add(btn_yes,btn_no)
        bot.send_message(message.chat.id,
                         "Знаете ли вы, кто может там проживать/кто способен вести данное производство?",reply_markup=markup)

    else:
        bot.send_message(message.chat.id, "Ошибка: фотография не найдена.")

@bot.message_handler(
    content_types=["location"],
    func=lambda message: get_user_state(message) == "AWAITING_LOCATION",
)

def handle_location(message):
    markup_remove = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id,
        "Ваша геопозиция была принята",
        reply_markup=markup_remove
    )
    user_data = get_user_data(message.chat.id)
    if user_data and "photo_url" in user_data:
        photo_url = user_data["photo_url"]
        location = (message.location.latitude, message.location.longitude)
        response = openai(photo_url)

        send_report_to_admin(admin_id, photo_url, location, response)

        bot.send_message(
            message.chat.id, "Спасибо за ваше сообщение! Мы его рассмотрим."
        )
        update_user_data(message.chat.id, state=None)
    else:
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

bot.infinity_polling()
