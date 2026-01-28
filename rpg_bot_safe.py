import db
import shop

import re
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

WORLD_CODES = {
    "1": "space",
    "2": "fantasy",
    "3": "zombie",
    "4": "noir"
}
user_sessions = {}

# === ФУНКЦИЯ СОЗДАНИЯ ИГРЫ ===
def create_game(setting_key):
    setting = SETTINGS[setting_key] # Достаем настройки по номеру (ключу)
    
    # Собираем полный промпт из кусочков
    full_prompt = f"""{setting['prompt']}
    
    ВАЖНЫЕ ПРАВИЛА:
    - В начале игры инвентарь всегда пустой.
    - Описывай ситуацию кратко (2-3 предложения).
    - Всегда давай 2-3 варианта действий в конце.
    - Используй эмодзи для атмосферы.

    ВАЖНОЕ ПРАВИЛО МЕХАНИКИ:
    Если персонаж получает урон или лечится, ТЫ ОБЯЗАН добавить в конец ответа тег:
    [HP: -число] или [HP: +число]

    Примеры:
    "Ты упал в яму и сломал ногу. [HP: -15]"
    "Ты выпил зелье. Тепло разливается по телу. [HP: +20]"

    НИКОГДА не пиши этот тег, если здоровье не меняется.
    
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

    if not games[user_id]:
        bot.send_message(user_id, "Ты еще не начал игру! Жми /start")

    if stats:
        hp = stats[0]
        money = stats[1]
        xp = stats[2]
        inv = stats[3]

        text = f"""
👤 *ПРОФИЛЬ ГЕРОЯ*
━━━━━━━━━━━━━━━
❤️ Здоровье: {hp}
💰 Золото: {money}
⭐ Опыт: {xp}
🎒 Инвентарь: {inv}
        """

        bot.send_message(user_id, text=text, parse_mode="Markdown")
    else:
        bot.send_message(user_id, "Ты еще не начал игру! Жми /start")

@bot.message_handler(commands=["shop"])
def show_shop(message):
    user_id = message.chat.id

    if user_id not in games:
        bot.send_message(user_id, "Ты еще не начал игру! Жми /start")
        return
    
    if user_id not in user_sessions:
        bot.send_message(user_id, "Мир не выбран. Напиши /reset")
        return

    world_key = user_sessions[user_id] 

    world_type = WORLD_CODES[world_key]
    
    bot.send_message(user_id, shop.get_menu(world_type=world_type))

@bot.message_handler(func=lambda m: m.text.lower().startswith("купить"))
def handle_buy(message):
    user_id = message.chat.id

    stats = db.get_stats(user_id=user_id)
    if not stats:
        bot.send_message(user_id, "Сначала /start")
        return

    if user_id not in user_sessions:
        bot.send_message(user_id, "Мир не выбран. Напиши /reset")

    parts = message.text.split(" ", 1)

    if len(parts) < 2:
        bot.send_message(user_id, "Что купить? Напиши: купить меч")
        return
    
    item_name = parts[1].strip()

    user_money = stats[0]

    world_key = user_sessions[user_id]
    world_type = WORLD_CODES[world_key]
    price = shop.get_price(item_name, world_type)

    if price == None:
        bot.send_message(user_id, "Не существует такого предмета")
        return
    
    if user_money < price:
        bot.send_message(user_id, "У тебя не хватает монет")
        return
    
    db.update_inventory(user_id=user_id, new_item=item_name)
    db.spend_money(user_id=user_id, amount=price)
    bot.send_message(user_id, f"Куплено: {item_name.capitalize()}!")

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
            
            user_sessions[user_id] = text

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
        current_state = db.get_stats(user_id)
        player_hp = current_state[0]
        player_money = current_state[1]
        player_xp = current_state[2]
        player_inv = current_state[3]

        context = f"[Системная инфа: Здоровье: {player_hp}, Монеты: {player_money}, XP: {player_xp}, Инвентарь игрока: {player_inv}]. Действие игрока: {text}"

        response = games[user_id].send_message(context)

        match = re.search(r'\[HP: ([+-]\d+)\]', response.text)

        if match:
            clean_text = response.text.replace(match.group(0), "").strip()
            hp_change = int(match.group(1))
            db.change_hp(user_id=user_id, hp_amount=hp_change)
        else:
            clean_text = response.text

        bot.send_message(user_id, clean_text)

        if db.get_stats(user_id=user_id)[0] == 0:
            del(games[user_id])
            del(user_sessions[user_id])
            db.clean_stats(user_id=user_id)
            bot.send_message(user_id, "☠️ ТЫ ПОГИБ. Игра окончена. Жми /start")
            return

        db.add_xp(user_id, 5)
        db.add_money(user_id, 10)
    except Exception as e:
        bot.send_message(user_id, "⚠️ Помехи связи (ошибка API). Повтори действие.")
        print(f"GAME ERROR: {e}")

# === ЗАПУСК ===
if __name__ == "__main__":
    print("🎮 Бот с мульти-вселенной запущен!")
    bot.infinity_polling()