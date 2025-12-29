# Telegram Bot "Clubs and Products"

This Telegram bot allows users to choose interests, get club and product recommendations, leave and view reviews, and manage their registrations. The bot also includes an admin panel for managing clubs, reviews, and products.

---

## Features

### For Users:
- Registration via phone number.
- Selecting skill level (Beginner, Advanced, Pro).
- Choosing and viewing interests.
- Receiving recommendations for clubs and products based on interests.
- Leaving and viewing reviews for clubs.
- Viewing registrations for clubs.
- Searching for clubs and products.

### For Administrators:
- Adding and removing clubs.
- Deleting reviews.
- Adding and removing products.

---

## Requirements

- Python 3.8+
- PostgreSQL
- Python packages:
  ```
  pip install pyTelegramBotAPI psycopg2
  ```

---

## Database Setup

1. Create a PostgreSQL database:

```sql
CREATE DATABASE postgres;
```

2. Create necessary tables:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE,
    first_name TEXT,
    username TEXT,
    phone TEXT,
    level TEXT
);

CREATE TABLE admins (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE
);

CREATE TABLE interests (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE
);

CREATE TABLE user_interests (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    interest_id INT REFERENCES interests(id),
    telegram_id BIGINT,
    UNIQUE(user_id, interest_id)
);

CREATE TABLE clubs (
    id SERIAL PRIMARY KEY,
    name TEXT,
    category TEXT,
    description TEXT,
    schedule TEXT,
    price TEXT,
    level TEXT,
    instructor TEXT,
    address TEXT
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT,
    category TEXT,
    club_category TEXT,
    price TEXT,
    description TEXT
);

CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    club_id INT REFERENCES clubs(id),
    rating INT,
    comment TEXT,
    created_at TIMESTAMP,
    status TEXT
);

CREATE TABLE club_registrations (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    club_id INT REFERENCES clubs(id),
    selected_time TIMESTAMP,
    status TEXT
);
```

---

## Bot Setup

1. Obtain a bot token from [BotFather](https://t.me/BotFather).
2. Replace the token in `bot.py`:

```python
bot = telebot.TeleBot('YOUR_TOKEN')
```

3. Configure PostgreSQL connection:

```python
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="postgres",
    host="localhost",
    port=5432
)
```

---

## Running the Bot

Run the bot with:

```bash
python bot.py
```

The bot will start polling and handle messages continuously.

---

## Admin Panel

- Command `/adm` checks if the user is an admin.
- Admins can:
  - Add or remove clubs.
  - Delete reviews.
  - Add or remove products.

---

## Notes

- Pagination is implemented for selecting interests.
- Reviews check for rating input between 1 and 5.
- Recommendations are generated based on user interests.
- Search works for both clubs and products.

---

## Libraries

- [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) for Telegram bot functionality.
- [psycopg2](https://www.psycopg.org/) for PostgreSQL connection.

