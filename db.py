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
    cursor.execute("SELECT money, xp, inventory FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() # Вернет (money, xp, inventory)

# 4. Функция начисления награды (за каждое сообщение)
def add_xp(user_id, xp_amount):
    cursor.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (xp_amount, user_id))
    connection.commit()

def add_money(user_id, money_amount):
    cursor.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (money_amount, user_id))
    connection.commit()