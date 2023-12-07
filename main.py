import telebot
import logging
import requests
from io import BytesIO
import json
from kz import messages as kz_msgs
from ru import messages as ru_msgs
from telebot import types
from telebot.handler_backends import State, StatesGroup
from telebot import custom_filters
from telebot.storage import StateMemoryStorage
from config import TELEGRAM_BOT_TOKEN
from func import (
    get_user_data,
    update_user_data,
    openai,
    create_db,
    insert_into_db,

)


# Initialization
state_storage = StateMemoryStorage()

create_db()
admin_id = "1096958608"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, state_storage=state_storage)


# States
class RegisterStates(StatesGroup):
    language = State()
    menu = State()


class AdStates(StatesGroup):
    photo = State()
    geolocation = State()
    receive = State()
    add_info = State()


class ManuStates(StatesGroup):
    photo = State()
    geolocation = State()
    receive = State()
    add_info = State()
class ReportStates(StatesGroup):
    photo = State()
    geolocation = State()
    receive = State()
    add_info = State()



# Additional functions
def get_message(user_id, message_key):
    data = get_user_data(user_id)
    if data["language"] == "ru":
        return ru_msgs[message_key]
    else:
        return kz_msgs[message_key]


# Main code
@bot.message_handler(commands=["start"])
def handle_register(message):
    bot.send_message(message.chat.id, "👇🏻Тілді таңдаңыз / Выберите язык👇🏻")
    bot.set_state(message.from_user.id, RegisterStates.language, message.chat.id)


@bot.message_handler(state=RegisterStates.language)
def handle_language_input(message):
    insert_into_db(message.from_user.id, message.text)
    bot.set_state(message.chat.id, RegisterStates.menu)


@bot.message_handler(state=RegisterStates.menu)
def menu(message):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(
        get_message(message.from_user.id, "btn_ad"), callback_data="report_ad"
    )
    btn2 = types.InlineKeyboardButton(
        get_message(message.from_user.id, "btn_manu"), callback_data="report_deliver"
    )

    markup.add(btn1, btn2)
    bot.send_message(
        message.chat.id,
        get_message(message.from_user.id, "welcome"),
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data == "report_ad")
def report_ad(call):
    bot.set_state(call.from_user.id, AdStates.photo, call.message.chat.id)
    bot.send_message(
        call.message.chat.id, get_message(call.message.chat.id, "text_ad_photo")
    )


@bot.message_handler(state=AdStates.photo, content_types=["photo"])
def handle_receive_name(message):
    photo_id = message.photo[-1].file_id
    file_info = bot.get_file(photo_id)
    photo_url = (
        f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info.file_path}"
    )
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["photo_url"] = photo_url
        data["type"] = "ad"

    bot.set_state(message.from_user.id, AdStates.geolocation, message.chat.id)


@bot.message_handler(state=AdStates.geolocation)
def handle_geolocation_choice(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    location_button = types.KeyboardButton(
        get_message(message.from_user.id, "btn_geo_my"), request_location=True
    )
    point_button = types.KeyboardButton(
        get_message(message.from_user.id, "btn_geo_other")
    )
    markup.add(location_button, point_button)

    bot.set_state(message.chat.id, AdStates.receive)
    bot.send_message(
        message.chat.id,
        get_message(message.from_user.id, "text_geo"),
        reply_markup=markup,
    )


@bot.message_handler(state=ReportStates.add_info, content_types=["location"])
def handle_location(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        longitute, latitude = message.text
        data["longitute"] = longitute
        data["latitude"] = latitude

    bot.set_state(message.chat.id, AdStates.add_info)
    bot.send_message(
        message.chat.id,
        get_message(message.from_user.id, "text_add_info"),
        reply_markup=markup,
    )


@bot.message_handler(state=ReportStates.add_info)
def handle_receive_name(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["age"] = message.text
    bot.set_state(message.from_user.id, ReportStates.character, message.chat.id)
    bot.send_message(message.chat.id, "Какие черты характера у получателя?")


@bot.message_handler(state=ReportStates.character)
def handle_receive_name(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["character"] = message.text
    bot.set_state(message.from_user.id, ReportStates.ganre, message.chat.id)
    bot.send_message(message.chat.id, "Какой жанр книги вы хотите увидеть?")


@bot.message_handler(state=ReportStates.ganre)
def handle_receive_name(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["ganre"] = message.text
    bot.set_state(message.from_user.id, ReportStates.main_action, message.chat.id)
    bot.send_message(
        message.chat.id, "Вокруг чего должен быть построен сюжет/основное действие?"
    )


@bot.message_handler(state=ReportStates.main_action)
def handle_receive_name(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["main_action"] = message.text
    bot.set_state(message.from_user.id, ReportStates.dream, message.chat.id)
    bot.send_message(
        message.chat.id,
        "Какая заветная мечта у получателя книги? (Кем хочет стать, где оказаться, абсолютно всё можно реализовать в книге!)",
    )


@bot.message_handler(state=ReportStates.dream)
def handle_receive_name(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["dream"] = message.text
    bot.set_state(message.from_user.id, ReportStates.interest, message.chat.id)
    bot.send_message(message.chat.id, "Увлечения получателя книги?")


@bot.message_handler(state=ReportStates.interest)
def handle_receive_name(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["interest"] = message.text
    bot.set_state(message.from_user.id, ReportStates.fav_person, message.chat.id)
    bot.send_message(message.chat.id, "Любимый персонаж, герой получателя книги?")


@bot.message_handler(state=ReportStates.fav_person)
def handle_receive_name(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["fav_person"] = message.text
    bot.set_state(message.from_user.id, ReportStates.how_person, message.chat.id)
    bot.send_message(message.chat.id, "Кем вы хотели бы видеть своего героя?")


@bot.message_handler(state=ReportStates.how_person)
def handle_receive_name(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["how_person"] = message.text
    bot.set_state(message.from_user.id, ReportStates.world, message.chat.id)
    bot.send_message(message.chat.id, "Где вы хотите видеть героя? (Мир книги)")


@bot.message_handler(state=ReportStates.world)
def handle_receive_name(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["world"] = message.text
    bot.set_state(message.from_user.id, ReportStates.fav_product, message.chat.id)
    bot.send_message(
        message.chat.id,
        "Любимое произведение получателя (фильмы, сериалы, аниме, мультики, книги, комиксы...)?",
    )


@bot.message_handler(state=ReportStates.fav_product)
def handle_receive_name(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["fav_product"] = message.text
    bot.set_state(message.from_user.id, ReportStates.atmosphere, message.chat.id)
    bot.send_message(
        message.chat.id,
        "Какая атмосфера в книге должна быть(грустная, веселая, мистическая...)?",
    )


@bot.message_handler(state=ReportStates.atmosphere)
def handle_receive_name(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["atmosphere"] = message.text
    bot.set_state(message.from_user.id, ReportStates.actions, message.chat.id)
    bot.send_message(message.chat.id, "Какое развитие действий вы хотите увидеть?")


@bot.message_handler(state=ReportStates.actions)
def handle_receive_name(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["actions"] = message.text
    bot.set_state(message.from_user.id, ReportStates.ending, message.chat.id)
    bot.send_message(message.chat.id, "Какую концовку вы хотели бы увидеть?")


@bot.message_handler(state=ReportStates.add_data)
def handle_add_data(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["add_data"] = message.text
        response = insert_request_data(message.from_user.id, data)
        bot.send_message(message.chat.id, response)
        bot.send_message(message.chat.id, "Мы создаем историю, ожидайте")
        openai(data)
    bot.delete_state(message.from_user.id, message.chat.id)


# Information command
@bot.message_handler(commands=["info"])
def show_info(message):
    bot.send_message(
        message.chat.id,
        "Это – бот SoulScript, благодаря которому Вы можете погрузиться в свою мечту и воссоздать именно тот мир, который вы хотите!",
    )


# Error handlers
@bot.message_handler(state=ReportStates.age, is_digit=False)
def age_incorrect(message):
    bot.send_message(message.chat.id, "Вы ввели не число. Введите возраст в виде числа")


@bot.message_handler(
    state=ReportStates.photo, func=lambda message: "photo" not in message.content_type
)
def photo_incorrect(message):
    bot.send_message(message.chat.id, "Отправьте фото")


bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.add_custom_filter(custom_filters.IsDigitFilter())

bot.infinity_polling(skip_pending=True)