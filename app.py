from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "ultimate_scheduler_secret_key"

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

DATABASE = "scheduler.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(DATABASE):
        conn = get_db_connection()
        schema_path = os.path.join(os.path.dirname(__file__),"schema.sql")
        with open("schema.sql") as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()

init_db()

# ---------------- AUTH ----------------

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
            conn.commit()
            flash("Registration successful!")
            return redirect(url_for("login"))
        except:
            flash("Email already exists!")
        finally:
            conn.close()

    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    tasks = conn.execute("SELECT * FROM tasks WHERE user_id=?", (session["user_id"],)).fetchall()
    conn.close()

    return render_template("dashboard.html", tasks=tasks)

@app.route("/add_task", methods=["POST"])
def add_task():
    if "user_id" not in session:
        return redirect(url_for("login"))

    title = request.form["title"]
    priority = request.form["priority"]
    due_date = request.form["due_date"]

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO tasks (user_id, title, priority, due_date, status) VALUES (?, ?, ?, ?, ?)",
        (session["user_id"], title, priority, due_date, "Pending")
    )
    conn.commit()
    conn.close()

    flash("Task added successfully")
    return redirect(url_for("dashboard"))

@app.route("/toggle_status/<int:task_id>")
def toggle_status(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    task = conn.execute("SELECT status FROM tasks WHERE id=? AND user_id=?", 
                        (task_id, session["user_id"])).fetchone()

    if task:
        new_status = "Completed" if task["status"] == "Pending" else "Pending"
        conn.execute("UPDATE tasks SET status=? WHERE id=?", (new_status, task_id))
        conn.commit()

    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/delete_task/<int:task_id>")
def delete_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    conn.execute("DELETE FROM tasks WHERE id=? AND user_id=?", 
                 (task_id, session["user_id"]))
    conn.commit()
    conn.close()

    flash("Task deleted")
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0",port=port)
