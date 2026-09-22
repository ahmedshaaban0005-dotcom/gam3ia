from datetime import datetime
import os
from flask import Flask, redirect, render_template, request, session, url_for
import sqlite3

# إعداد التطبيق ومسار القوالب
template_dir = os.path.abspath('templates')
app = Flask(__name__, template_folder=template_dir)
app.secret_key = "agricoop_secret_key_2026"

def init_db():
    conn = sqlite3.connect("agricoop.db")
    cursor = conn.cursor()
    
    # جدول الحسابات وميزان المراجعة
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0
        )
    """)
    
    # جدول الحركات اليومية
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0
        )
    """)
    
    # جدول خدمات الأسمدة والتقاوي
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fertilizers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_name TEXT NOT NULL,
            item_type TEXT NOT NULL,
            quantity REAL NOT NULL,
            total_price REAL NOT NULL,
            date TEXT NOT NULL
        )
    """)
    
    # إضافة بيانات افتتاحية إذا كان الجدول فارغاً
    cursor.execute("SELECT COUNT(*) FROM accounts")
    if cursor.fetchone()[0] == 0:
        initial_accounts = [
            ("الأصول الثابتة (مباني وأراضي)", 4150547.74, 0.0),
            ("الخزينة (نقدية بالصندوق)", 22027.79, 0.0),
            ("أجور العاملين والمكافآت", 150000.00, 0.0),
            ("مصاريف إشراف الحصاد والخدمات", 85000.50, 0.0),
            ("أرصدة البنوك الجارية", 620000.00, 0.0),
            ("رأس المال", 0.0, 9842000.0),
            ("احتياطي قانوني وعام", 0.0, 450575.03),
        ]
        cursor.executemany(
            "INSERT INTO accounts (name, debit, credit) VALUES (?, ?, ?)",
            initial_accounts,
        )
        conn.commit()
        
    conn.close()

# تشغيل قاعدة البيانات عند بدء السيرفر
init_db()

@app.route("/")
def index():
    conn = sqlite3.connect("agricoop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, debit, credit FROM accounts")
    rows = cursor.fetchall()
    conn.close()

    accounts_list = []
    total_debit = 0.0
    total_credit = 0.0

    for row in rows:
        total_debit += row[2]
        total_credit += row[3]
        accounts_list.append({
            "id": row[0],
            "name": row[1],
            "debit": f"{row[2]:,.2f}" if row[2] > 0 else "-",
            "credit": f"{row[3]:,.2f}" if row[3] > 0 else "-",
        })

    return render_template(
        "index.html",
        accounts=accounts_list,
        total_debit=f"{total_debit:,.2f}",
        total_credit=f"{total_credit:,.2f}",
    )

@app.route("/clear_cookies")
def clear_cookies():
    session.clear()
    resp = redirect(url_for("index"))
    for cookie in request.cookies:
        resp.set_cookie(cookie, "", expires=0)
    return resp

@app.route("/add", methods=["POST"])
def add_account():
    name = request.form.get("account_name")
    debit = float(request.form.get("debit_amount") or 0.0)
    credit = float(request.form.get("credit_amount") or 0.0)

    if name:
        conn = sqlite3.connect("agricoop.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO accounts (name, debit, credit) VALUES (?, ?, ?)",
            (name, debit, credit),
        )
        conn.commit()
        conn.close()

    return redirect(url_for("index"))

@app.route("/edit/<int:acc_id>")
def edit_account(acc_id):
    conn = sqlite3.connect("agricoop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, debit, credit FROM accounts WHERE id = ?", (acc_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return redirect(url_for("index"))
        
    account = {
        "id": row[0],
        "name": row[1],
        "debit": row[2],
        "credit": row[3]
    }
    return render_template("edit_account.html", account=account)

@app.route("/update/<int:acc_id>", methods=["POST"])
def update_account(acc_id):
    name = request.form.get("account_name")
    debit = float(request.form.get("debit_amount") or 0.0)
    credit = float(request.form.get("credit_amount") or 0.0)

    if name:
        conn = sqlite3.connect("agricoop.db")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE accounts SET name = ?, debit = ?, credit = ? WHERE id = ?",
            (name, debit, credit, acc_id),
        )
        conn.commit()
        conn.close()

    return redirect(url_for("index"))

@app.route("/delete/<int:acc_id>")
def delete_account(acc_id):
    conn = sqlite3.connect("agricoop.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM accounts WHERE id = ?", (acc_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/assets_liabilities")
def assets_liabilities():
    conn = sqlite3.connect("agricoop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, debit, credit FROM accounts")
    rows = cursor.fetchall()
    conn.close()

    assets_list = []
    liabilities_list = []
    total_assets = 0.0
    total_liabilities = 0.0

    for row in rows:
        if "رأس المال" in row[1] or "احتياطي" in row[1] or row[3] > 0:
            total_liabilities += row[3]
            liabilities_list.append(
                {"id": row[0], "name": row[1], "amount": f"{row[3]:,.2f}"}
            )
        else:
            total_assets += row[2]
            assets_list.append(
                {"id": row[0], "name": row[1], "amount": f"{row[2]:,.2f}"}
            )

    return render_template(
        "assets_liabilities.html",
        assets=assets_list,
        liabilities=liabilities_list,
        total_assets=f"{total_assets:,.2f}",
        total_liabilities=f"{total_liabilities:,.2f}",
    )

@app.route("/fertilizers")
def fertilizers():
    conn = sqlite3.connect("agricoop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, farmer_name, item_type, quantity, total_price, date FROM fertilizers ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    fertilizers_list = []
    for row in rows:
        fertilizers_list.append({
            "id": row[0],
            "farmer_name": row[1],
            "item_type": row[2],
            "quantity": f"{row[3]:,.2f}",
            "total_price": f"{row[4]:,.2f}",
            "date": row[5],
        })

    return render_template("fertilizers.html", fertilizers=fertilizers_list)

@app.route("/add_fertilizer", methods=["POST"])
def add_fertilizer():
    farmer_name = request.form.get("farmer_name")
    item_type = request.form.get("item_type")
    quantity = float(request.form.get("quantity") or 0.0)
    total_price = float(request.form.get("total_price") or 0.0)
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    if farmer_name and item_type:
        conn = sqlite3.connect("agricoop.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO fertilizers (farmer_name, item_type, quantity, total_price, date) VALUES (?, ?, ?, ?, ?)",
            (farmer_name, item_type, quantity, total_price, date_str),
        )
        conn.commit()
        conn.close()

    return redirect(url_for("fertilizers"))

@app.route("/transaction")
def transaction():
    conn = sqlite3.connect("agricoop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, date, description, debit, credit FROM transactions ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    transactions_list = []
    for row in rows:
        transactions_list.append({
            "id": row[0],
            "date": row[1],
            "desc": row[2],
            "debit": f"{row[3]:,.2f}" if row[3] > 0 else "-",
            "credit": f"{row[4]:,.2f}" if row[4] > 0 else "-",
        })

    return render_template("transaction.html", transactions=transactions_list)

@app.route("/add_transaction", methods=["POST"])
def add_transaction():
    desc = request.form.get("description")
    debit = float(request.form.get("debit") or 0.0)
    credit = float(request.form.get("credit") or 0.0)
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    if desc:
        conn = sqlite3.connect("agricoop.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (date, description, debit, credit) VALUES (?, ?, ?, ?)",
            (date_str, desc, debit, credit),
        )
        cursor.execute(
            "INSERT INTO accounts (name, debit, credit) VALUES (?, ?, ?)",
            (desc, debit, credit),
        )
        conn.commit()
        conn.close()

    return redirect(url_for("transaction"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)