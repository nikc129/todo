from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import time
from collections import defaultdict

app = Flask(__name__)   # <-- MOVE THIS UP

# Simple in-memory metrics
metrics = {
    "request_count": 0,
    "error_count": 0,
    "latency": []
}

@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def record_metrics(response):
    latency = time.time() - request.start_time

    metrics["request_count"] += 1
    metrics["latency"].append(latency)

    if response.status_code >= 500:
        metrics["error_count"] += 1

    return response

@app.route("/metrics")
def get_metrics():
    total = metrics["request_count"]
    errors = metrics["error_count"]

    avg_latency = sum(metrics["latency"]) / total if total else 0
    error_rate = (errors / total) if total else 0

    return {
        "total_requests": total,
        "error_count": errors,
        "error_rate": error_rate,
        "avg_latency_sec": avg_latency
    }

def get_db():
    conn = sqlite3.connect("todo.db")
    conn.row_factory = sqlite3.Row
    return conn

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