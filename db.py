import sqlite3

connection = sqlite3.connect("rpg_save.db", check_same_thread=False)
cursor = connection.cursor()

def init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        hp INTEGER DEFAULT 100,
        money INTEGER DEFAULT 0,
        xp INTEGER DEFAULT 0,
        inventory TEXT DEFAULT 'Пусто',
        quest_stage INTEGER DEFAULT 0,
        quest_target TEXT DEFAULT 'Начало пути'
    )
    """)
    connection.commit()

def add_user(user_id, username):
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        connection.commit()
        print(f"➕ Игрок {username} добавлен.")

def get_stats(user_id):
    # === ИЗМЕНЕНИЕ: Теперь возвращаем еще и quest_stage ===
    cursor.execute("SELECT hp, money, xp, inventory, quest_stage FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() # (hp, money, xp, inv, stage)

def change_hp(user_id, hp_amount):
    cursor.execute("SELECT hp FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if not res: return
    current_hp = res[0]
    new_hp = max(0, min(100, current_hp + hp_amount))
    cursor.execute("UPDATE users SET hp = ? WHERE user_id = ?", (new_hp, user_id))
    connection.commit()

def add_xp(user_id, xp_amount):
    cursor.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (xp_amount, user_id))
    connection.commit()

def add_money(user_id, money_amount):
    cursor.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (money_amount, user_id))
    connection.commit()

def update_inventory(user_id, new_item):
    cursor.execute("SELECT inventory FROM users WHERE user_id = ?", (user_id,))
    current = cursor.fetchone()[0]
    new_inventory = new_item if current == "Пусто" else f"{current}, {new_item}"
    cursor.execute("UPDATE users SET inventory = ? WHERE user_id = ?", (new_inventory, user_id))
    connection.commit()

def clean_stats(user_id):
    cursor.execute("UPDATE users SET hp=?, inventory=?, quest_stage=? WHERE user_id=?", (100, "Пусто", 0, user_id))
    connection.commit()

def spend_money(user_id, amount):
    cursor.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (amount, user_id))
    connection.commit()

def players_stats():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]

def update_quest_stage(user_id, stage, target_text=""):
    cursor.execute("UPDATE users SET quest_stage = ?, quest_target = ? WHERE user_id = ?", (stage, target_text, user_id))
    connection.commit()