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
from telebot import custom_filters
state_storage=StateMemoryStorage()
create_db()
create_table()
admin_id = "894349873"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, state_storage=state_storage)
url=""
def handle_photo(message):
    photo_id = message.photo[-1].file_id
    file_info = bot.get_file(photo_id)
    photo_url = (
        f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info.file_path}"
    )
    global url
    url=photo_url
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    location_button = types.KeyboardButton("Отправить мою геолокацию", request_location=True)
    map_button = types.KeyboardButton("Выбрать точку на карте(Через меню телеграмма)")
    markup.add(location_button,map_button)
    bot.set_state(message.from_user.id,Allstates.geo,message.chat.id)
    bot.send_message(
        message.chat.id,
        "Теперь, пожалуйста, отправьте геолокацию через меню телеграма",
        reply_markup=markup
    )
class Allstates(StatesGroup):
    info=State()
    lang = State()
    geo = State()
    photo=State()
    report_ad = State()
    report_del = State()
    ad = State()
    choice=State()

@bot.message_handler(commands=["start"])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(text="Русский", callback_data="ru")
    btn2 = types.InlineKeyboardButton(text="Қазақша", callback_data="kz")
    markup.add(btn1, btn2)
    bot.send_message(
        message.chat.id, "Выберите язык👇🏻 / Тілді таңдаңыз👇🏻", reply_markup=markup
    )
    bot.set_state(message.from_user.id,Allstates.info,message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data in ["ru", "kz","report_ad","report_delivery"],state=Allstates.info)
def callback_inline(call):
    language = "Русский" if call.data == "ru" else "Қазақша"
    if call.data=="ru" or call.data=="kz":
        menu(call.message, language)
    if call.data=="report_ad" or call.data=="report_delivery":
        handle_callback_query(call)


def menu(message,language):
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
    bot.set_state(message.from_user.id, Allstates.choice, message.chat.id)


def handle_callback_query(call):

    if call.data == "report_ad":
        bot.send_message(
            call.message.chat.id, "Пожалуйста, отправьте фотографию незаконной рекламы."
        )
        bot.set_state(call.message.from_user.id,Allstates.report_ad,call.message.chat.id)
    elif call.data=="report_delivery":
        bot.send_message(
            call.message.chat.id, "Пожалуйста, отправьте фотографию о незаконном производстве(Прикрепите фото (не более двух). Не превышающее 10 МБ. Если нет, выберите Продолжить.)"
        )
        bot.set_state(call.message.from_user.id, Allstates.report_del, call.message.chat.id)
    else:
        pass

@bot.message_handler(content_types=["photo"])
def handle_report(message):
    print("Yes")
    handle_photo(message)
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


bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling(skip_pending=True)
