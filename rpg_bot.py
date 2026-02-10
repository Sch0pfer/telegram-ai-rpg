import telebot
import os
from dotenv import load_dotenv

from config import Config
import db
import shop
from game_session import GameSession

load_dotenv()

# === НАСТРОЙКИ И КЛЮЧИ ===
TOKEN: str = Config.BOT_TOKEN
API_KEY: str = Config.GOOGLE_API_KEY

bot = telebot.TeleBot(token=TOKEN)
db.init_db()

sessions = {} 

def get_main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    start_button = telebot.types.KeyboardButton("🎲 Начало / Сюжет")
    profile_button = telebot.types.KeyboardButton("👤 Профиль")
    inventory_button = telebot.types.KeyboardButton("🎒 Инвентарь")
    shop_button = telebot.types.KeyboardButton("🏪 Магазин")

    markup.add(start_button, profile_button, inventory_button, shop_button)

    return markup

def get_admin_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    add_money_button = telebot.types.KeyboardButton("💰 +1000 монет")
    check_players_stats_button = telebot.types.KeyboardButton("👀 Узнать статистику")

    markup.add(add_money_button, check_players_stats_button)

    return markup

def text_handler(message, id_user):
    """
    Возвращает True, если была нажата кнопка меню.
    Возвращает False, если это просто текст (ход игры).
    """
    user_text = message.text
    id = id_user

    if user_text == "🎲 Начало / Сюжет":
        start(message)
        return True
    elif user_text == "🎒 Инвентарь":
        show_inventory(message)
        return True
    elif user_text == "👤 Профиль":
        profile(message)
        return True
    elif user_text == "🏪 Магазин":
        show_shop(message)
        return True
    elif user_text == "💰 +1000 монет":
        db.add_money(user_id=id, money_amount=1000)
    elif user_text == "👀 Узнать статистику":
        players_amount = db.players_stats()
        bot.send_message(id, f"Количество игроков: {players_amount}.", reply_markup=get_admin_menu())

    return False


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.message.chat.id
    
    if call.data.startswith("купить "):
        # Вытаскиваем название: "купить меч" -> "меч"
        item_name = call.data.split(" ", 1)[1]
        
        # Вызываем универсальную функцию
        perform_buy(user_id, item_name, user_id)
        
        # Обязательно отвечаем телеграму, чтобы убрались "часики" на кнопке
        bot.answer_callback_query(call.id)

# === START: Создаем сессию ===
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id
    username = message.from_user.username
    
    db.add_user(user_id, username)
    
    # СОЗДАЕМ ОБЪЕКТ СЕССИИ
    sessions[user_id] = GameSession(user_id)
    
    bot.send_message(user_id, "⚔️ Выбери мир:\n1. Космос\n2. Фэнтези\n3. Зомби\n4. Нуар", reply_markup=get_main_menu())

# === RESET ===
@bot.message_handler(commands=["reset"])
def reset(message):
    user_id = message.chat.id
    if user_id in sessions:
        del sessions[user_id] # Просто удаляем объект сессии
    bot.send_message(user_id, "Мир сброшен. Жми /start", reply_markup=get_main_menu())

@bot.message_handler(commands=["profile"])
def profile(message):
    user_id = message.chat.id

    stats = db.get_stats(user_id=user_id)

    if user_id not in sessions:
        bot.send_message(user_id, "Ты еще не начал игру! Жми /start", reply_markup=get_main_menu())
        return

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

        bot.send_message(user_id, text=text, parse_mode="Markdown", reply_markup=get_main_menu())

@bot.message_handler(commands=["inventory"])
def show_inventory(message):
    user_id = message.chat.id
    
    if user_id not in sessions:
        bot.send_message(user_id, "Сначала начни игру!", reply_markup=get_main_menu())
        return

    stats = db.get_stats(user_id=user_id)
    if stats:
        inventory = stats[3]
        bot.send_message(user_id, f"🎒 Инвентарь: {inventory}", parse_mode="Markdown", reply_markup=get_main_menu())


@bot.message_handler(commands=["shop"])
def show_shop(message):
    user_id = message.chat.id

    if user_id not in sessions:
        bot.send_message(user_id, "Сначала /start", reply_markup=get_main_menu())
        return
    
    session = sessions[user_id]

    if not session.is_active:
        bot.send_message(user_id, "Сначала выбери мир!", reply_markup=get_main_menu())
        return

    world_type = session.world_type
    bot.send_message(user_id, shop.get_menu(world_type), reply_markup=get_main_menu())

    markup = telebot.types.InlineKeyboardMarkup()

    buy_potion_btn = telebot.types.InlineKeyboardButton(text="Купить зелье (30g)", callback_data="купить зелье")
    buy_sword_btn = telebot.types.InlineKeyboardButton(text="Купить меч (50g)", callback_data="купить меч")

    markup.add(buy_potion_btn, buy_sword_btn)

    bot.send_message(user_id, "Или используйте предложенные варианты", reply_markup=markup)

def perform_buy(user_id, item_name, chat_id):
    """
    Универсальная функция покупки.
    """
    stats = db.get_stats(user_id=user_id)
    if not stats:
        bot.send_message(chat_id, "Сначала /start", reply_markup=get_main_menu())
        return

    session = sessions[user_id]

    if not session.is_active:
        bot.send_message(chat_id, "Мир не выбран. Напиши /reset", reply_markup=get_main_menu())
        return

    user_money = stats[1]

    world_type = session.world_type
    price = shop.get_price(item_name, world_type)

    if price is None:
        bot.send_message(chat_id, f"Товара '{item_name}' нет в наличии.", reply_markup=get_main_menu())
        return
    
    if user_money < price:
        bot.send_message(chat_id, f"Не хватает монет! Нужно {price}, у тебя {user_money}.", reply_markup=get_main_menu())
        return
    
    # Покупка
    db.update_inventory(user_id=user_id, new_item=item_name)
    db.spend_money(user_id=user_id, amount=price)
    bot.send_message(chat_id, f"✅ Куплено: {item_name.capitalize()}!", reply_markup=get_main_menu())

@bot.message_handler(func=lambda m: m.text.lower().startswith("купить"))
def handle_buy(message):
    user_id = message.chat.id
    
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        bot.send_message(user_id, "Что купить? Пример: купить меч", reply_markup=get_main_menu())
        return
    
    item_name = parts[1].strip()
    
    # Вызываем универсальную функцию
    perform_buy(user_id, item_name, message.chat.id)

@bot.message_handler(commands=["admin"])
def admin(message):
    user_id = message.chat.id

    if user_id != Config.ADMIN_ID:
        bot.send_message("У тебя нет власти здесь!")
        return
    
    bot.send_message(user_id, "Приветствую, создатель.", reply_markup=get_admin_menu())

# === ГЛАВНЫЙ ЦИКЛ ИГРЫ (PLAY) ===
@bot.message_handler(func=lambda m: True)
def play(message):
    user_id = message.chat.id
    
    if text_handler(message, user_id):
        return

    # 1. Проверяем, есть ли сессия
    if user_id not in sessions:
        bot.send_message(user_id, "Напиши /start", reply_markup=get_main_menu())
        return

    session = sessions[user_id] # Получаем объект игрока

    # 2. Если игра еще НЕ началась (игрок выбирает мир)
    if not session.is_active:
        user_choice = message.text.strip()
        
        # Пытаемся запустить игру через метод класса
        intro_text = session.start_game(user_choice)
        
        if intro_text:
            bot.send_message(user_id, f"🌍 Мир загружен!\n\n{intro_text}", reply_markup=get_main_menu())
        else:
            bot.send_message(user_id, "⚠️ Неверный выбор. Отправь цифру 1-4.", reply_markup=get_main_menu())
        return

    # 3. Если игра идет - делаем ход
    bot.send_chat_action(user_id, "typing")
    try:
        # Вся магия теперь внутри make_move
        answer = session.make_move(message.text)
        bot.send_message(user_id, answer, reply_markup=get_main_menu())
        
        # Проверка на смерть
        stats = db.get_stats(user_id)
        if stats and stats[0] <= 0: # HP <= 0
            del sessions[user_id]
            db.clean_stats(user_id)
            bot.send_message(user_id, "☠️ ТЫ ПОГИБ. /start", reply_markup=get_main_menu())
            
    except Exception as e:
        print(f"Error: {e}")
        bot.send_message(user_id, "Ошибка нейросети. Попробуй еще раз.")

# === ЗАПУСК ===
if __name__ == "__main__":
    print("🎮 Бот с мульти-вселенной запущен!")
    bot.infinity_polling()