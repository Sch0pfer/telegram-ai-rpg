import db

import telebot
from google import genai
from google.genai import types

# === НАСТРОЙКИ И КЛЮЧИ ===
TOKEN: str = "XXX"
API_KEY: str = "XXX"

bot = telebot.TeleBot(token=TOKEN)
db.init_db()
client = genai.Client(api_key=API_KEY)

games = {}               # Тут храним активные игры: {user_id: chat_object}
waiting_for_setting = {} # Тут храним тех, кто выбирает меню: {user_id: True}

# === СЛОВАРЬ СЕТТИНГОВ (МИРОВ) ===
SETTINGS = {
    "1": {
        "name": "🚀 Космос",
        "prompt": """Ты - бортовой компьютер космического корабля в беде.
                     Стиль: технический, тревожный.
                     Используй термины: разгерметизация, модуль, сектор, кислород."""
    },
    "2": {
        "name": "🏰 Фэнтези",
        "prompt": """Ты - мастер подземелий в мире мечей и магии.
                     Стиль: эпический, загадочный, старинный.
                     Используй термины: заклинание, гильдия, древний, мана, клинок."""
    },
    "3": {
        "name": "🧟 Зомби-апокалипсис",
        "prompt": """Ты - рация выжившего в мире после эпидемии.
                     Стиль: напряжённый, отчаянный, грубый.
                     Используй термины: укрытие, припасы, орда, зараженные, патроны."""
    },
    "4": {
        "name": "🕵️ Нуар-Детектив",
        "prompt": """Ты - ведущий текстового квеста в стиле Нуар-детектива 1940-х годов.
                     Стиль: мрачный, циничный, дождливый город, джаз.
                     Используй термины: улика, револьвер, роковая женщина, инспектор."""
    }
}

# === ФУНКЦИЯ СОЗДАНИЯ ИГРЫ ===
def create_game(setting_key):
    setting = SETTINGS[setting_key] # Достаем настройки по номеру (ключу)
    
    # Собираем полный промпт из кусочков
    full_prompt = f"""{setting['prompt']}
    
    ВАЖНЫЕ ПРАВИЛА:
    - Описывай ситуацию кратко (2-3 предложения).
    - Всегда давай 2-3 варианта действий в конце.
    - Используй эмодзи для атмосферы.
    
    ФОРМАТ ОТВЕТА СТРОГО ТАКОЙ:
    [Текст описания ситуации...]
    
    Варианты:
    1. ...
    2. ...
    
    🎒 Инвентарь: [список]
    ❤️ Здоровье: 100%
    """
    
    # Создаем чат с нейросетью
    return client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(system_instruction=full_prompt)
    )

# === КОМАНДА /START ===
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id
    username = message.from_user.username

    db.add_user(user_id=user_id, username=username)

    # Генерируем текст меню автоматически из нашего словаря
    menu_text = "⚔️ *ВЫБЕРИ СВОЙ МИР* ⚔️\n\n"
    for key, value in SETTINGS.items():
        menu_text += f"{key} — {value['name']}\n"
    
    menu_text += "\nОтправь цифру номера:"
    
    bot.send_message(user_id, menu_text, parse_mode="Markdown")
    waiting_for_setting[user_id] = True # Ставим метку, что игрок в меню

# === КОМАНДА /RESET ===
@bot.message_handler(commands=["reset"])
def reset(message):
    user_id = message.chat.id
    
    # Удаляем игрока отовсюду
    if user_id in games:
        del games[user_id]
    if user_id in waiting_for_setting:
        del waiting_for_setting[user_id]
        
    bot.send_message(user_id, "💥 Мир уничтожен. Напиши /start для выбора нового.")

@bot.message_handler(commands=["profile"])
def profile(message):
    user_id = message.chat.id

    stats = db.get_stats(user_id=user_id)

    if stats:
        money = stats[0]
        xp = stats[1]
        inv = stats[2]

        text = f"""
👤 *ПРОФИЛЬ ГЕРОЯ*
━━━━━━━━━━━━━━━
💰 Золото: {money}
⭐ Опыт: {xp}
🎒 Инвентарь: {inv}
        """

        bot.send_message(user_id, text=text, parse_mode="Markdown")
    else:
        bot.send_message(user_id, "Ты еще не начал игру! Жми /start")

# === ОБРАБОТКА ВСЕХ СООБЩЕНИЙ ===
@bot.message_handler(func=lambda m: True)
def play(message):
    user_id = message.chat.id
    text = message.text.strip()
    
    # 1. ЛОГИКА ВЫБОРА МИРА (ЕСЛИ ИГРОК В МЕНЮ)
    if user_id in waiting_for_setting:
        if text in SETTINGS:
            # Игрок выбрал правильную цифру
            del waiting_for_setting[user_id] # Убираем из "ждунов"
            
            bot.send_message(user_id, f"🌍 Загрузка мира: {SETTINGS[text]['name']}...")
            bot.send_chat_action(user_id, "typing")
            
            try:
                # Создаем игру с выбранным сеттингом
                games[user_id] = create_game(text)
                response = games[user_id].send_message("Начни игру. Введи игрока в курс дела.")
                bot.send_message(user_id, response.text)
            except Exception as e:
                bot.send_message(user_id, "❌ Ошибка загрузки нейросети. Попробуй /start снова.")
                print(f"CRITICAL ERROR: {e}") # Пишем ошибку в консоль разработчика
        else:
            bot.send_message(user_id, "⚠️ Нет такого мира. Отправь цифру из меню.")
        return
    
    # 2. ЛОГИКА САМОЙ ИГРЫ
    if user_id not in games:
        bot.send_message(user_id, "Напиши /start чтобы начать игру")
        return
    
    # Идет игра
    bot.send_chat_action(user_id, "typing")
    
    try:
        response = games[user_id].send_message(text)
        bot.send_message(user_id, response.text)
        db.add_xp(user_id, 1)
        db.add_money(user_id, 1)
    except Exception as e:
        bot.send_message(user_id, "⚠️ Помехи связи (ошибка API). Повтори действие.")
        print(f"GAME ERROR: {e}")

# === ЗАПУСК ===
if __name__ == "__main__":
    print("🎮 Бот с мульти-вселенной запущен!")
    bot.infinity_polling()