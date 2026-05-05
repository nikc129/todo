from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect("todo.db")
    conn.row_factory = sqlite3.Row
    return conn

# Create table if not exists
def init_db():
    with get_db() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            completed INTEGER DEFAULT 0
        )
        """)

init_db()

@app.route("/")
def index():
    db = get_db()
    tasks = db.execute("SELECT * FROM tasks").fetchall()
    return render_template("index.html", tasks=tasks)

@app.route("/add", methods=["POST"])
def add():
    content = request.form["content"]
    if content:
        db = get_db()
        db.execute("INSERT INTO tasks (content) VALUES (?)", (content,))
        db.commit()
    return redirect(url_for("index"))

@app.route("/complete/<int:id>")
def complete(id):
    db = get_db()
    db.execute("UPDATE tasks SET completed = NOT completed WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("index"))

@app.route("/delete/<int:id>")
def delete(id):
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)