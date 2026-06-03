# Coin Control — Трекер особистих фінансів

Веб-застосунок для обліку особистих доходів та витрат з підтримкою мультивалютності та рахунків.

## Особливості

- Головна сторінка з підсумком доходів, витрат та балансу
- Підтримка кількох валют (UAH, USD, EUR)
- Рахунки (Готівка, Картка, Заощадження) з автоматичним оновленням балансу
- Список транзакцій з фільтром за датою
- Перегляд, створення, редагування та видалення транзакцій
- Управління категоріями з лічильником транзакцій
- AI-асистент на базі Gemini

## Структура бази даних

**categories** — `id`, `name`, `color`, `icon`, `transaction_count`

**accounts** — `id`, `name`, `currency`, `balance`, `icon`, `color`

**transactions** — `id`, `title`, `amount`, `currency`, `type`, `date`, `note`, `category_id`, `account_id`, `created_at`

## Реалізовано 

### Транзакція з rollback
Кожна операція запису виконується у блоці транзакції PostgreSQL. Якщо будь-який крок завершується помилкою — виконується `conn.rollback()` і жодні зміни не зберігаються.

### Тригер
`trigger_category_count` автоматично оновлює поле `transaction_count` у таблиці категорій при кожному INSERT, UPDATE або DELETE у таблиці транзакцій.

### AI-асистент 

У застосунку реалізовано сторінку з AI-асистентом на базі Gemini API. Користувач може написати будь-яке питання і отримати відповідь від нейромережі прямо у браузері.

## Опис файлів
cc_ukr/
├── app.py
├── init_db.sql
├── requirements.txt
├── .env
├── README.md
├── static/
│   └── style.css
└── templates/
├── base.html
├── index.html
├── transaction_detail.html
├── transaction_form.html
├── accounts.html
├── account_form.html
├── categories.html
└── category_form.html



## Покроковий запуск

### Крок 1 — Встановити PostgreSQL
Завантажити з https://postgresapp.com та запустити сервер на порту 5434.


### Крок 2 — Підключити і відправити
```bash
git remote add origin https://github.com/Anna8343/coin-control.git
git branch -M main
git push -u origin main
```

### Крок 3 — Створити базу даних
```bash
/Applications/Postgres.app/Contents/Versions/18/bin/psql -p 5434 -c "CREATE DATABASE coincontrol;"
```

### Крок 4 —Заповнити базу даних
```bash
/Applications/Postgres.app/Contents/Versions/18/bin/psql -p 5434 -d coincontrol -f init_db.sql
```

### Крок 5 — Налаштувати файл .env
Відкрити файл `.env` і вписати:

Open in browser: **http://127.0.0.1:5000**


