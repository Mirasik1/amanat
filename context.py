import logging
import sqlite3
from config import OPEN_AI_TOKEN
from io import BytesIO
from openai import OpenAI
import requests

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
            latitude REAL
        )
    """)
    conn.commit()
    conn.close()

def add_response(telegram_id, report_data):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    try:

        required_fields = ['report_type', 'response','ad_info', 'ad_info_text', 'photo_url', 'longitude', 'latitude']
        if not all(field in report_data for field in required_fields):
            raise ValueError("Отсутствуют обязательные поля в данных о жалобе.")


        cursor.execute("""
            INSERT INTO reports (telegram_id, report_type,response, ad_info, ad_info_text, photo_url, longitude, latitude)
            VALUES (?, ?,?, ?, ?, ?, ?, ?)
        """, (
            telegram_id,
            report_data['report_type'],
            report_data['response'],
            report_data['ad_info'],
            report_data['ad_info_text'],
            report_data['photo_url'],
            report_data['longitude'],
            report_data['latitude']
        ))

        conn.commit()
        return "Данные о жалобе успешно добавлены."
    except sqlite3.Error as e:
        return f"Ошибка при добавлении данных о жалобе: {str(e)}"
    except ValueError as ve:
        return f"Ошибка: {str(ve)}"
    finally:
        conn.close()


def get_all_reports():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM reports")
        rows = str(cursor.fetchall())

        return rows
    except sqlite3.Error as e:
        print(f"Ошибка при получении данных из таблицы reports: {str(e)}")
    finally:
        conn.close()