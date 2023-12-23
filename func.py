import logging
import sqlite3
from config import OPEN_AI_TOKEN
from io import BytesIO
from openai import OpenAI
import requests
client = OpenAI(api_key=OPEN_AI_TOKEN)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def create_db():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            state TEXT,
            language TEXT,
            photo_url TEXT,
            responses INTEGER
        )
    """)
    conn.commit()
    conn.close()

def create_table():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            state TEXT,
            language TEXT,
            photo_url TEXT,
            responses INTEGER NOT NULL
        )
    """
    )

    conn.commit()
    conn.close()

def openai(url):
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f'Ни в коем случае не используй выражения на подобии "На изображении изображено". Распознавай потенциальные методы рекламы, например: листовки, граффити, баннеры, подозрительные надписи на стенах. Типы источников: "веб-сайт", "телеграмм канал/бот", "номер телефона". Других источников не может быть. Оценивай уверенность в корректности понимания текста (Текст полностью понятен, текст частично понятен, текст полностью не понятен). При их нахождении проверь источник на тип, дай ответ на фото ВОТ ТАК, НЕ ОТХОДИ ОТ ДАННОГО ПРИМЕРА: "Потенциальный источник:  тип источника, текст источника - Текст источника, предполагаемая ссылка: СОЗДАЙ ССЫЛКУ ПО ТИПУ - https//..., степень уверенности - оценка". Если на изображении нет подозрительных объектов, напиши "На фотографии нет подозрительных объектов."',
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": url,
                        },
                    },
                ],
            }
        ],
        max_tokens=1000,
    )

    cloth_description = response.choices[0].message.content

    return cloth_description


def create_db_and_table():
    conn = sqlite3.connect('amanat.sql')
    cursor = conn.cursor()
    create_table_query = '''CREATE TABLE IF NOT EXISTS users (
                                user_id INTEGER PRIMARY KEY,
                                preferred_language TEXT
                            )'''
    cursor.execute(create_table_query)
    conn.commit()
    conn.close()


def get_user_data(telegram_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        # Конвертируем кортеж в словарь
        columns = ['telegram_id', 'state', 'language', 'photo_url', 'responses']
        return dict(zip(columns, row))
    return None


def update_user_data(telegram_id, **kwargs):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    fields = ', '.join([f"{key} = :{key}" for key in kwargs])
    sql = f"""
        INSERT INTO users (telegram_id, {', '.join(kwargs.keys())}) VALUES (:telegram_id, {', '.join(':' + key for key in kwargs)})
        ON CONFLICT(telegram_id) DO UPDATE SET {fields};
    """
    cursor.execute(sql, {'telegram_id': telegram_id, **kwargs})
    conn.commit()
    conn.close()


def insert_into_db(telegram_id, nickname, responses):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    if cursor.fetchone() is not None:
        return "Пользователь уже зарегистрирован."

    cursor.execute(
        "INSERT INTO users (telegram_id, state, language, photo_url, responses) VALUES (?, ?, ?, ?, ?)",
        (telegram_id, nickname, state, language, responses),
    )
    conn.commit()
    conn.close()
    return "Регистрация успешно завершена."


def add_photo(user_id, file_id, cell_number):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO photo_storage (user_id, file_id) VALUES (?, ?)",
        (user_id, file_id, cell_number),
    )
    conn.commit()
    conn.close()


def list_photos():
    conn = sqlite3.connect("photos.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM photo_storage")
    photos = cursor.fetchall()

    conn.close()

    photos_list = [
        "ID: {}, User ID: {}, File ID: {}, Cell Number: {}".format(*photo)
        for photo in photos
    ]
    return "\n".join(photos_list)
