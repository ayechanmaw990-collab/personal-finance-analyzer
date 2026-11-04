
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = "finance-analyzer-local-key"

DATABASE = "finance.db"


# ==============================
# Database Connection
# ==============================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ==============================
# Initialize Database
# ==============================

def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            category TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            description TEXT,
            transaction_date TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ==============================
# Generate Last 6 Months
# ==============================

def get_last_six_months():
    today = date.today()

    months = []

    for i in range(5, -1, -1):
        year = today.year
        month = today.month - i

        while month <= 0:
            month += 12
            year -= 1

        month_key = f"{year}-{month:02d}"

        months.append(month_key)

    return months


# ==============================
# Dashboard
# ==============================

@app.route("/")
def index():

    conn = get_db()

    # All transactions
    transactions = conn.execute("""
        SELECT * FROM transactions
        ORDER BY transaction_date DESC, id DESC
    """).fetchall()

    # Total income
    income = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type = 'income'
    """).fetchone()[0]

    # Total expense
    expense = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type = 'expense'
    """).fetchone()[0]

    # Expense by category
    categories = conn.execute("""
        SELECT category, SUM(amount) AS total
        FROM transactions
        WHERE type = 'expense'
        GROUP BY category
        ORDER BY total DESC
    """).fetchall()

    # ==============================
    # Monthly Analysis
    # ==============================

    monthly_results = conn.execute("""
        SELECT
            strftime('%Y-%m', transaction_date) AS month,
            SUM(
                CASE
                    WHEN type = 'income' THEN amount
                    ELSE 0
                END
            ) AS monthly_income,
            SUM(
                CASE
                    WHEN type = 'expense' THEN amount
                    ELSE 0
                END
            ) AS monthly_expense

        FROM transactions

        WHERE transaction_date >= ?

        GROUP BY strftime('%Y-%m', transaction_date)

        ORDER BY month ASC
    """, (
        get_last_six_months()[0] + "-01",
    )).fetchall()

    conn.close()

    # Calculate balance
    balance = income - expense

    # Convert monthly results to dictionary
    monthly_dict = {
        row["month"]: row
        for row in monthly_results
    }

    # Prepare chart data
    monthly_labels = []
    monthly_income = []
    monthly_expense = []

    for month in get_last_six_months():

        monthly_labels.append(month)

        if month in monthly_dict:

            monthly_income.append(
                monthly_dict[month]["monthly_income"] or 0
            )

            monthly_expense.append(
                monthly_dict[month]["monthly_expense"] or 0
            )

        else:

            monthly_income.append(0)
            monthly_expense.append(0)

    # ==============================
    # Render Dashboard
    # ==============================

    return render_template(
        "index.html",

        transactions=transactions,

        income=income,
        expense=expense,
        balance=balance,

        categories=categories,

        monthly_labels=monthly_labels,
        monthly_income=monthly_income,
        monthly_expense=monthly_expense
    )


# ==============================
# Add Transaction
# ==============================

@app.route("/add", methods=["GET", "POST"])
def add_transaction():

    if request.method == "POST":

        transaction_type = request.form.get("type")
        category = request.form.get("category", "").strip()
        amount_text = request.form.get("amount", "").strip()
        description = request.form.get("description", "").strip()
        transaction_date = request.form.get("transaction_date")

        try:
            amount = float(amount_text)

        except ValueError:

            flash("金額を正しく入力してください。")
            return redirect(url_for("add_transaction"))

        if transaction_type not in ("income", "expense"):

            flash("種類を選択してください。")
            return redirect(url_for("add_transaction"))

        if not category or amount <= 0 or not transaction_date:

            flash("すべての必須項目を正しく入力してください。")
            return redirect(url_for("add_transaction"))

        try:
            date.fromisoformat(transaction_date)

        except ValueError:

            flash("日付を正しく入力してください。")
            return redirect(url_for("add_transaction"))

        conn = get_db()

        conn.execute("""
            INSERT INTO transactions
            (type, category, amount, description, transaction_date)
            VALUES (?, ?, ?, ?, ?)
        """, (
            transaction_type,
            category,
            amount,
            description,
            transaction_date
        ))

        conn.commit()
        conn.close()

        flash("取引を登録しました。")

        return redirect(url_for("index"))

    return render_template(
        "add_transaction.html",
        today=date.today().isoformat()
    )


# ==============================
# Delete Transaction
# ==============================

@app.route("/delete/<int:transaction_id>", methods=["POST"])
def delete_transaction(transaction_id):

    conn = get_db()

    conn.execute(
        "DELETE FROM transactions WHERE id = ?",
        (transaction_id,)
    )

    conn.commit()
    conn.close()

    flash("取引を削除しました。")

    return redirect(url_for("index"))


# ==============================
# Run Application
# ==============================

if __name__ == "__main__":

    init_db()

    app.run(debug=True)
