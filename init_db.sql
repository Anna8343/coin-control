CREATE TABLE IF NOT EXISTS categories (
    id                SERIAL PRIMARY KEY,
    name              VARCHAR(100) NOT NULL UNIQUE,
    color             VARCHAR(20)  NOT NULL DEFAULT '#6c757d',
    icon              VARCHAR(10)  NOT NULL DEFAULT '💰',
    transaction_count INTEGER      NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS accounts (
    id       SERIAL PRIMARY KEY,
    name     VARCHAR(100)  NOT NULL UNIQUE,
    currency VARCHAR(10)   NOT NULL DEFAULT 'UAH',
    balance  NUMERIC(12,2) NOT NULL DEFAULT 0,
    icon     VARCHAR(10)   NOT NULL DEFAULT '💳',
    color    VARCHAR(20)   NOT NULL DEFAULT '#378ADD'
);

CREATE TABLE IF NOT EXISTS transactions (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(255)  NOT NULL,
    amount      NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    currency    VARCHAR(10)   NOT NULL DEFAULT 'UAH',
    type        VARCHAR(10)   NOT NULL CHECK (type IN ('income','expense')),
    date        DATE          NOT NULL DEFAULT CURRENT_DATE,
    note        TEXT,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    account_id  INTEGER REFERENCES accounts(id)   ON DELETE SET NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION update_category_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.category_id IS NOT NULL THEN
        UPDATE categories SET transaction_count = transaction_count + 1 WHERE id = NEW.category_id;
    END IF;
    IF TG_OP = 'DELETE' AND OLD.category_id IS NOT NULL THEN
        UPDATE categories SET transaction_count = GREATEST(transaction_count - 1, 0) WHERE id = OLD.category_id;
    END IF;
    IF TG_OP = 'UPDATE' THEN
        IF OLD.category_id IS DISTINCT FROM NEW.category_id THEN
            IF OLD.category_id IS NOT NULL THEN
                UPDATE categories SET transaction_count = GREATEST(transaction_count - 1, 0) WHERE id = OLD.category_id;
            END IF;
            IF NEW.category_id IS NOT NULL THEN
                UPDATE categories SET transaction_count = transaction_count + 1 WHERE id = NEW.category_id;
            END IF;
        END IF;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_category_count ON transactions;
CREATE TRIGGER trigger_category_count
    AFTER INSERT OR UPDATE OR DELETE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_category_count();

INSERT INTO categories (name, color, icon) VALUES
    ('Зарплата',   '#3B6D11', '💵'),
    ('Їжа',        '#A32D2D', '🛒'),
    ('Краса',      '#993556', '✨'),
    ('Одяг',       '#534AB7', '👗'),
    ('Розваги',    '#854F0B', '🎵'),
    ('Транспорт',  '#185FA5', '🚌'),
    ('Здоров''я',  '#0F6E56', '💊'),
    ('Подорожі',   '#BA7517', '✈️')
ON CONFLICT (name) DO NOTHING;

INSERT INTO accounts (name, currency, balance, icon, color) VALUES
    ('Готівка',      'UAH', 8000,  '💵', '#3B6D11'),
    ('Картка',       'UAH', 42000, '💳', '#185FA5'),
    ('Заощадження',  'USD', 1500,  '🏦', '#854F0B')
ON CONFLICT (name) DO NOTHING;

INSERT INTO transactions (title, amount, currency, type, date, note, category_id, account_id) VALUES
    ('Зарплата за травень', 65000, 'UAH', 'income',  '2026-05-31', 'Основна зарплата',    (SELECT id FROM categories WHERE name='Зарплата'),  (SELECT id FROM accounts WHERE name='Картка')),
    ('Продукти',             5500, 'UAH', 'expense', '2026-06-01', NULL,                  (SELECT id FROM categories WHERE name='Їжа'),        (SELECT id FROM accounts WHERE name='Картка')),
    ('Салон краси',          6500, 'UAH', 'expense', '2026-06-01', 'Стрижка + манікюр',   (SELECT id FROM categories WHERE name='Краса'),      (SELECT id FROM accounts WHERE name='Готівка')),
    ('Одяг',                 8200, 'UAH', 'expense', '2026-06-02', 'Літній гардероб',      (SELECT id FROM categories WHERE name='Одяг'),       (SELECT id FROM accounts WHERE name='Картка')),
    ('Концерт + вечеря',     7800, 'UAH', 'expense', '2026-06-02', 'Вечір з друзями',      (SELECT id FROM categories WHERE name='Розваги'),    (SELECT id FROM accounts WHERE name='Готівка')),
    ('Транспорт',            4800, 'UAH', 'expense', '2026-06-03', 'Метро + таксі',        (SELECT id FROM categories WHERE name='Транспорт'),  (SELECT id FROM accounts WHERE name='Картка')),
    ('Авіаквитки',           4200, 'USD', 'expense', '2026-06-03', 'Літня відпустка',      (SELECT id FROM categories WHERE name='Подорожі'),   (SELECT id FROM accounts WHERE name='Заощадження'))
ON CONFLICT DO NOTHING;
