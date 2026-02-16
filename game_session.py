from google import genai
from google.genai import types
import re
from config import Config
from npc import Goga
import image_gen
import db

# === КВЕСТОВЫЕ ЛИНИИ (FSM) ===
# Для каждого мира прописываем этапы.
# prompt: Скрытая инструкция для AI.
# target: Что видит игрок в профиле.
ADVENTURES = {
    "fantasy": {
        0: {
            "target": "Найти Древний Амулет",
            "prompt": "Игрок должен найти 'Древний Амулет'. Не пускай его в Храм и к боссу, пока он не найдет этот предмет. Намекай, что амулет спрятан в лесу или у торговца."
        },
        1: {
            "target": "Проникнуть в Храм",
            "prompt": "У игрока есть Амулет. Теперь направляй его к Заброшенному Храму. Опиши его величие и закрытые врата, которые открываются Амулетом."
        },
        2: {
            "target": "Убить Стража Храма",
            "prompt": "Игрок в Храме. Появился Страж Храма (Босс). Начинай битву. Страж очень силен."
        },
        3: {
            "target": "Герой Фэнтези (Квест завершен)",
            "prompt": "Страж повержен. Поздравь игрока с победой и предложи исследовать мир свободно."
        }
    },
    # Заглушки для других миров, чтобы не крашилось
    "space": {0: {"target": "Выжить", "prompt": "Выживай."}},
    "zombie": {0: {"target": "Выжить", "prompt": "Выживай."}},
    "noir": {0: {"target": "Выжить", "prompt": "Выживай."}},
}

SETTINGS = {
    "1": {"name": "🚀 Космос", "prompt": "Ты - бортовой компьютер..."},
    "2": {"name": "🏰 Фэнтези", "prompt": "Ты - мастер подземелий..."},
    "3": {"name": "🧟 Зомби", "prompt": "Ты - рация выжившего..."},
    "4": {"name": "🕵️ Нуар", "prompt": "Ты - ведущий детектива..."}
}

WORLD_CODES = {"1": "space", "2": "fantasy", "3": "zombie", "4": "noir"}

class GameSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.client = genai.Client(api_key=Config.GOOGLE_API_KEY)
        self.chat = None
        self.world_type = None
        self.is_active = False
        self.goga = Goga()

    def start_game(self, setting_key):
        if setting_key not in SETTINGS: return None
        
        self.world_type = WORLD_CODES[setting_key]
        setting = SETTINGS[setting_key]
        
        # Сброс квеста при старте
        db.update_quest_stage(self.user_id, 0, "Начало пути")

        full_prompt = f"""{setting['prompt']}
        ВАЖНО: Если здоровье меняется, пиши [HP: +число] или [HP: -число].
        ВАЖНО: Всегда добавляй описание локации для генерации картинки в теге [IMG: описание].
        """
        
        self.chat = self.client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=full_prompt)
        )
        self.is_active = True
        
        response = self.chat.send_message("Начни игру. Введи в курс дела.")
        return self._parse_response(response.text)

    def make_move(self, user_text):
        if not self.chat: return ["Ошибка сессии", ""]

        stats = db.get_stats(self.user_id) # (hp, money, xp, inv, quest_stage)
        if not stats: return ["Ошибка БД", ""]
        
        hp, money, xp, inv, stage = stats
        
        # === 1. FSM: ПОДМЕС ГЕЙМПЛЕЯ В ПРОМПТ ===
        context = f"[Инфо: HP {hp}, Inv: {inv}]. Игрок: {user_text}"
        
        # Берем данные текущего этапа
        quests = ADVENTURES.get(self.world_type, {})
        current_quest = quests.get(stage)
        
        if current_quest:
            context += f"\n[СЮЖЕТНАЯ ИНСТРУКЦИЯ (НЕ ПОКАЗЫВАТЬ ИГРОКУ): {current_quest['prompt']}]"

        # === 2. ОТПРАВКА ===
        response = self.chat.send_message(context)
        ai_text = response.text

        # === 3. FSM: ПРОВЕРКА УСЛОВИЙ ПЕРЕХОДА ===
        new_stage = stage
        
        # ЛОГИКА ДЛЯ ФЭНТЕЗИ (Hardcoded Logic)
        if self.world_type == "fantasy":
            # Переход 0 -> 1 (Нашел амулет)
            if stage == 0 and ("амулет" in inv.lower() or "amulet" in inv.lower()):
                new_stage = 1
                
            # Переход 1 -> 2 (Попал в храм)
            elif stage == 1 and ("храм" in ai_text.lower() or "temple" in ai_text.lower()):
                new_stage = 2
                
            # Переход 2 -> 3 (Победил стража)
            elif stage == 2 and ("победа" in ai_text.lower() or "сразил" in ai_text.lower()):
                new_stage = 3

        # Если этап изменился - пишем в базу
        if new_stage != stage:
            next_target = quests.get(new_stage, {}).get("target", "Конец")
            db.update_quest_stage(self.user_id, new_stage, next_target)
            ai_text += f"\n\n🎉 **КВЕСТ ОБНОВЛЕН:** {next_target}"

        # === 4. ПАРСИНГ HP и IMG ===
        final_text, img_url = self._parse_response(ai_text) # Вынес парсинг в метод
        
        # Награды
        db.add_xp(self.user_id, 10)
        db.add_money(self.user_id, 5)
        
        return [final_text, img_url]

    def _parse_response(self, text):
        """Парсит теги [HP] и [IMG], обновляет базу и возвращает чистый текст и URL"""
        clean_text = text
        
        # HP
        hp_change = 0
        for match in re.finditer(r'\[HP: ([+-]?\d+)\]', text):
            hp_change += int(match.group(1))
            clean_text = clean_text.replace(match.group(0), "")
        
        if hp_change != 0:
            db.change_hp(self.user_id, hp_change)

        # IMG
        img_url = ""
        img_match = re.search(r'\[IMG: (.+)\]', clean_text)
        if img_match:
            desc = img_match.group(1)
            clean_text = clean_text.replace(img_match.group(0), "")
            try:
                img_url = image_gen.generate_location_image(desc)
            except:
                pass # Если генерация упала, не крашим бота

        return [clean_text.strip(), img_url]