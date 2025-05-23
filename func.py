import sqlite3
import pandas as pd
import random
from config import OPEN_AI_TOKEN
from io import BytesIO
from openai import OpenAI
import requests
client = OpenAI(api_key=OPEN_AI_TOKEN)


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


def get_user_data(telegram_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
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
        (telegram_id, nickname, responses),
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


def fetch_reports_data():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM reports")
        rows = cursor.fetchall()
        for row in rows:
            return row
    except Exception as e:
        return f"Произошла ошибка: {e}"
    finally:
        conn.close()


def create_excel(report_name):
    conn = sqlite3.connect("data.db")
    query = "SELECT * FROM reports"
    df = pd.read_sql_query(query, conn)
    conn.close()
    excel_path = report_name + ".xlsx"
    df.to_excel(excel_path, index=False)


def create_db():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            language INTEGER
        )
    """)
    conn.commit()
    conn.close()


def insert_user(telegram_id, language):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (telegram_id, language) VALUES (?, ?)", (telegram_id, language))

    conn.commit()
    conn.close()


def get_language_by_telegram_id(telegram_id):
    telegram_id=int(telegram_id)
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT language FROM users WHERE telegram_id = ?", (telegram_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    else:
        return None


def change_language_by_telegram_id(telegram_id, new_language):
    with sqlite3.connect("data.db") as conn:
        cursor = conn.cursor()
        try:
            if not 0 <= new_language <= 1:
                raise ValueError("Недопустимое значение для языка. Должно быть число от 0 до 9.")
            cursor.execute("UPDATE users SET language = ? WHERE telegram_id = ?", (new_language, telegram_id))
            conn.commit()

            return "Язык пользователя успешно изменен."
        except sqlite3.Error as e:
            return f"Ошибка при изменении языка пользователя: {str(e)}"
        except ValueError as ve:
            return f"Ошибка: {str(ve)}"


def create_reports_table():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            report_type TEXT,
            response TEXT,
            ad_info TEXT,
            photo_url TEXT,
            longitude REAL,
            latitude REAL,
            ad_info_text TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_response(telegram_id, report_data):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    try:
        required_fields = ['report_type','ad_info', 'response', 'photo_url', 'longitude', 'latitude','ad_info_text']
        if not all(field in report_data for field in required_fields):
            raise ValueError("Отсутствуют обязательные поля в данных о жалобе.")

        cursor.execute("""
            INSERT INTO reports (telegram_id, report_type, ad_info,response, photo_url, longitude, latitude, ad_info_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            telegram_id,
            report_data['report_type'],
            report_data['ad_info'],
            report_data['response'],
            report_data['photo_url'],
            report_data['longitude'],
            report_data['latitude'],
            report_data['ad_info_text']
        ))

        conn.commit()
        return "Данные о жалобе успешно добавлены."
    except sqlite3.Error as e:
        return f"Ошибка при добавлении данных о жалобе: {str(e)}"
    except ValueError as ve:
        return f"Ошибка: {str(ve)}"
    finally:
        conn.close()


def add_report(report_data):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reports (telegram_id, report_type, ad_info, response, photo_url, longitude, latitude, ad_info_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        894349873,
        report_data['report_type'],
        report_data['ad_info'],
        report_data['response'],
        report_data['photo_url'],
        report_data['longitude'],
        report_data['latitude'],
        None
    ))
    conn.commit()
    conn.close()


def get_all_reports():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM reports")
        rows = cursor.fetchall()
        return rows
    except sqlite3.Error as e:
        print(f"Ошибка при получении данных из таблицы reports: {str(e)}")
    finally:
        conn.close()


def generate_reports():
    for _ in range(100):
        add_report(
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
        add_report(
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

