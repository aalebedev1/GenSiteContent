# -*- coding: utf-8 -*-
"""
Генератор постов для товаров — Flask-приложение.
Запуск: python app.py

Возможности:
  - Генерация текста по шаблону (5 настроений)
  - Публикация ВКонтакте (мгновенно или по расписанию)
  - Сохранение постов в избранное

Для изменений тона, длины, эмодзи — смотри файл voice.md
Для подключения ВК — заполни config.json (см. config.example.json)
"""

from flask import Flask, render_template, request, jsonify, send_file
import random
import json
import os
import hashlib
from datetime import datetime
import requests

app = Flask(__name__)

# ============================================================
# ФАЙЛЫ КОНФИГУРАЦИИ И ДАННЫХ
# ============================================================
CONFIG_FILE = "config.json"
FAVORITES_FILE = "favorites.json"


# ============================================================
# ШАБЛОНЫ ПОСТОВ — группировка по настроению (mood)
# Каждый шаблон использует {name}, {description}, {price}
# Чтобы добавить новый шаблон — просто допиши ещё одну строку
# ============================================================

POST_TEMPLATES = {

    # ----- ВОСТОРЖЕННЫЙ -----
    "enthusiastic": [
        "🔥 {name} — то, что вам нужно!\n\n{description}\n\nВсего {price}! 🎉\nНе упустите возможность!",
        "💥 Вы будете в восторге от {name}!\n\n{description}\n\nСпециальная цена: {price} ⚡\nЗабирайте прямо сейчас!",
        "🌟 {name} уже покоряет сердца!\n\n{description}\n\nВсего {price} — и вы счастливый обладатель! 🎊",
    ],

    # ----- ДЕЛОВОЙ -----
    "professional": [
        "📊 {name}: профессиональное решение\n\n{description}\n\n{price}\nИнвестируйте в качество.",
        "⚙️ {name} — надёжность и эффективность\n\n{description}\n\nСтоимость: {price}\nВыбирайте проверенное.",
        "📈 {name} для тех, кто ценит результат\n\n{description}\n\n{price}\nРазумный выбор профессионалов.",
    ],

    # ----- ДРУЖЕСКИЙ -----
    "friendly": [
        "👋 Друзья, хочу поделиться находкой!\n\n{name}\n\n{description}\n\nИ это всего {price}! 💫",
        "😊 Вы спрашивали — мы нашли!\n\n{name} — {description}\n\nЦена вопроса: {price} 🎁\n\nДовольны будете на все 100%!",
        "💬 От души рекомендую {name}!\n\n{description}\n\n{price} — согласитесь, отличное предложение 🌸",
    ],

    # ----- КРАТКИЙ -----
    "concise": [
        "✏️ {name}\n{description}\n{price}",
        "{name}\n\n{description}\n\n👉 {price}",
        "📌 {name} | {price}\n{description}",
    ],

    # ----- ЗАБОТЛИВЫЙ -----
    "caring": [
        "💛 Забота о вас — наша главная цель\n\n{name} — {description}\n\nВсего {price} 🌟\n\nПодарите себе лучшее!",
        "🌿 Позаботьтесь о себе с {name}\n\n{description}\n\n{price} — это ли не подарок судьбы? 💝",
        "🤗 Вы достойны лучшего!\n\n{name}\n\n{description}\n\nС любовью, всего за {price} ✨",
    ],
}

# Соответствие ключей и русских названий для выпадающего списка
MOOD_NAMES = {
    "enthusiastic": "Восторженный 🎉",
    "professional": "Деловой 📊",
    "friendly": "Дружеский 👋",
    "concise": "Краткий ✏️",
    "caring": "Заботливый 💛",
}


# ============================================================
# ЧТЕНИЕ ФАЙЛА voice.md
# ============================================================
def load_voice_settings():
    """Читает настройки из voice.md. Если файла нет — заглушка."""
    try:
        with open("voice.md", "r", encoding="utf-8") as f:
            content = f.read()
        return {"raw": content, "loaded": True}
    except FileNotFoundError:
        return {"raw": "Файл voice.md не найден. Создайте его для кастомизации тона.", "loaded": False}


# ============================================================
# НАСТРОЙКИ ВКОНТАКТЕ (config.json)
# ============================================================
def load_config():
    """
    Читает config.json и проверяет, заполнены ли VK-данные.
    Если файла нет — создаёт пустой.
    """
    default = {"vk_token": "", "vk_group_id": "", "vk_api_version": "5.199"}
    if not os.path.exists(CONFIG_FILE):
        save_config(default)
        return default
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # Добавляем ключи, которых нет в файле (обновление версии)
        for k, v in default.items():
            cfg.setdefault(k, v)
        return cfg
    except (json.JSONDecodeError, IOError):
        return default


def save_config(cfg):
    """Сохраняет config.json."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=4)


def is_vk_configured():
    """Проверяет, заполнены ли token и group_id."""
    cfg = load_config()
    return bool(cfg.get("vk_token") and cfg.get("vk_group_id"))


# ============================================================
# ИЗБРАННОЕ (favorites.json)
# ============================================================
def load_favorites():
    """Читает список избранных постов из JSON-файла."""
    if not os.path.exists(FAVORITES_FILE):
        return []
    try:
        with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def save_favorites(favs):
    """Сохраняет список избранных постов в JSON-файл."""
    with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
        json.dump(favs, f, ensure_ascii=False, indent=2)


# ============================================================
# ПУБЛИКАЦИЯ ВКОНТАКТЕ
# ============================================================
def vk_publish_post(message, publish_date=None):
    """
    Публикует пост на стене сообщества ВКонтакте.
    * message — текст поста
    * publish_date — Unix-метка времени (для отложенной публикации)
    Возвращает словарь с результатом.
    """
    cfg = load_config()
    token = cfg.get("vk_token", "")
    group_id = cfg.get("vk_group_id", "")
    api_version = cfg.get("vk_api_version", "5.199")

    if not token or not group_id:
        return {"success": False, "error": "VK не настроен. Заполните config.json."}

    # URL метода wall.post
    url = "https://api.vk.com/method/wall.post"

    # owner_id для сообщества — отрицательное число
    try:
        owner_id = -abs(int(group_id))
    except ValueError:
        return {"success": False, "error": "vk_group_id должен быть числом (ID сообщества)."}

    params = {
        "owner_id": owner_id,
        "message": message,
        "access_token": token,
        "v": api_version,
    }

    # Если указано время отложенной публикации
    if publish_date is not None:
        params["publish_date"] = int(publish_date)

    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Ошибка соединения с VK: {e}"}
    except ValueError:
        return {"success": False, "error": "Неверный ответ от VK API."}

    # Проверяем ошибки VK API
    if "error" in data:
        code = data["error"].get("error_code", "?")
        msg = data["error"].get("error_msg", "Неизвестная ошибка VK")
        return {"success": False, "error": f"VK ошибка {code}: {msg}"}

    # Успех
    post_id = data.get("response", {}).get("post_id")
    return {"success": True, "post_id": post_id, "scheduled": publish_date is not None}


# ============================================================
# МАРШРУТЫ (ROUTES)
# ============================================================

@app.route("/")
def index():
    """Главная страница."""
    voice = load_voice_settings()
    vk_ok = is_vk_configured()
    favs = load_favorites()
    return render_template("index.html", voice=voice, moods=MOOD_NAMES,
                           vk_configured=vk_ok, favorites=favs)


# ---- ГЕНЕРАЦИЯ ПОСТА ---------------------------------------

@app.route("/generate", methods=["POST"])
def generate():
    """
    Генерация поста по шаблону.
    Принимает: product_name, description, price, mood.
    Возвращает JSON с текстом.
    """
    name = request.form.get("product_name", "").strip()
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "").strip()
    mood = request.form.get("mood", "friendly")

    if not description:
        return jsonify({"error": "Поле «Описание товара» обязательно для заполнения."}), 400

    if not name:
        name = "Этот товар"

    if not price:
        price = "доступной цене"

    templates = POST_TEMPLATES.get(mood, POST_TEMPLATES["friendly"])
    template = random.choice(templates)
    post_text = template.format(name=name, description=description, price=price)

    return jsonify({"post": post_text, "mood": mood, "product_name": name})


# ---- ПУБЛИКАЦИЯ ВКОНТАКТЕ -----------------------------------

@app.route("/publish", methods=["POST"])
def publish():
    """
    Публикует пост ВКонтакте (мгновенно или по расписанию).
    Принимает: text, schedule (опционально — строка datetime-local).
    """
    text = request.form.get("text", "").strip()
    schedule_str = request.form.get("schedule", "").strip()

    if not text:
        return jsonify({"error": "Нет текста для публикации."}), 400

    # Если указано время отложенной публикации
    publish_ts = None
    if schedule_str:
        try:
            # Формат из datetime-local: "2026-05-10T15:30"
            dt = datetime.strptime(schedule_str, "%Y-%m-%dT%H:%M")
            publish_ts = dt.timestamp()
            # Проверяем, что время в будущем
            if publish_ts <= datetime.now().timestamp():
                return jsonify({"error": "Время отложенной публикации должно быть в будущем."}), 400
        except ValueError:
            return jsonify({"error": "Неверный формат даты и времени."}), 400

    result = vk_publish_post(text, publish_ts)

    if result["success"]:
        if result.get("scheduled"):
            msg = "Пост запланирован на указанное время."
        else:
            msg = "Пост опубликован!"
        return jsonify({"success": True, "message": msg, "post_id": result.get("post_id")})
    else:
        return jsonify({"error": result["error"]}), 400


# ---- ИЗБРАННОЕ ----------------------------------------------

@app.route("/favorite/add", methods=["POST"])
def favorite_add():
    """Добавляет пост в избранное."""
    text = request.form.get("text", "").strip()
    product_name = request.form.get("product_name", "").strip()
    mood = request.form.get("mood", "").strip()

    if not text:
        return jsonify({"error": "Нет текста для сохранения."}), 400

    favs = load_favorites()

    # Проверяем, нет ли уже такого поста (по тексту)
    for f in favs:
        if f["text"] == text:
            return jsonify({"success": True, "message": "Пост уже в избранном.", "id": f["id"]})

    # Создаём ID на основе текста и времени
    raw = text + datetime.now().isoformat()
    post_id = hashlib.md5(raw.encode()).hexdigest()[:8]

    favs.append({
        "id": post_id,
        "text": text,
        "product_name": product_name,
        "mood": mood,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    save_favorites(favs)
    return jsonify({"success": True, "message": "Пост добавлен в избранное!", "id": post_id})


@app.route("/favorite/remove", methods=["POST"])
def favorite_remove():
    """Удаляет пост из избранного по ID."""
    post_id = request.form.get("id", "").strip()

    if not post_id:
        return jsonify({"error": "Не указан ID поста."}), 400

    favs = load_favorites()
    new_favs = [f for f in favs if f["id"] != post_id]

    if len(new_favs) == len(favs):
        return jsonify({"error": "Пост с таким ID не найден."}), 404

    save_favorites(new_favs)
    return jsonify({"success": True, "message": "Пост удалён из избранного."})


@app.route("/favorites/list")
def favorites_list():
    """Возвращает список избранных постов."""
    return jsonify(load_favorites())


# ---- СТАТИЧЕСКИЕ ФАЙЛЫ В КОРНЕ ПРОЕКТА -----------------------

@app.route("/voice.md")
def serve_voice():
    return send_file("voice.md")


@app.route("/config.example.json")
def serve_config_example():
    return send_file("config.example.json")


# ============================================================
# ЗАПУСК
# ============================================================
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
