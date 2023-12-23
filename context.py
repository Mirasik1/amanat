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