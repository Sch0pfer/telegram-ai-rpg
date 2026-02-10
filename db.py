import sqlite3

# Подключаемся к файлу. check_same_thread=False нужно для работы с ботом
connection = sqlite3.connect("rpg_save.db", check_same_thread=False)
cursor = connection.cursor()

# 1. Функция создания таблицы (Запускаем один раз при старте)
def init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        hp INTEGER DEFAULT 100,
        money INTEGER DEFAULT 0,
        xp INTEGER DEFAULT 0,
        inventory TEXT DEFAULT 'Пусто'
    )
    """)
    connection.commit()

# 2. Функция добавления нового игрока
def add_user(user_id, username):
    # Проверяем, есть ли он уже
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        # Если нет - добавляем
        cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        connection.commit()
        print(f"➕ Игрок {username} добавлен в базу!")
    else:
        print(f"ℹ️ Игрок {username} уже есть в базе.")

# 3. Функция получения статистики
def get_stats(user_id):
    cursor.execute("SELECT hp, money, xp, inventory FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() # Вернет (hp, money, xp, inventory)

def change_hp(user_id, hp_amount):
    cursor.execute("SELECT hp FROM users WHERE user_id = ?", (user_id,))
    hp = cursor.fetchone()[0]
    new_hp = hp + hp_amount
    if new_hp < 0:
        new_hp = 0
    elif new_hp > 100:
        new_hp = 100

    cursor.execute("UPDATE users SET hp = ? WHERE user_id = ?", (new_hp, user_id))
    connection.commit()

# 4. Функция начисления награды (за каждое сообщение)
def add_xp(user_id, xp_amount):
    cursor.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (xp_amount, user_id))
    connection.commit()

def add_money(user_id, money_amount):
    cursor.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (money_amount, user_id))
    connection.commit()

def update_inventory(user_id, new_item):
    cursor.execute("SELECT inventory FROM users WHERE user_id = ?", (user_id,))
    current = cursor.fetchone()[0]

    if current == "Пусто":
        new_inventory = new_item
    else:
        new_inventory = current + ", " + new_item

    cursor.execute("UPDATE users SET inventory = ? WHERE user_id = ?", (new_inventory, user_id))
    connection.commit()

def clean_stats(user_id):
    cursor.execute("UPDATE users SET hp = ?, inventory = ? WHERE user_id = ?", (100, "Пусто", user_id))
    connection.commit()

def spend_money(user_id, amount):
    cursor.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (amount, user_id))
    connection.commit()

def players_stats():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]