import logging
import sqlite3
from config import OPEN_AI_TOKEN
from io import BytesIO
from openai import OpenAI

client = OpenAI(api_key=OPEN_AI_TOKEN)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def create_db():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            language TEXT
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT, 
            longitude FLOAT,
            latitude FLOAT,
            photo_url TEXT,
            add_info TEXT,
            FOREIGN KEY(user_id) REFERENCES users(telegram_id)
        )
    """
    )
    conn.commit()
    conn.close()


def generate_dalle_image(prompt):
    try:
        response = openai.Image.create(
            model="image-alpha-001", prompt=prompt, n=1, size="1024x1024"
        )
        return response.data[0].url
    except Exception as e:
        print(f"Произошла ошибка при генерации изображения: {e}")
        return None


def openai(url):
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "",
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
        columns = ["telegram_id", "language"]
        return dict(zip(columns, row))
    return None


def update_user_data(telegram_id, **kwargs):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    fields = ", ".join([f"{key} = ?" for key in kwargs])
    values = list(kwargs.values())
    values.append(telegram_id)

    sql = f"UPDATE users SET {fields} WHERE telegram_id = ?;"
    cursor.execute(sql, values)

    conn.commit()
    conn.close()


def insert_into_db(telegram_id, language):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    if cursor.fetchone() is not None:
        return

    cursor.execute(
        "INSERT INTO users (telegram_id, language) VALUES (?, ?)",
        (telegram_id, language),
    )
    conn.commit()
    conn.close()


def insert_report_data(telegram_id, request_data):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT telegram_id FROM users WHERE telegram_id = ?", (telegram_id,)
    )
    user_id = cursor.fetchone()

    if user_id is None:
        conn.close()
        return "Пользователь не найден"

    request_values = (
        user_id[0],
        request_data.get("type"),
        request_data.get("longitude"),
        request_data.get("latitude"),
        request_data.get("photo_url"),
        request_data.get("add_info"),
    )

    cursor.execute(
        """
        INSERT INTO requests (
            user_id, type, longitude, latitude, photo_url, add_info
        ) VALUES (?, ?, ?, ?, ?, ?)
    """,
        request_values,
    )

    conn.commit()
    conn.close()
    return "Спасибо, что помогаете стране!"
