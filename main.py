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
from geopy.distance import geodesic
import random
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


@bot.callback_query_handler(
    func=lambda call: call.data in ["ru", "kz"], state=Allstates.language
)
def callback_inline(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Выберите язык👇🏻 / Тілді таңдаңыз👇🏻",
        reply_markup=None,
    )
    language = 0 if call.data == "ru" else 1
    if func.get_language_by_telegram_id(call.from_user.id) == None:
        func.insert_user(call.from_user.id, language)
    else:
        func.change_language_by_telegram_id(call.from_user.id, language)
    menu(call)


def menu(call):
    language = func.get_language_by_telegram_id(call.from_user.id)
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(msg["btn_ad"][language], callback_data="ad")
    btn2 = types.InlineKeyboardButton(msg["btn_manu"][language], callback_data="manu")

    markup.add(btn1, btn2)
    bot.send_message(
        call.message.chat.id,
        msg["text_welcome"][language],
        reply_markup=markup,
    )
    bot.set_state(call.from_user.id, Allstates.menu, call.message.chat.id)


@bot.callback_query_handler(
    func=lambda call: call.data in ["ad", "manu"], state=Allstates.menu
)
def report(call):
    language = func.get_language_by_telegram_id(call.from_user.id)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=msg["text_welcome"][language],
        reply_markup=None,
    )
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data["report_type"] = call.data
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_skip = types.KeyboardButton(msg["skip"][language])
    markup.add(btn_skip)
    bot.set_state(call.from_user.id, Allstates.photo, call.message.chat.id)
    bot.send_message(
        call.message.chat.id, msg["text_photo"][language], reply_markup=markup
    )

@bot.message_handler(content_types=["photo"],state=Allstates.photo)
def photo_message(message):
    language=func.get_language_by_telegram_id(message.from_user.id)
    print("Message id :", message.from_user.id)
    photo_id = message.photo[-1].file_id
    file_info = bot.get_file(photo_id)
    photo_url = (
        f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info.file_path}"
    )
    bot.send_message(message.chat.id, msg["loading"][language])
    response = photo_url #openai(photo_url)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["response"] = response
        data["photo_url"] = photo_url
    print(data)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_skip = types.KeyboardButton(msg["skip"][language])
    markup.add(btn_skip)
    bot.set_state(message.from_user.id, Allstates.geo, message.chat.id)
    bot.send_message(message.chat.id, msg["text_geo"][language], reply_markup=markup)


@bot.message_handler(content_types=["location"], state=Allstates.geo)
def handle_location(message):
    language = func.get_language_by_telegram_id(message.from_user.id)

    longitude = message.location.longitude
    latitude = message.location.latitude

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["longitude"] = longitude
        data["latitude"] = latitude

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_no = types.KeyboardButton(msg["no"][language])
    markup.add(btn_no)

    bot.send_message(
        message.chat.id, msg["text_add_info"][language], reply_markup=markup
    )
    bot.set_state(message.from_user.id, Allstates.additional_info, message.chat.id)


@bot.message_handler(content_types=["text"], state=Allstates.additional_info)
def send(message):
    language = func.get_language_by_telegram_id(message.from_user.id)
    markup_remove = types.ReplyKeyboardRemove()

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["ad_info"] = message.text

    bot.send_message(message.chat.id, msg["report_end"][language])
    bot.set_state(message.from_user.id, Allstates.send, message.chat.id)

    bot.send_message(admin_id, str(data))


@bot.message_handler(state="*", commands=["cancel"])
def any_state(message):
    language = func.get_language_by_telegram_id(message.from_user.id)
    bot.send_message(message.chat.id, msg["text_cancel"][language])
    bot.delete_state(message.from_user.id, message.chat.id)


def get_color_for_radius(radius):
    if radius >= 5000:
        return "red"
    else:
        green_to_red = 255 * (radius - 10) / (5000 - 10)
        return f"#{int(green_to_red):02x}00{255-int(green_to_red):02x}"


@bot.message_handler(commands=["map"])
def show_map(message):
    center_latitude = 51.1694
    center_longitude = 71.4491
    m = folium.Map(location=[center_latitude, center_longitude], zoom_start=12)

    data = func.get_all_reports()

    circle_centers = []
    print(len(data))
    for report in data:
        _, _, report_type, _, _, _, longitude, latitude, _ = report
        circle_centers.append(((latitude, longitude), 50, {report_type}))

    def merge_circles(circle_centers, max_iterations=10):
        iteration = 0
        while iteration < max_iterations:
            merged_circles = []
            skip_indices = set()

            for i, base_circle in enumerate(circle_centers):
                if i in skip_indices:
                    continue
                base_center, base_radius, base_types = base_circle
                merged = False

                for j, compare_circle in enumerate(circle_centers):
                    if i != j and j not in skip_indices:
                        compare_center, compare_radius, compare_types = compare_circle
                        distance = geodesic(base_center, compare_center).meters

                        # Если круги пересекаются
                        if distance <= base_radius + compare_radius:
                            # Находим центр между двумя кругами
                            new_center = ((base_center[0] + compare_center[0]) / 2,
                                          (base_center[1] + compare_center[1]) / 2)
                            # Новый радиус будет средним увеличенным на небольшой коэффициент
                            new_radius = (base_radius + compare_radius) / 2 * 1.05
                            # Объединяем типы преступлений
                            new_types = base_types.union(compare_types)
                            merged_circles.append((new_center, new_radius, new_types))
                            skip_indices.add(i)
                            skip_indices.add(j)
                            merged = True
                            break

                if not merged and i not in skip_indices:
                    merged_circles.append(base_circle)

            # Если не было слияний в этой итерации, выходим из цикла
            if len(merged_circles) == len(circle_centers):
                break
            else:
                # Переходим к следующей итерации с новым списком кругов
                circle_centers = merged_circles
                iteration += 1

        return merged_circles

    merged_circles = merge_circles(circle_centers)

    for center, radius, types in merged_circles:
        color = get_color_for_radius(radius)
        text = f"Виды преступлений: {', '.join(types)} \n Количество преступлений: {len(types)}"
        folium.Circle(
            location=[center[0], center[1]],
            radius=radius,
            popup=text,
            color=color,
            fill=True,
            fill_color=color,
        ).add_to(m)
    m.save("index_merged.html")

def get_color_for_radius(radius):
    if radius < 100:
        return "green"
    elif radius < 200:
        return "yellow"
    else:
        return "red"



@bot.message_handler(
    func=lambda message: message.text in ["Пропустить", "Өткізіп жіберу"],
    state=Allstates.photo,
)
def skip_photo(message):
    language = func.get_language_by_telegram_id(message.from_user.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["response"] = None
        data["photo_url"] = None

    bot.send_message(message.chat.id, msg["text_geo"][0])
    bot.set_state(message.from_user.id, Allstates.geo, message.chat.id)


@bot.message_handler(
    func=lambda message: message.text in ["Пропустить", "Өткізіп жіберу"],
    state=Allstates.geo,
)
def skip_geo(message):
    language = func.get_language_by_telegram_id(message.from_user.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["longitude"] = None
        data["latitude"] = None

    bot.send_message(message.chat.id, msg["text_add_info"][language])
    bot.set_state(message.from_user.id, Allstates.additional_info, message.chat.id)


@bot.message_handler(commands=["list"])
def send_admin(message):

    if message.chat.id == admin_id:
        admin_text = func.get_all_reports()
        bot.send_message(admin_id, admin_text)
    else:
        pass


@bot.message_handler(commands=["excel"])
def send_excel(message):
    func.create_excel("reports")
    file_path = "./reports.xlsx"
    with open(file_path, "rb") as file:
        bot.send_document(message.chat.id, document=file)


def generate_reports():
    for _ in range(100):
        func.add_report(
            {
                "report_type": "type" + str(random.randint(1, 5)),
                "ad_info": "ad_info",
                "response": "response",
                "photo_url": "url",
                "longitude": 71.4491 + random.uniform(-0.01, 0.01),
                "latitude": 51.1694 + random.uniform(-0.01, 0.01),
                "ad_info_text": "ad_info_text",
            }
        )

    for _ in range(50):
        func.add_report(
            {
                "report_type": "type" + str(random.randint(1, 5)),
                "ad_info": "ad_info",
                "response": "response",
                "photo_url": "url",
                "longitude": 71.4083 + random.uniform(-0.005, 0.005),
                "latitude": 51.0880 + random.uniform(-0.005, 0.005),
                "ad_info_text": "ad_info_text",
            }
        )


# generate_reports()

bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling(skip_pending=True)
