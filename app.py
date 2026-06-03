from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "coincontrol-secret")
DB_URL = os.getenv("DATABASE_URL", "postgresql://annamancenko@localhost:5434/coincontrol")


def get_db():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    return conn


@app.route("/")
def index():
    date_from = request.args.get("date_from", "")
    date_to   = request.args.get("date_to", "")

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    query = """
        SELECT t.id, t.title, t.amount, t.currency, t.type, t.date, t.note,
               c.name AS category_name, c.color AS category_color, c.icon AS category_icon,
               a.name AS account_name
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN accounts   a ON t.account_id  = a.id
        WHERE 1=1
    """
    params = []
    if date_from:
        query += " AND t.date >= %s"
        params.append(date_from)
    if date_to:
        query += " AND t.date <= %s"
        params.append(date_to)
    query += " ORDER BY t.date DESC, t.id DESC"

    cur.execute(query, params)
    transactions = cur.fetchall()

    cur.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='income'")
    total_income = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='expense'")
    total_expense = cur.fetchone()[0]
    balance = total_income - total_expense

    cur.execute("SELECT * FROM accounts ORDER BY name")
    accounts = cur.fetchall()
    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()

    cur.close(); conn.close()
    return render_template("index.html",
        transactions=transactions,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        accounts=accounts,
        categories=categories,
        date_from=date_from,
        date_to=date_to)


@app.route("/transactions/<int:id>")
def view_transaction(id):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT t.*, c.name AS category_name, c.color AS category_color,
               a.name AS account_name
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN accounts   a ON t.account_id  = a.id
        WHERE t.id = %s
    """, (id,))
    transaction = cur.fetchone()
    cur.close(); conn.close()
    if not transaction:
        flash("Transaction not found", "error")
        return redirect(url_for("index"))
    return render_template("transaction_detail.html", transaction=transaction)


@app.route("/transactions/new", methods=["GET", "POST"])
def new_transaction():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()
    cur.execute("SELECT * FROM accounts ORDER BY name")
    accounts = cur.fetchall()

    if request.method == "POST":
        title       = request.form.get("title", "").strip()
        amount      = request.form.get("amount", "").strip()
        currency    = request.form.get("currency", "UAH")
        type_       = request.form.get("type", "expense")
        date        = request.form.get("date", "").strip()
        note        = request.form.get("note", "").strip()
        category_id = request.form.get("category_id") or None
        account_id  = request.form.get("account_id") or None

        if not title or not amount or not date:
            flash("Title, amount and date are required", "error")
            cur.close(); conn.close()
            return render_template("transaction_form.html", transaction=None,
                                   categories=categories, accounts=accounts)
        try:
            amount = float(amount)
            cur.execute("""
                INSERT INTO transactions (title, amount, currency, type, date, note, category_id, account_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (title, amount, currency, type_, date, note, category_id, account_id))

            if account_id:
                delta = amount if type_ == "income" else -amount
                cur.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", (delta, account_id))

            conn.commit()
            flash("Transaction added!", "success")
            return redirect(url_for("index"))
        except Exception as e:
            conn.rollback()
            flash(f"Error: {e}", "error")
        finally:
            cur.close(); conn.close()
    else:
        cur.close(); conn.close()
    return render_template("transaction_form.html", transaction=None,
                           categories=categories, accounts=accounts)


@app.route("/transactions/<int:id>/edit", methods=["GET", "POST"])
def edit_transaction(id):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM transactions WHERE id = %s", (id,))
    transaction = cur.fetchone()
    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()
    cur.execute("SELECT * FROM accounts ORDER BY name")
    accounts = cur.fetchall()

    if not transaction:
        flash("Transaction not found", "error")
        cur.close(); conn.close()
        return redirect(url_for("index"))

    if request.method == "POST":
        title       = request.form.get("title", "").strip()
        amount      = request.form.get("amount", "").strip()
        currency    = request.form.get("currency", "UAH")
        type_       = request.form.get("type", "expense")
        date        = request.form.get("date", "").strip()
        note        = request.form.get("note", "").strip()
        category_id = request.form.get("category_id") or None
        account_id  = request.form.get("account_id") or None

        if not title or not amount or not date:
            flash("Title, amount and date are required", "error")
            cur.close(); conn.close()
            return render_template("transaction_form.html", transaction=transaction,
                                   categories=categories, accounts=accounts)
        try:
            amount         = float(amount)
            old_amount     = float(transaction["amount"])
            old_type       = transaction["type"]
            old_account_id = transaction["account_id"]

            if old_account_id:
                old_delta = old_amount if old_type == "income" else -old_amount
                cur.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s", (old_delta, old_account_id))

            cur.execute("""
                UPDATE transactions SET title=%s, amount=%s, currency=%s, type=%s,
                date=%s, note=%s, category_id=%s, account_id=%s WHERE id=%s
            """, (title, amount, currency, type_, date, note, category_id, account_id, id))

            if account_id:
                new_delta = amount if type_ == "income" else -amount
                cur.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", (new_delta, account_id))

            conn.commit()
            flash("Transaction updated!", "success")
            return redirect(url_for("view_transaction", id=id))
        except Exception as e:
            conn.rollback()
            flash(f"Error: {e}", "error")
        finally:
            cur.close(); conn.close()
    else:
        cur.close(); conn.close()
    return render_template("transaction_form.html", transaction=transaction,
                           categories=categories, accounts=accounts)


@app.route("/transactions/<int:id>/delete", methods=["POST"])
def delete_transaction(id):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT * FROM transactions WHERE id = %s", (id,))
        t = cur.fetchone()
        if t:
            if t["account_id"]:
                delta = float(t["amount"]) if t["type"] == "income" else -float(t["amount"])
                cur.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s", (delta, t["account_id"]))
            cur.execute("DELETE FROM transactions WHERE id = %s", (id,))
        conn.commit()
        flash("Transaction deleted", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "error")
    finally:
        cur.close(); conn.close()
    return redirect(url_for("index"))


@app.route("/accounts")
def accounts():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM accounts ORDER BY name")
    accounts = cur.fetchall()
    cur.close(); conn.close()
    return render_template("accounts.html", accounts=accounts)


@app.route("/accounts/new", methods=["GET", "POST"])
def new_account():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        currency = request.form.get("currency", "UAH")
        balance  = request.form.get("balance", "0").strip()
        icon     = request.form.get("icon", "💳").strip()
        color    = request.form.get("color", "#378ADD").strip()
        if not name:
            flash("Name is required", "error")
            return render_template("account_form.html", account=None)
        conn = get_db()
        cur  = conn.cursor()
        try:
            cur.execute("INSERT INTO accounts (name, currency, balance, icon, color) VALUES (%s,%s,%s,%s,%s)",
                        (name, currency, float(balance), icon, color))
            conn.commit()
            flash("Account created!", "success")
            return redirect(url_for("accounts"))
        except Exception as e:
            conn.rollback()
            flash(f"Error: {e}", "error")
        finally:
            cur.close(); conn.close()
    return render_template("account_form.html", account=None)


@app.route("/accounts/<int:id>/edit", methods=["GET", "POST"])
def edit_account(id):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM accounts WHERE id = %s", (id,))
    account = cur.fetchone()
    if not account:
        flash("Account not found", "error")
        cur.close(); conn.close()
        return redirect(url_for("accounts"))
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        currency = request.form.get("currency", "UAH")
        icon     = request.form.get("icon", "💳").strip()
        color    = request.form.get("color", "#378ADD").strip()
        try:
            cur.execute("UPDATE accounts SET name=%s, currency=%s, icon=%s, color=%s WHERE id=%s",
                        (name, currency, icon, color, id))
            conn.commit()
            flash("Account updated!", "success")
            return redirect(url_for("accounts"))
        except Exception as e:
            conn.rollback()
            flash(f"Error: {e}", "error")
        finally:
            cur.close(); conn.close()
    else:
        cur.close(); conn.close()
    return render_template("account_form.html", account=account)


@app.route("/accounts/<int:id>/delete", methods=["POST"])
def delete_account(id):
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("UPDATE transactions SET account_id = NULL WHERE account_id = %s", (id,))
        cur.execute("DELETE FROM accounts WHERE id = %s", (id,))
        conn.commit()
        flash("Account deleted", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "error")
    finally:
        cur.close(); conn.close()
    return redirect(url_for("accounts"))


@app.route("/categories")
def categories():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM categories ORDER BY name")
    cats = cur.fetchall()
    cur.close(); conn.close()
    return render_template("categories.html", categories=cats)


@app.route("/categories/new", methods=["GET", "POST"])
def new_category():
    if request.method == "POST":
        name  = request.form.get("name", "").strip()
        color = request.form.get("color", "#6c757d").strip()
        icon  = request.form.get("icon", "💰").strip()
        if not name:
            flash("Name is required", "error")
            return render_template("category_form.html", category=None)
        conn = get_db()
        cur  = conn.cursor()
        try:
            cur.execute("INSERT INTO categories (name, color, icon) VALUES (%s,%s,%s)", (name, color, icon))
            conn.commit()
            flash("Category created!", "success")
            return redirect(url_for("categories"))
        except psycopg2.IntegrityError:
            conn.rollback()
            flash("Category already exists", "error")
        finally:
            cur.close(); conn.close()
    return render_template("category_form.html", category=None)


@app.route("/categories/<int:id>/edit", methods=["GET", "POST"])
def edit_category(id):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM categories WHERE id = %s", (id,))
    category = cur.fetchone()
    if not category:
        flash("Category not found", "error")
        cur.close(); conn.close()
        return redirect(url_for("categories"))
    if request.method == "POST":
        name  = request.form.get("name", "").strip()
        color = request.form.get("color", "#6c757d").strip()
        icon  = request.form.get("icon", "💰").strip()
        try:
            cur.execute("UPDATE categories SET name=%s, color=%s, icon=%s WHERE id=%s", (name, color, icon, id))
            conn.commit()
            flash("Category updated!", "success")
            return redirect(url_for("categories"))
        except Exception as e:
            conn.rollback()
            flash(f"Error: {e}", "error")
        finally:
            cur.close(); conn.close()
    else:
        cur.close(); conn.close()
    return render_template("category_form.html", category=category)


@app.route("/categories/<int:id>/delete", methods=["POST"])
def delete_category(id):
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("UPDATE transactions SET category_id = NULL WHERE category_id = %s", (id,))
        cur.execute("DELETE FROM categories WHERE id = %s", (id,))
        conn.commit()
        flash("Category deleted", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "error")
    finally:
        cur.close(); conn.close()
    return redirect(url_for("categories"))


if __name__ == "__main__":
    app.run(debug=True)
