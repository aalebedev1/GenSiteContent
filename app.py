# -*- coding: utf-8 -*-
"""
Генератор постов для товаров — Flask-приложение.
Запуск: python app.py
Для изменений тона, длины, эмодзи — смотри файл voice.md
"""

from flask import Flask, render_template, request, jsonify
import random

app = Flask(__name__)

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
# Функция читает настройки из voice.md и возвращает словарь.
# Если файла нет — возвращаются значения по умолчанию.
# ============================================================
def load_voice_settings():
    try:
        with open("voice.md", "r", encoding="utf-8") as f:
            content = f.read()
        return {"raw": content, "loaded": True}
    except FileNotFoundError:
        return {"raw": "Файл voice.md не найден. Создайте его для кастомизации тона.", "loaded": False}


# ============================================================
# МАРШРУТЫ (ROUTES)
# ============================================================

@app.route("/")
def index():
    """Главная страница — передаём в шаблон настройки и список настроений."""
    voice = load_voice_settings()
    return render_template("index.html", voice=voice, moods=MOOD_NAMES)


@app.route("/generate", methods=["POST"])
def generate():
    """
    Генерация поста.
    Принимает из формы: product_name, description, price, mood.
    Возвращает JSON с готовым текстом или ошибку.
    """
    name = request.form.get("product_name", "").strip()
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "").strip()
    mood = request.form.get("mood", "friendly")

    # Проверка обязательного поля
    if not description:
        return jsonify({"error": "Поле «Описание товара» обязательно для заполнения."}), 400

    # Если название не указано — используем заглушку
    if not name:
        name = "Этот товар"

    # Если цена не указана — убираем из шаблона
    if not price:
        price = "доступной цене"

    # Выбираем случайный шаблон для выбранного настроения
    templates = POST_TEMPLATES.get(mood, POST_TEMPLATES["friendly"])
    template = random.choice(templates)

    # Формируем пост
    post_text = template.format(name=name, description=description, price=price)

    return jsonify({"post": post_text})


# ============================================================
# ЗАПУСК
# ============================================================
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
