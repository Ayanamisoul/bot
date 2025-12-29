import telebot
from telebot import types
import psycopg2
import threading
import time
from datetime import datetime, timedelta

# --- Настройка бота и базы данных ---
bot = telebot.TeleBot('8371274334:AAHpaZsUQ_FP7lNrLMVxnFlvU_uyK3vnamI')

conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="postgres",
    host="localhost",
    port=5432
)
cursor = conn.cursor()

INTERESTS_PER_PAGE = 5

# --- Функции для интересов ---
def get_interests_page(page):
    cursor.execute("SELECT id, name FROM interests ORDER BY id")
    all_interests = cursor.fetchall()
    start = page * INTERESTS_PER_PAGE
    end = start + INTERESTS_PER_PAGE
    return all_interests[start:end], len(all_interests)

def show_interests_page(chat_id, page):
    interests_page, total = get_interests_page(page)
    keyboard = types.InlineKeyboardMarkup()
    for interest_id, name in interests_page:
        keyboard.add(types.InlineKeyboardButton(name, callback_data=f"interest_{interest_id}"))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅ Назад", callback_data=f"intset_page_{page-1}"))
    if (page + 1) * INTERESTS_PER_PAGE < total:
        nav_buttons.append(types.InlineKeyboardButton("Вперед ➡", callback_data=f"intset_page_{page+1}"))
    if nav_buttons:
        keyboard.row(*nav_buttons)

    bot.send_message(chat_id, "Выберите интерес:", reply_markup=keyboard)
# --- Оставить отзыв ---
def leave_review(chat_id, user_id, club_id):
    msg = bot.send_message(chat_id, "Введите ваш отзыв:")
    bot.register_next_step_handler(msg, lambda m: save_review_text(m, user_id, club_id))

def save_review_text(message, user_id, club_id):
    review_text = message.text
    msg = bot.send_message(message.chat.id, "Оцените клуб от 1 до 5:")
    bot.register_next_step_handler(msg, lambda m: save_review_rating(m, user_id, club_id, review_text))

def save_review_rating(message, user_id, club_id, review_text):
    try:
        rating = int(message.text)
        if rating < 1 or rating > 5:
            raise ValueError
    except ValueError:
        msg = bot.send_message(message.chat.id, "Введите число от 1 до 5:")
        bot.register_next_step_handler(msg, lambda m: save_review_rating(m, user_id, club_id, review_text))
        return

    try:
        cursor.execute("""
            INSERT INTO reviews (user_id, club_id, rating, comment, created_at, status)
            VALUES (%s, %s, %s, %s, NOW(), %s)
        """, (user_id, club_id, rating, review_text, 'active'))
        conn.commit()
        bot.send_message(message.chat.id, "✅ Ваш отзыв сохранён в базе данных!")
    except psycopg2.Error as e:
        conn.rollback()
        bot.send_message(message.chat.id, f"❌ Ошибка при сохранении отзыва: {e}")


        
# --- Просмотреть отзывы ---
def view_reviews(chat_id, club_id):
    cursor.execute("""
        SELECT rating, comment, created_at
        FROM reviews
        WHERE club_id=%s
        ORDER BY created_at DESC
    """, (club_id,))
    reviews = cursor.fetchall()
    if not reviews:
        bot.send_message(chat_id, "Отзывов пока нет.")
        return

    cursor.execute("SELECT AVG(rating) FROM reviews WHERE club_id=%s", (club_id,))
    avg_rating = cursor.fetchone()[0]
    bot.send_message(chat_id, f"⭐ Средний рейтинг клуба: {avg_rating:.1f}/5")

    for r in reviews:
        bot.send_message(chat_id, f"Оценка: {r[0]}/5\nОтзыв: {r[1]}\nДата: {r[2].strftime('%d.%m.%Y %H:%M')}")

# --- Главное меню ---
def show_main_menu(message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton('Уровень подготовки', callback_data='level'),
        types.InlineKeyboardButton('Ваши интересы', callback_data='interes')
    )
    keyboard.add(
        types.InlineKeyboardButton('Рекомендации', callback_data='recomends'),
        types.InlineKeyboardButton('Записи', callback_data='zap')
    )
    keyboard.add(
        types.InlineKeyboardButton('Товары', callback_data='atr'),
        types.InlineKeyboardButton('Поиск', callback_data='find')
    )
    bot.send_message(
        message.chat.id,
        f"👋 Добро пожаловать, <b>{message.from_user.first_name}</b>!\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
def show_admin_menu(message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("Добавить/Удалить клуб", callback_data="admin_clubs"),
        types.InlineKeyboardButton("Удалить комментарии", callback_data="admin_reviews")
    )
    keyboard.add(
        types.InlineKeyboardButton("Добавить/Удалить продукт", callback_data="admin_products")
    )
    bot.send_message(message.chat.id, "👮 Админ-меню:", reply_markup=keyboard)
def manage_clubs(message):
    text = message.text
    # Проверка, существует ли клуб
    cursor.execute("SELECT id FROM clubs WHERE name=%s", (text,))
    club = cursor.fetchone()
    if club:
        cursor.execute("DELETE FROM clubs WHERE id=%s", (club[0],))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Клуб '{text}' удалён.")
    else:
        cursor.execute("INSERT INTO clubs (name) VALUES (%s)", (text,))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Клуб '{text}' добавлен.") 
def delete_review(message):
    review_id = message.text
    try:
        review_id = int(review_id)
        cursor.execute("DELETE FROM reviews WHERE id=%s", (review_id,))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Комментарий {review_id} удалён.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректный ID комментария.")
def manage_products(message):
    text = message.text
    # Проверка, существует ли продукт
    cursor.execute("SELECT id FROM products WHERE name=%s", (text,))
    product = cursor.fetchone()
    if product:
        cursor.execute("DELETE FROM products WHERE id=%s", (product[0],))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Продукт '{text}' удалён.")
    else:
        # Для примера добавим продукт с минимальной информацией
        cursor.execute("INSERT INTO products (name, category, price) VALUES (%s,%s,%s)", (text, "Разное", 0))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Продукт '{text}' добавлен.")                   
@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_"))
def admin_callback_handler(callback):
    telegram_id = callback.from_user.id
    cursor.execute("SELECT id FROM admins WHERE telegram_id=%s", (telegram_id,))
    admin = cursor.fetchone()
    if not admin:
        bot.send_message(callback.message.chat.id, "❌ У вас нет прав администратора.")
        return

    # --- Управление клубами ---
    if callback.data == "admin_clubs":
        bot.send_message(callback.message.chat.id, "Введите название клуба для добавления или удаления:")
        bot.register_next_step_handler(callback.message, manage_clubs)

    # --- Управление отзывами ---
    elif callback.data == "admin_reviews":
        bot.send_message(callback.message.chat.id, "Введите ID комментария для удаления:")
        bot.register_next_step_handler(callback.message, delete_review)

    # --- Управление продуктами ---
    elif callback.data == "admin_products":
        bot.send_message(callback.message.chat.id, "Введите название продукта для добавления или удаления:")
        bot.register_next_step_handler(callback.message, manage_products)    
@bot.message_handler(commands=['adm'])
def admin_login(message):
    telegram_id = message.from_user.id
    cursor.execute("SELECT id FROM admins WHERE telegram_id=%s", (telegram_id,))
    admin = cursor.fetchone()
    if admin:
        show_admin_menu(message)
    else:
        bot.send_message(message.chat.id, "❌ У вас нет прав администратора.")
@bot.message_handler(commands=['start'])
def start(message):
    telegram_id = message.from_user.id
    cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
    user = cursor.fetchone()
    if user:
        show_main_menu(message)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        contact_button = types.KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)
        keyboard.add(contact_button)
        bot.send_message(
            message.chat.id,
            f"Привет, {message.from_user.first_name}! Похоже, вы не зарегистрированы.\n"
            "Для регистрации отправьте ваш номер телефона, нажав кнопку ниже:",
            reply_markup=keyboard
        )

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if message.contact is not None:
        phone = message.contact.phone_number
        telegram_id = message.from_user.id
        first_name = message.from_user.first_name
        username = message.from_user.username

        cursor.execute("""
            INSERT INTO users (telegram_id, first_name, username, phone)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (telegram_id) DO UPDATE SET phone=%s
        """, (telegram_id, first_name, username, phone, phone))
        conn.commit()
        bot.send_message(message.chat.id, "Спасибо! Ваш номер телефона сохранен.", reply_markup=types.ReplyKeyboardRemove())
        show_main_menu(message)

# --- Функция поиска ---
def perform_search(chat_id, query):
    results = []

    # Поиск по клубам
    cursor.execute("""
        SELECT id, name, category, description, schedule, price, level, instructor, address
        FROM clubs
        WHERE name ILIKE %s OR description ILIKE %s
    """, (f"%{query}%", f"%{query}%"))
    clubs = cursor.fetchall()
    for c in clubs:
        results.append(f"🏛 Клуб: {c[1]}\nКатегория: {c[2]}\nОписание: {c[3]}\nРасписание: {c[4]}\nЦена: {c[5]}\nУровень: {c[6]}\nПреподаватель: {c[7]}\nАдрес: {c[8]}")

    # Поиск по товарам
    cursor.execute("""
        SELECT id, name, category, club_category, price, description
        FROM products
        WHERE name ILIKE %s OR category ILIKE %s OR description ILIKE %s
    """, (f"%{query}%", f"%{query}%", f"%{query}%"))
    products = cursor.fetchall()
    for p in products:
        results.append(f"🛍 Товар: {p[1]}\nКатегория: {p[2]}\nПродаёт клуб категории: {p[3]}\nЦена: {p[4]}\nОписание: {p[5]}")

    if results:
        for res in results:
            bot.send_message(chat_id, res)
    else:
        bot.send_message(chat_id, "❌ По вашему запросу ничего не найдено.")

# --- Получение рекомендаций ---
def get_user_recommended_clubs(user_id):
    cursor.execute("""
        SELECT DISTINCT c.id, c.name, c.description, c.schedule, c.price, c.level, c.instructor, c.address
        FROM clubs c
        JOIN user_interests ui ON c.category = (
            SELECT i.name FROM interests i WHERE i.id = ui.interest_id
        )
        WHERE ui.user_id = %s
    """, (user_id,))
    return cursor.fetchall()

def get_user_recommended_products(user_id):
    cursor.execute("""
        SELECT p.id, p.name, p.category, p.club_category, p.price, p.description
        FROM products p
        WHERE p.club_category IN (
            SELECT c.category
            FROM clubs c
            JOIN user_interests ui ON ui.interest_id = (
                SELECT i.id FROM interests i WHERE i.name = c.category
            )
            WHERE ui.user_id = %s
        )
    """, (user_id,))
    return cursor.fetchall()


# --- Обработчик callback ---
@bot.callback_query_handler(func=lambda c: True)
def callback_handler(callback):
    telegram_id = callback.from_user.id

    # --- Уровень подготовки ---
    if callback.data == 'level':
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Выбрать уровень", callback_data="levelset"),
                     types.InlineKeyboardButton("Узнать уровень", callback_data="levelinfo"))
        bot.send_message(callback.message.chat.id, "Уровни:", reply_markup=keyboard)
    elif callback.data == 'levelset':
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Новичок", callback_data="level1"),
                     types.InlineKeyboardButton("Продвинутый", callback_data="level2"),
                     types.InlineKeyboardButton("Профи", callback_data="level3"))
        bot.send_message(callback.message.chat.id, "Выберите уровень подготовки:", reply_markup=keyboard)
    elif callback.data == 'levelinfo':
        cursor.execute("SELECT level FROM users WHERE telegram_id=%s", (telegram_id,))
        result = cursor.fetchone()
        if result and result[0]:
            bot.send_message(callback.message.chat.id, f"📊 Ваш текущий уровень: {result[0]}")
        else:
            bot.send_message(callback.message.chat.id, "❌ Уровень не установлен.")
    elif callback.data in ['level1', 'level2', 'level3']:
        level_map = {'level1': 'Новичок', 'level2': 'Продвинутый', 'level3': 'Профи'}
        chosen_level = level_map[callback.data]
        cursor.execute("UPDATE users SET level=%s WHERE telegram_id=%s", (chosen_level, telegram_id))
        conn.commit()
        bot.send_message(callback.message.chat.id, f"✅ Ваш уровень установлен: {chosen_level}")

    # --- Интересы ---
    elif callback.data == 'interes':
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Выбрать интересы", callback_data="intset"),
                     types.InlineKeyboardButton("Мои интересы", callback_data="intinfo"))
        bot.send_message(callback.message.chat.id, "Интересы", reply_markup=keyboard)
    elif callback.data.startswith("intset"):
        page = int(callback.data.split("_")[-1]) if callback.data.startswith("intset_page_") else 0
        show_interests_page(callback.message.chat.id, page)
    elif callback.data.startswith("interest_"):
        interest_id = int(callback.data.split("_")[-1])
        cursor.execute("SELECT id FROM users WHERE telegram_id=%s", (telegram_id,))
        result = cursor.fetchone()
        if result:
            user_id = result[0]
            cursor.execute("INSERT INTO user_interests (user_id, interest_id, telegram_id) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", (user_id, interest_id, telegram_id))
            conn.commit()
            bot.answer_callback_query(callback.id, "✅ Выбран интерес!")
    elif callback.data == 'intinfo':
        cursor.execute("""
            SELECT i.name FROM interests i
            JOIN user_interests ui ON i.id = ui.interest_id
            JOIN users u ON ui.user_id = u.id
            WHERE u.telegram_id=%s
        """, (telegram_id,))
        interests = cursor.fetchall()
        if interests:
            names = ', '.join([i[0] for i in interests])
            bot.send_message(callback.message.chat.id, f"Ваши интересы: {names}")
        else:
            bot.send_message(callback.message.chat.id, "Вы ещё не выбрали интересы.")

    # --- Рекомендации ---
    elif callback.data == 'recomends':
       cursor.execute("SELECT id FROM users WHERE telegram_id=%s", (telegram_id,))
       result = cursor.fetchone()
       if result:
           user_id = result[0]
           clubs = get_user_recommended_clubs(user_id)
           if not clubs:
               bot.send_message(callback.message.chat.id, "По вашим интересам пока ничего не найдено.")
               return
           for c in clubs:
               club_id = c[0]
               text = f"🏛 {c[1]} ({c[5]})\n{c[2]}\nРасписание: {c[3]}\nЦена: {c[4]}\nИнструктор: {c[6]}\nАдрес: {c[7]}"
               keyboard = types.InlineKeyboardMarkup()
               keyboard.add(
                   types.InlineKeyboardButton("✏️ Оставить отзыв", callback_data=f"leave_review_{club_id}"),
                   types.InlineKeyboardButton("📝 Просмотреть отзывы", callback_data=f"view_reviews_{club_id}")
               )
               bot.send_message(callback.message.chat.id, text, reply_markup=keyboard)

# --- Обработка кликов по кнопкам отзывов ---
    elif callback.data.startswith("leave_review_"):
       club_id = int(callback.data.split("_")[-1])
       cursor.execute("SELECT id FROM users WHERE telegram_id=%s", (telegram_id,))
       user_id = cursor.fetchone()[0]
       leave_review(callback.message.chat.id, user_id, club_id)

    elif callback.data.startswith("view_reviews_"):
       club_id = int(callback.data.split("_")[-1])
       view_reviews(callback.message.chat.id, club_id)



    # --- Записи ---
    elif callback.data == 'zap':
       cursor.execute("SELECT id FROM users WHERE telegram_id=%s", (telegram_id,))
       result = cursor.fetchone()
       if result:
           user_id = result[0]
           # Получаем записи пользователя
           cursor.execute("""
                SELECT cr.id, c.name, cr.selected_time, cr.status
                FROM club_registrations cr
                JOIN clubs c ON cr.club_id = c.id
                WHERE cr.user_id=%s
                ORDER BY cr.selected_time
           """, (user_id,))
           registrations = cursor.fetchall()
           if not registrations:
            bot.send_message(callback.message.chat.id, "У вас пока нет записей на кружки.")
           else:
              for r in registrations:
                  text = f"🏛 {r[1]}\nВремя: {r[2]}\nСтатус: {r[3]}"
                  bot.send_message(callback.message.chat.id, text)


    # --- Товары ---
    elif callback.data == 'atr':
    # Получаем id пользователя по telegram_id
        cursor.execute("SELECT id FROM users WHERE telegram_id=%s", (telegram_id,))
        result = cursor.fetchone()
        if result:
            user_id = result[0]
        # Получаем товары по интересам пользователя
            products = get_user_recommended_products(user_id)
            if products:
                for p in products:
                    text = f"🛍 {p[1]}\nКатегория: {p[2]}\nПродаёт клуб категории: {p[3]}\nЦена: {p[4]}\nОписание: {p[5]}"
                    bot.send_message(callback.message.chat.id, text)
            else:
                bot.send_message(callback.message.chat.id, "Список товаров по вашим интересам пуст.")
    
    # --- Поиск ---
    elif callback.data == 'find':
        msg = bot.send_message(callback.message.chat.id, "Введите ключевое слово для поиска:")
        bot.register_next_step_handler(msg, lambda m: perform_search(m.chat.id, m.text))

# --- Запуск бота ---
bot.polling(none_stop=True)
