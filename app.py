from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import time
import threading
import boto3

app = Flask(__name__)

# CloudWatch client
cloudwatch = boto3.client('cloudwatch', region_name='ap-south-1')

# Metrics storage
metrics = {
    "request_count": 0,
    "error_count": 0,
    "total_latency": 0.0
}

# ------------------- REQUEST TRACKING -------------------

@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def record_metrics(response):
    latency = time.time() - request.start_time

    metrics["request_count"] += 1
    metrics["total_latency"] += latency

    if response.status_code >= 500:
        metrics["error_count"] += 1

    return response

# ------------------- METRICS ENDPOINT -------------------

@app.route("/metrics")
def get_metrics():
    total = metrics["request_count"]
    errors = metrics["error_count"]

    avg_latency = metrics["total_latency"] / total if total else 0
    error_rate = (errors / total) if total else 0

    return {
        "total_requests": total,
        "error_count": errors,
        "error_rate": error_rate,
        "avg_latency_sec": avg_latency
    }

# ------------------- CLOUDWATCH PUSH -------------------

def push_metrics():
    while True:
        time.sleep(10)  # push every 10 seconds

        total = metrics["request_count"]
        errors = metrics["error_count"]
        avg_latency = metrics["total_latency"] / total if total else 0

        try:
            cloudwatch.put_metric_data(
                Namespace='TodoApp',
                MetricData=[
                    {
                        'MetricName': 'RequestCount',
                        'Value': total,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'ErrorCount',
                        'Value': errors,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'Latency',
                        'Value': avg_latency,
                        'Unit': 'Seconds'
                    }
                ]
            )
            print("Metrics pushed to CloudWatch")

        except Exception as e:
            print("CloudWatch Error:", e)

# Start background thread
threading.Thread(target=push_metrics, daemon=True).start()

# ------------------- DATABASE -------------------

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

# ------------------- ROUTES -------------------

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

# ------------------- RUN -------------------

if __name__ == "__main__":
    app.run(debug=True)