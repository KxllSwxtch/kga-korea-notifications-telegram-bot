import re
import time
import telebot
import os
import requests
import urllib.parse
from telebot import types
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
from dotenv import load_dotenv
from datetime import datetime
from translations import translations

COLOR_TRANSLATIONS = {
    "검정색": "Чёрный",
    "쥐색": "Тёмно-серый",
    "은색": "Серебристый",
    "은회색": "Серо-серебристый",
    "흰색": "Белый",
    "은하색": "Галактический серый",
    "명은색": "Светло-серебристый",
    "갈대색": "Коричневато-серый",
    "연금색": "Светло-золотистый",
    "청색": "Синий",
    "하늘색": "Голубой",
    "담녹색": "Тёмно-зелёный",
    "청옥색": "Бирюзовый"
}

# Загружаем переменные из .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# FSM-хранилище
state_storage = StateMemoryStorage()

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN, state_storage=state_storage)
user_search_data = {}

# FSM: Состояния формы
class CarForm(StatesGroup):
    brand = State()
    model = State()
    generation = State()
    trim = State()
    color = State()
    mileage_from = State()
    mileage_to = State()

def get_manufacturers():
    url = "https://api.encar.com/search/car/list/general?count=true&q=(And.Hidden.N._.SellType.%EC%9D%bc%EB%B0%98._.CarType.A.)&inav=%7CMetadata%7CSort"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:    
        response = requests.get(url, headers=headers)
        data = response.json()
        manufacturers = data.get("iNav", {}).get("Nodes", [])[2].get("Facets", [])[0].get("Refinements", {}).get("Nodes", [])[0].get("Facets", [])
        return manufacturers
    except Exception as e:
        print("Ошибка при получении марок:", e)
        return []

def get_models_by_brand(manufacturer):
    url = f"https://api.encar.com/search/car/list/general?count=true&q=(And.Hidden.N._.SellType.%EC%9D%bc%EB%B0%98._.(C.CarType.A._.Manufacturer.{manufacturer}.))&inav=%7CMetadata%7CSort"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        all_manufacturers = data.get("iNav", {}).get("Nodes", [])[2].get("Facets", [])[0].get("Refinements", {}).get("Nodes", [])[0].get("Facets", [])
        selected_manufacturer = next((item for item in all_manufacturers if item.get("IsSelected")), None)
        if selected_manufacturer:
            return selected_manufacturer.get("Refinements", {}).get("Nodes", [])[0].get("Facets", [])
        return []
    except Exception as e:
        print(f"Ошибка при получении моделей для {manufacturer}:", e)
        return []

def get_generations_by_model(manufacturer, model_group):
    url = f"https://api.encar.com/search/car/list/general?count=true&q=(And.Hidden.N._.SellType.%EC%9D%bc%EB%B0%98._.(C.CarType.A._.(C.Manufacturer.{manufacturer}._.ModelGroup.{model_group}.)))&inav=%7CMetadata%7CSort"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        all_manufacturers = data.get("iNav", {}).get("Nodes", [])[2].get("Facets", [])[0].get("Refinements", {}).get("Nodes", [])[0].get("Facets", [])
        selected_manufacturer = next((item for item in all_manufacturers if item.get("IsSelected")), None)
        if not selected_manufacturer:
            return []
        model_group_data = selected_manufacturer.get("Refinements", {}).get("Nodes", [])[0].get("Facets", [])
        selected_model = next((item for item in model_group_data if item.get("IsSelected")), None)
        if not selected_model:
            return []
        return selected_model.get("Refinements", {}).get("Nodes", [])[0].get("Facets", [])
    except Exception as e:
        print(f"Ошибка при получении поколений для {manufacturer}, {model_group}:", e)
        return []

def get_trims_by_generation(manufacturer, model_group, model):
    url = f"https://api.encar.com/search/car/list/general?count=true&q=(And.Hidden.N._.(C.CarType.A._.(C.Manufacturer.{manufacturer}._.(C.ModelGroup.{model_group}._.Model.{model}.))))&inav=%7CMetadata%7CSort"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        all_manufacturers = data.get("iNav", {}).get("Nodes", [])[1].get("Facets", [])[0].get("Refinements", {}).get("Nodes", [])[0].get("Facets", [])
        selected_manufacturer = next((item for item in all_manufacturers if item.get("IsSelected")), None)
        if not selected_manufacturer:
            return []
        model_group_data = selected_manufacturer.get("Refinements", {}).get("Nodes", [])[0].get("Facets", [])
        selected_model_group = next((item for item in model_group_data if item.get("IsSelected")), None)
        if not selected_model_group:
            return []
        model_data = selected_model_group.get("Refinements", {}).get("Nodes", [])[0].get("Facets", [])
        selected_model = next((item for item in model_data if item.get("IsSelected")), None)
        if not selected_model:
            return []
        return selected_model.get("Refinements", {}).get("Nodes", [])[0].get("Facets", [])
    except Exception as e:
        print(f"Ошибка при получении комплектаций для {manufacturer}, {model_group}, {model}:", e)
        return []

@bot.message_handler(commands=['start'])
def start_handler(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔍 Найти авто", callback_data="search_car"),
        types.InlineKeyboardButton("🧮 Рассчитать по ссылке", url="https://t.me/kgaexportbot"),
    )
    markup.add(
        types.InlineKeyboardButton("📸 Instagram", url="https://www.instagram.com/kgakorea/"),
        types.InlineKeyboardButton("🎵 TikTok", url="https://www.tiktok.com/@kga_korea")
    )
    markup.add(
        types.InlineKeyboardButton("🌐 Сайт компании", url="https://kga-korea.com/")
    )
    welcome_text = (
        "👋 Добро пожаловать бот от *KGA Korea*!\n\n"
        "С помощью этого бота вы можете:\n"
        "• 🔍 Найти интересующий вас автомобиль\n"
        "• 🧮 Получить расчёт стоимости авто по ссылке\n"
        "• 📬 Подписаться на соцсети и быть в курсе\n\n"
        "*Выберите действие ниже:*"
    )
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "search_car")
def handle_search_car(call):
    manufacturers = get_manufacturers()
    if not manufacturers:
        bot.answer_callback_query(call.id, "Не удалось загрузить марки.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    for item in manufacturers:  # Удалено ограничение [:10]
        kr_name = item.get("DisplayValue", "Без названия")
        eng_name = item.get("Metadata", {}).get("EngName", [""])[0]
        callback_data = f"brand_{eng_name}_{kr_name}"
        display_text = f"{eng_name}"
        markup.add(types.InlineKeyboardButton(display_text, callback_data=callback_data))

    bot.edit_message_text(
        "Выбери марку автомобиля:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("brand_"))
def handle_brand_selection(call):
    _, eng_name, kr_name = call.data.split("_", 2)
    models = get_models_by_brand(kr_name)
    if not models:
        bot.answer_callback_query(call.id, "Не удалось загрузить модели.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    for item in models:
        model_kr = item.get("DisplayValue", "Без названия")
        model_eng = item.get("Metadata", {}).get("EngName", [""])[0]
        callback_data = f"model_{model_eng}_{model_kr}"
        display_text = f"{model_eng}"
        markup.add(types.InlineKeyboardButton(display_text, callback_data=callback_data))

    bot.edit_message_text(
        f"Марка: {eng_name} ({kr_name})\nТеперь выбери модель:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("model_"))
def handle_model_selection(call):
    _, model_eng, model_kr = call.data.split("_", 2)
    message_text = call.message.text
    # Получаем марку из предыдущего текста сообщения
    brand_line = next((line for line in message_text.split("\n") if "Марка:" in line), "")
    brand_part = brand_line.replace("Марка:", "").strip()
    if " (" in brand_part:
        brand_eng, brand_kr = brand_part.split(" (")
        brand_kr = brand_kr.rstrip(")")
    else:
        brand_eng = brand_part
        brand_kr = ""

    generations = get_generations_by_model(brand_kr, model_kr)
    if not generations:
        bot.answer_callback_query(call.id, "Не удалось загрузить поколения.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    for item in generations:
        gen_kr = item.get("DisplayValue", "Без названия")
        gen_eng = item.get("Metadata", {}).get("EngName", [""])[0]

        start_raw = str(item.get("Metadata", {}).get("ModelStartDate", [""])[0])
        end_raw = str(item.get("Metadata", {}).get("ModelEndDate", [""])[0])

        def format_date(date_str):
            if len(date_str) == 6:
                return f"{date_str[4:6]}.{date_str[0:4]}"
            return ""

        start_date = format_date(start_raw)
        end_date = format_date(end_raw) if len(end_raw) > 0 else "н.в."

        period = f"({start_date} — {end_date})" if start_date else ""

        callback_data = f"generation_{gen_eng}_{gen_kr}"
        display_text = f"{gen_kr} {gen_eng} {period}".strip()
        markup.add(types.InlineKeyboardButton(display_text, callback_data=callback_data))

    bot.edit_message_text(
        f"Марка: {brand_eng.strip()} ({brand_kr})\nМодель: {model_eng} ({model_kr})\nТеперь выбери поколение:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("generation_"))
def handle_generation_selection(call):
    def translate_trim(text):
        return (text
            .replace("가솔린+전기", "Гибрид")
            .replace("가솔린", "Бензин")
            .replace("디젤", "Дизель")
            .replace("전기", "Электро")
            .replace("2WD", "2WD")
            .replace("4WD", "4WD")
        )
    
    _, generation_eng, generation_kr = call.data.split("_", 2)
    message_text = call.message.text

    brand_line = next((line for line in message_text.split("\n") if "Марка:" in line), "")
    model_line = next((line for line in message_text.split("\n") if "Модель:" in line), "")

    brand_eng, brand_kr = brand_line.replace("Марка:", "").strip().split(" (")
    brand_kr = brand_kr.rstrip(")")
    model_eng, model_kr = model_line.replace("Модель:", "").strip().split(" (")

    model_kr = model_kr.rstrip(")")

    generations = get_generations_by_model(brand_kr, model_kr)
    selected_generation = next((g for g in generations if g.get("DisplayValue") == generation_kr or g.get("Metadata", {}).get("EngName", [""])[0] == generation_eng), None)
    if not selected_generation:
        bot.answer_callback_query(call.id, "Не удалось определить поколение.")
        return

    start_raw = str(selected_generation.get("Metadata", {}).get("ModelStartDate", [""])[0])
    end_raw = str(selected_generation.get("Metadata", {}).get("ModelEndDate", [""])[0])

    trims = get_trims_by_generation(brand_kr, model_kr, generation_kr)
    if not trims:
        bot.answer_callback_query(call.id, "Не удалось загрузить комплектации.")
        return

    current_year = datetime.now().year
    current_month = datetime.now().month

    start_year = int(start_raw[:4]) if start_raw and start_raw.isdigit() and len(start_raw) == 6 else current_year
    if end_raw and end_raw.isdigit() and len(end_raw) == 6:
        end_year = int(end_raw[:4])
    else:
        end_year = current_year

    markup = types.InlineKeyboardMarkup(row_width=2)
    for item in trims:
        trim_kr = item.get("DisplayValue", "Без названия")
        trim_eng = item.get("Metadata", {}).get("EngName", [""])[0]
        callback_data = f"trim_{trim_eng}_{trim_kr}"
        display_text = translate_trim(trim_eng or trim_kr)
        markup.add(types.InlineKeyboardButton(display_text, callback_data=callback_data))

    bot.edit_message_text(
        f"Марка: {brand_eng.strip()} ({brand_kr})\nМодель: {model_eng} ({model_kr})\nПоколение: {generation_eng} ({generation_kr})\nТеперь выбери комплектацию:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("trim_"))
def handle_trim_selection(call):
    parts = call.data.split("_", 2)
    trim_eng = parts[1]
    trim_kr = parts[2] if len(parts) > 2 else parts[1]
    if not trim_eng.strip():
        print("⚠️ trim_eng пустой, возможно, ошибка в callback_data или split")
    message_text = call.message.text

    brand_line = next((line for line in message_text.split("\n") if "Марка:" in line), "")
    model_line = next((line for line in message_text.split("\n") if "Модель:" in line), "")
    generation_line = next((line for line in message_text.split("\n") if "Поколение:" in line), "")

    brand_eng, brand_kr = brand_line.replace("Марка:", "").strip().split(" (")
    brand_kr = brand_kr.rstrip(")")
    model_part = model_line.replace("Модель:", "").strip()
    if " (" in model_part:
        model_eng, model_kr = model_part.split(" (")
        model_kr = model_kr.rstrip(")")
    else:
        model_eng = model_part
        model_kr = ""
    generation_part = generation_line.replace("Поколение:", "").strip()
    if "(" in generation_part and ")" in generation_part:
        parts = generation_part.rsplit("(", 1)
        generation_eng = parts[0].strip()
        generation_kr = parts[1].replace(")", "").strip()
        generation_kr = translations.get(generation_kr, generation_kr)
    else:
        generation_eng = generation_part
        generation_kr = ""

    generations = get_generations_by_model(brand_kr, model_kr)
    selected_generation = next(
        (g for g in generations if
         g.get("DisplayValue") == generation_kr or
         generation_kr in g.get("DisplayValue", "") or
         generation_eng in g.get("Metadata", {}).get("EngName", [""])[0]),
        None
    )
    if not selected_generation:
        bot.answer_callback_query(call.id, "Не удалось определить поколение.")
        return

    start_raw = str(selected_generation.get("Metadata", {}).get("ModelStartDate", [""])[0])
    end_raw = str(selected_generation.get("Metadata", {}).get("ModelEndDate", [""])[0] or "")

    current_year = datetime.now().year
    current_month = datetime.now().month

    if end_raw and end_raw.isdigit():
        end_year = int(end_raw[:4])
    else:
        end_year = current_year

    end_date_value = end_raw if len(end_raw) > 0 else f"{current_year}{current_month:02d}"

    start_year = int(start_raw[:4]) if len(start_raw) == 6 else current_year
    end_year = int(end_date_value[:4])

    year_markup = types.InlineKeyboardMarkup(row_width=4)
    for y in range(start_year, end_year + 1):
        year_markup.add(types.InlineKeyboardButton(str(y), callback_data=f"year_{y}"))

    user_id = call.from_user.id
    print(f"✅ DEBUG trim_eng: {trim_eng}")
    print(f"✅ DEBUG trim_kr: {trim_kr}")
    if user_id not in user_search_data:
        user_search_data[user_id] = {}
    user_search_data[user_id]["manufacturer"] = brand_kr.strip()
    user_search_data[user_id]["model_group"] = model_kr.strip()
    user_search_data[user_id]["model"] = generation_kr.strip()
    user_search_data[user_id]["trim"] = trim_eng.strip() or trim_kr.strip()
    bot.send_message(
        call.message.chat.id,
        f"Марка: {brand_eng.strip()} ({brand_kr})\nМодель: {model_eng} ({model_kr})\nПоколение: {generation_eng} ({generation_kr})\nКомплектация: {trim_eng} ({trim_kr})"
    )
    bot.send_message(
        call.message.chat.id,
        "Выбери год выпуска автомобиля:",
        reply_markup=year_markup
    )
    
    mileage_markup = types.InlineKeyboardMarkup(row_width=4)
    for value in range(0, 200001, 10000):
        mileage_markup.add(types.InlineKeyboardButton(f"{value} км", callback_data=f"mileage_from_{value}"))


    # Removed mileage selection from trim handler.

@bot.callback_query_handler(func=lambda call: call.data.startswith("year_"))
def handle_year_selection(call):
    selected_year = int(call.data.split("_")[1])
    user_id = call.from_user.id
    if user_id not in user_search_data:
        user_search_data[user_id] = {}
    user_search_data[user_id]["year"] = selected_year  # 👈 сохраняем год

    mileage_markup = types.InlineKeyboardMarkup(row_width=4)
    for value in range(0, 200001, 10000):
        mileage_markup.add(types.InlineKeyboardButton(f"{value} км", callback_data=f"mileage_from_{value}"))
    message_text = call.message.text
    bot.send_message(
        call.message.chat.id,
        f"{message_text}\nГод выпуска: {selected_year}\nТеперь выбери минимальный пробег:",
        reply_markup=mileage_markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("mileage_from_"))
def handle_mileage_from(call):
    mileage_from = int(call.data.split("_")[2])
    mileage_markup = types.InlineKeyboardMarkup(row_width=4)
    for value in range(mileage_from + 10000, 200001, 10000):
        mileage_markup.add(types.InlineKeyboardButton(f"{value} км", callback_data=f"mileage_to_{mileage_from}_{value}"))

    bot.send_message(
        call.message.chat.id,
        f"Минимальный пробег: {mileage_from} км\nТеперь выбери максимальный пробег:",
        reply_markup=mileage_markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("mileage_to_"))
def handle_mileage_to(call):
    mileage_from = int(call.data.split("_")[2])
    mileage_to = int(call.data.split("_")[3])

    markup = types.InlineKeyboardMarkup(row_width=2)
    for kr, ru in COLOR_TRANSLATIONS.items():
        markup.add(types.InlineKeyboardButton(ru, callback_data=f"color_{kr}"))

    bot.send_message(
        call.message.chat.id,
        f"Пробег: от {mileage_from} км до {mileage_to} км\nТеперь выбери цвет автомобиля:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("color_"))
def handle_color_selection(call):
    selected_color_kr = call.data.split("_", 1)[1]
    message_text = call.message.text
    selected_color_ru = "Любой" if selected_color_kr == "all" else COLOR_TRANSLATIONS.get(selected_color_kr, "Неизвестно")

    user_id = call.from_user.id
    user_data = user_search_data.get(user_id, {})
    print(f"✅ DEBUG user_data before color selection: {user_data}")

    manufacturer = user_data.get("manufacturer", "")
    model_group = user_data.get("model_group", "")
    model = user_data.get("model", "")
    trim = user_data.get("trim", "")

    mileage_line = next((line for line in message_text.split("\n") if "Пробег:" in line), "")
    mileage_from = int(mileage_line.split("от")[1].split("км")[0].strip())
    mileage_to = int(mileage_line.split("до")[1].split("км")[0].strip())

    year = user_data.get("year", datetime.now().year)

    print("⚙️ Данные переданы в check_for_new_cars:")
    print(f"manufacturer: {manufacturer.strip()}")
    print(f"model_group: {model_group.strip()}")
    print(f"model: {model.strip()}")
    print(f"trim: {trim.strip()}")

    bot.send_message(
        call.message.chat.id,
        "🔍 Начинаем поиск автомобилей по заданным параметрам. Это может занять некоторое время..."
    )
    # Кнопка для добавления нового автомобиля в поиск
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Добавить новый автомобиль в поиск", callback_data="search_car"))
    bot.send_message(call.message.chat.id, "Хотите добавить ещё один автомобиль в поиск?", reply_markup=markup)

    import threading
    threading.Thread(
        target=check_for_new_cars,
        args=(
            call.message.chat.id,
            manufacturer.strip(),  # manufacturer
            model_group.strip(),   # model_group
            model.strip(),         # model
            trim.strip(),          # trim
            year,
            mileage_from,
            mileage_to,
            selected_color_kr.strip()
        ),
        daemon=True
    ).start()
    
@bot.message_handler(state=CarForm.brand)
def handle_brand(message):
    bot.send_message(message.chat.id, "Отлично! Теперь введи модель:")
    bot.set_state(message.from_user.id, CarForm.model, message.chat.id)

# Обработчик модели
@bot.message_handler(state=CarForm.model)
def handle_model(message):
    bot.send_message(message.chat.id, "Укажи поколение:")
    bot.set_state(message.from_user.id, CarForm.generation, message.chat.id)

checked_ids = set()

def build_encar_url(manufacturer, model_group, model, trim, year, mileage_from, mileage_to, color):
    print("DEBUG PARAMS:")
    print("RAW INPUTS:", manufacturer, model_group, model, trim)
    print("manufacturer:", f"[{manufacturer}]")
    print("model_group:", f"[{model_group}]")
    print("model:", f"[{model}]")
    print("trim:", f"[{trim}]")
    print("year:", year)
    print("mileage_from:", mileage_from)
    print("mileage_to:", mileage_to)
    print("color:", f"[{color}]")

    if not all([manufacturer.strip(), model_group.strip(), model.strip(), trim.strip()]):
        print("❌ Не переданы необходимые параметры для построения URL")
        return ""

    # Строим основной фильтр без цвета и пробега
    core_query = (
        f"(And.Hidden.N._.SellType.일반._."
        f"(C.CarType.A._."
        f"(C.Manufacturer.{manufacturer}._."
        f"(C.ModelGroup.{model_group}._."
        f"(C.Model.{model_group} ({model})._."
        f"(And.BadgeGroup.{trim}._.YearGroup.{year}.))))))"
    )

    # Добавляем фильтры цвета и пробега снаружи
    mileage_part = f"Mileage.range({mileage_from}..{mileage_to})" if mileage_from > 0 else f"Mileage.range(..{mileage_to})"
    extended_query = f"{core_query}_.Color.{color}._.{mileage_part}."

    encoded_query = urllib.parse.quote(extended_query, safe="()_.%")
    url = f"https://api-encar.habsidev.com/api/catalog?count=true&q={encoded_query}&sr=%7CModifiedDate%7C0%7C1"

    print(f"📡 Сформирован URL: {url}")
    return url

def check_for_new_cars(chat_id, manufacturer, model_group, model, trim, year_from, mileage_from, mileage_to, color):
    url = build_encar_url(manufacturer, model_group, model, trim, year_from, mileage_from, mileage_to, color)

    print(url)

    while True:
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

            if response.status_code != 200:
                print(f"❌ API вернул статус {response.status_code}: {response.text}")
                time.sleep(300)
                continue

            try:
                data = response.json()
            except Exception as json_err:
                print(f"❌ Ошибка парсинга JSON: {json_err}")
                print(f"Ответ: {response.text}")
                time.sleep(300)
                continue

            cars = data.get("SearchResults", [])
            new_cars = [car for car in cars if car["Id"] not in checked_ids]

            for car in new_cars:
                checked_ids.add(car["Id"])
                details_url = f"https://api.encar.com/v1/readside/vehicle/{car['Id']}"
                details_response = requests.get(details_url, headers={"User-Agent": "Mozilla/5.0"})
               
                if details_response.status_code == 200:
                    details_data = details_response.json()
                    specs = details_data.get("spec", {})
                    displacement = specs.get("displacement", "Не указано")
                    extra_text = f"\nОбъём двигателя: {displacement}cc\n\n👉 <a href='https://fem.encar.com/cars/detail/{car['Id']}'>Ссылка на автомобиль</a>"
                else:
                    extra_text = "\nℹ️ Не удалось получить подробности о машине."

                name = f'{car.get("Manufacturer", "")} {car.get("Model", "")} {car.get("Badge", "")}'
                price = car.get("Price", 0)
                mileage = car.get("Mileage", 0)
                year = car.get("FormYear", "")
                
                def format_number(n):
                    return f"{int(n):,}".replace(",", " ")
                
                formatted_mileage = format_number(mileage)
                formatted_price = format_number(price * 10000)
                
                text = f"✅ Новое поступление по вашему запросу!\n\n<b>{name}</b> {year} г.\nПробег: {formatted_mileage} км\nЦена: ₩{formatted_price}" + extra_text
                bot.send_message(chat_id, text, parse_mode="HTML")

            time.sleep(300)
        except Exception as e:
            print(f"🔧 Общая ошибка при проверке новых авто: {e}")
            time.sleep(300)

# Запуск бота
if __name__ == "__main__":
    print("Bot is running...")
    
    # url = build_encar_url(
    #     manufacturer="현대",
    #     model_group="쏘나타",
    #     model="쏘나타 디 엣지(DN8_)",
    #     trim="가솔린 1600cc",
    #     year=2023,
    #     mileage_from=1,
    #     mileage_to=200000,
    #     color="검정색"
    # )
    # print(url)

    bot.infinity_polling()