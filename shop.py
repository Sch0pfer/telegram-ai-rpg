SHOP_ITEMS = {
    "space": {
        "бластер": {"price": 50, "desc": "+10 к атаке"},
        "аптечка": {"price": 30, "desc": "Восстанавливает 50 HP"},
        "щит": {"price": 80, "desc": "+20 к защите"},
    },
    "fantasy": {
        "меч": {"price": 50, "desc": "+10 к атаке"},
        "зелье": {"price": 30, "desc": "Восстанавливает 50 HP"},
        "щит": {"price": 80, "desc": "+20 к защите"},
    },
    "zombie": {
        "дробовик": {"price": 50, "desc": "+10 к атаке"},
        "бинты": {"price": 30, "desc": "Восстанавливает 50 HP"},
        "броня": {"price": 80, "desc": "+20 к защите"},
    },
    "noir": {
        "револьвер": {"price": 50, "desc": "+10 к атаке"},
        "виски": {"price": 30, "desc": "Восстанавливает 50 HP"},
        "плащ": {"price": 80, "desc": "+20 к защите"},
    }
}

def get_menu(world_type):
    items = SHOP_ITEMS.get(world_type, SHOP_ITEMS["fantasy"])
    
    text = "🏪 *МАГАЗИН*\n\n"
    for name, info in items.items():
        text += f"• {name.capitalize()} — {info['price']} 💰\n"
        text += f"  _{info['desc']}_\n\n"
    
    text += "Напиши: `купить [предмет]`"
    return text
    
def get_price(item_name, world_type):
    def check_item(item, items):
        if item.strip().lower() in items:
            return True
        else:
            return False
    
    items = SHOP_ITEMS.get(world_type, SHOP_ITEMS["fantasy"])
    
    if check_item(item=item_name, items=items):
        price = items[item_name]["price"]
        return price
    
    return None