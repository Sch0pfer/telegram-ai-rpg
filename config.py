import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    GOOGLE_API_KEY = os.getenv("GOOGLE_KEY")
    PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN")

    try:
        ADMIN_ID = int(os.getenv("ADMIN_ID"))
    except:
        ADMIN_ID = None
    
    START_MONEY = 0
    START_HP = 100

    DB_NAME = "rpg_save.db"

if not Config.BOT_TOKEN or not Config.GOOGLE_API_KEY:
    raise ValueError("❌ ОШИБКА: Не найдены ключи в .env!")