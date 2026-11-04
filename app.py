
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash
)
import sqlite3
from datetime import date, datetime
import math

app = Flask(__name__)
app.secret_key = "finance-analyzer-local-key"

DATABASE = "finance.db"


# ==================================
# Database Connection
# ==================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ==================================
# Initialize Database
# ==================================

def init_db():

    conn = get_db()

    # Transactions table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL
                CHECK(type IN ('income', 'expense')),
            category TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            description TEXT,
            transaction_date TEXT NOT NULL
        )
    """)

    # Monthly budget table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monthly_budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL UNIQUE,
            amount REAL NOT NULL CHECK(amount > 0)
        )
    """)

    # Category budget table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS category_budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            UNIQUE(month, category)
        )
    """)

    conn.commit()
    conn.close()


# Validate Month

def valid_month(month):

    try:
        datetime.strptime(month, "%Y-%m")
        return True

    except (ValueError, TypeError):
        return False



# Validate Amount


def valid_amount(amount_text):

    try:
        amount = float(amount_text)

        if not math.isfinite(amount) or amount <= 0:
            return None

        return amount

    except (ValueError, TypeError):
        return None


# Generate Last 6 Months

def get_last_six_months():

    today = date.today()
    months = []

    for i in range(5, -1, -1):

        year = today.year
        month = today.month - i

        while month <= 0:
            month += 12
            year -= 1

        months.append(f"{year}-{month:02d}")

    return months


# Dashboard

@app.route("/")
def index():

    conn = get_db()

    transactions = conn.execute("""
        SELECT *
        FROM transactions
        ORDER BY transaction_date DESC, id DESC
    """).fetchall()

    income = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type = 'income'
    """).fetchone()[0]

    expense = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type = 'expense'
    """).fetchone()[0]

    categories = conn.execute("""
        SELECT category, SUM(amount) AS total
        FROM transactions
        WHERE type = 'expense'
        GROUP BY category
        ORDER BY total DESC
    """).fetchall()

    # Monthly Analysis
    months = get_last_six_months()

    monthly_results = conn.execute("""
        SELECT
            strftime('%Y-%m', transaction_date) AS month,

            SUM(
                CASE WHEN type = 'income'
                THEN amount ELSE 0 END
            ) AS monthly_income,

            SUM(
                CASE WHEN type = 'expense'
                THEN amount ELSE 0 END
            ) AS monthly_expense

        FROM transactions

        WHERE transaction_date >= ?

        GROUP BY strftime('%Y-%m', transaction_date)

        ORDER BY month ASC
    """, (months[0] + "-01",)).fetchall()

    monthly_dict = {
        row["month"]: row
        for row in monthly_results
    }

    monthly_income = []
    monthly_expense = []

    for month in months:

        row = monthly_dict.get(month)

        monthly_income.append(
            row["monthly_income"] or 0 if row else 0
        )

        monthly_expense.append(
            row["monthly_expense"] or 0 if row else 0
        )

    # Current Month Budget
    current_month = date.today().strftime("%Y-%m")

    monthly_budget_row = conn.execute("""
        SELECT amount
        FROM monthly_budgets
        WHERE month = ?
    """, (current_month,)).fetchone()

    monthly_budget = (
        monthly_budget_row["amount"]
        if monthly_budget_row else 0
    )

    monthly_spent = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type = 'expense'
        AND substr(transaction_date, 1, 7) = ?
    """, (current_month,)).fetchone()[0]

    monthly_remaining = monthly_budget - monthly_spent

    monthly_percent = (
        monthly_spent / monthly_budget * 100
        if monthly_budget > 0 else 0
    )

    # Current Month Category Budgets
    category_budget_data = conn.execute("""
        SELECT
            cb.id,
            cb.category,
            cb.amount AS budget,
            COALESCE(SUM(t.amount), 0) AS spent

        FROM category_budgets cb

        LEFT JOIN transactions t
            ON t.category = cb.category
            AND t.type = 'expense'
            AND substr(t.transaction_date, 1, 7) = cb.month

        WHERE cb.month = ?

        GROUP BY cb.id, cb.category, cb.amount

        ORDER BY cb.category ASC
    """, (current_month,)).fetchall()

    conn.close()

    balance = income - expense

    return render_template(
        "index.html",

        transactions=transactions,

        income=income,
        expense=expense,
        balance=balance,

        categories=categories,

        monthly_labels=months,
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,

        current_month=current_month,
        monthly_budget=monthly_budget,
        monthly_spent=monthly_spent,
        monthly_remaining=monthly_remaining,
        monthly_percent=monthly_percent,

        category_budget_data=category_budget_data
    )


# Add Transaction

@app.route("/add", methods=["GET", "POST"])
def add_transaction():

    if request.method == "POST":

        transaction_type = request.form.get("type")
        category = request.form.get(
            "category", ""
        ).strip()

        amount = valid_amount(
            request.form.get("amount", "").strip()
        )

        description = request.form.get(
            "description", ""
        ).strip()

        transaction_date = request.form.get(
            "transaction_date"
        )

        if transaction_type not in ("income", "expense"):
            flash("種類を選択してください。")
            return redirect(url_for("add_transaction"))

        if not category or amount is None or not transaction_date:
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


# Delete Transaction

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


# Edit Transaction

@app.route("/edit/<int:transaction_id>", methods=["GET", "POST"])
def edit_transaction(transaction_id):

    conn = get_db()

    transaction = conn.execute("""
        SELECT *
        FROM transactions
        WHERE id = ?
    """, (transaction_id,)).fetchone()

    if transaction is None:
        conn.close()
        flash("取引が見つかりません。")
        return redirect(url_for("index"))

    if request.method == "POST":

        transaction_type = request.form.get("type")

        category = request.form.get(
            "category", ""
        ).strip()

        amount = valid_amount(
            request.form.get("amount", "").strip()
        )

        description = request.form.get(
            "description", ""
        ).strip()

        transaction_date = request.form.get(
            "transaction_date", ""
        )

        if transaction_type not in ("income", "expense"):
            conn.close()
            flash("種類を選択してください。")
            return redirect(
                url_for("edit_transaction", transaction_id=transaction_id)
            )

        if not category or amount is None or not transaction_date:
            conn.close()
            flash("すべての必須項目を正しく入力してください。")
            return redirect(
                url_for("edit_transaction", transaction_id=transaction_id)
            )

        try:
            date.fromisoformat(transaction_date)

        except ValueError:
            conn.close()
            flash("日付を正しく入力してください。")
            return redirect(
                url_for("edit_transaction", transaction_id=transaction_id)
            )

        conn.execute("""
            UPDATE transactions
            SET
                type = ?,
                category = ?,
                amount = ?,
                description = ?,
                transaction_date = ?
            WHERE id = ?
        """, (
            transaction_type,
            category,
            amount,
            description,
            transaction_date,
            transaction_id
        ))

        conn.commit()
        conn.close()

        flash("取引を更新しました。")

        return redirect(url_for("index"))

    conn.close()

    return render_template(
        "edit_transaction.html",
        transaction=transaction
    )




# Budget Page

@app.route("/budget", methods=["GET", "POST"])
def budget():

    current_month = date.today().strftime("%Y-%m")

    if request.method == "POST":

        action = request.form.get("action")
        selected_month = request.form.get("month", "")

        if not valid_month(selected_month):
            flash("年月を正しく選択してください。")
            return redirect(url_for("budget"))

        # Save Monthly Budget
        if action == "monthly":

            amount = valid_amount(
                request.form.get("amount", "").strip()
            )

            if amount is None:
                flash("Budget金額を正しく入力してください。")
                return redirect(url_for("budget", month=selected_month))

            conn = get_db()

            conn.execute("""
                INSERT INTO monthly_budgets (month, amount)
                VALUES (?, ?)
                ON CONFLICT(month)
                DO UPDATE SET amount = excluded.amount
            """, (selected_month, amount))

            conn.commit()
            conn.close()

            flash("月間Budgetを保存しました。")

        # Save Category Budget
        elif action == "category":

            category = request.form.get("category", "").strip()

            amount = valid_amount(
                request.form.get("amount", "").strip()
            )

            if not category or amount is None:
                flash("Categoryと金額を正しく入力してください。")
                return redirect(url_for("budget", month=selected_month))

            conn = get_db()

            conn.execute("""
                INSERT INTO category_budgets
                    (month, category, amount)
                VALUES (?, ?, ?)
                ON CONFLICT(month, category)
                DO UPDATE SET amount = excluded.amount
            """, (selected_month, category, amount))

            conn.commit()
            conn.close()

            flash("Category Budgetを保存しました。")

        else:
            flash("操作を確認してください。")

        return redirect(url_for("budget", month=selected_month))

    # GET request
    selected_month = request.args.get("month", current_month)

    if not valid_month(selected_month):
        selected_month = current_month

    conn = get_db()

    # Monthly Budget
    monthly_budget_row = conn.execute("""
        SELECT amount
        FROM monthly_budgets
        WHERE month = ?
    """, (selected_month,)).fetchone()

    monthly_budget = (
        monthly_budget_row["amount"]
        if monthly_budget_row else 0
    )

    # Monthly Expenses
    monthly_spent = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type = 'expense'
        AND substr(transaction_date, 1, 7) = ?
    """, (selected_month,)).fetchone()[0]

    # Category Budgets
    category_budgets = conn.execute("""
        SELECT
            cb.id,
            cb.category,
            cb.amount AS budget,
            COALESCE(SUM(t.amount), 0) AS spent

        FROM category_budgets cb

        LEFT JOIN transactions t
            ON LOWER(TRIM(t.category)) =
               LOWER(TRIM(cb.category))
            AND t.type = 'expense'
            AND substr(t.transaction_date, 1, 7) = cb.month

        WHERE cb.month = ?

        GROUP BY cb.id, cb.category, cb.amount

        ORDER BY cb.category ASC
    """, (selected_month,)).fetchall()

    conn.close()

    # Monthly Calculation
    monthly_remaining = monthly_budget - monthly_spent

    monthly_percent = (
        monthly_spent / monthly_budget * 100
        if monthly_budget > 0 else 0
    )

    # Category Calculation
    category_budget_list = []

    for item in category_budgets:

        budget_amount = item["budget"]
        spent_amount = item["spent"]

        remaining = budget_amount - spent_amount

        percent = (
            spent_amount / budget_amount * 100
            if budget_amount > 0 else 0
        )

        category_budget_list.append({
            "id": item["id"],
            "category": item["category"],
            "amount": budget_amount,
            "spent": spent_amount,
            "remaining": remaining,
            "percent": percent
        })

    return render_template(
        "budget.html",
        selected_month=selected_month,
        monthly_budget=monthly_budget,
        monthly_spent=monthly_spent,
        monthly_remaining=monthly_remaining,
        monthly_percent=monthly_percent,
        category_budgets=category_budget_list
    )


# ==================================
# Delete Category Budget
# ==================================

@app.route(
    "/budget/category/delete/<int:budget_id>",
    methods=["POST"]
)
def delete_category_budget(budget_id):

    selected_month = request.form.get("month", "")

    if not valid_month(selected_month):
        flash("年月が正しくありません。")
        return redirect(url_for("budget"))

    conn = get_db()

    conn.execute("""
        DELETE FROM category_budgets
        WHERE id = ?
    """, (budget_id,))

    conn.commit()
    conn.close()

    flash("Category Budgetを削除しました。")

    return redirect(url_for("budget", month=selected_month))



# Run Application


if __name__ == "__main__":

    init_db()

    app.run(debug=True)

# Run Application


if __name__ == "__main__":

    init_db()

    app.run(debug=True)
