"""ACEest Fitness & Gym - Flask Web Application (v3.2.4)"""

import os
import sqlite3
from datetime import datetime, date
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB_NAME = os.environ.get("DB_NAME", "aceest_fitness.db")
APP_VERSION = os.environ.get("APP_VERSION", "3.2.4")

PROGRAMS = {
    "Fat Loss (FL) - 3 day": {"factor": 22, "desc": "3-day full-body fat loss"},
    "Fat Loss (FL) - 5 day": {"factor": 24, "desc": "5-day split, higher volume fat loss"},
    "Muscle Gain (MG) - PPL": {"factor": 35, "desc": "Push/Pull/Legs hypertrophy"},
    "Beginner (BG)": {"factor": 26, "desc": "3-day simple beginner full-body"},
}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT UNIQUE NOT NULL,
            age              INTEGER,
            height           REAL,
            weight           REAL,
            program          TEXT,
            calories         INTEGER,
            target_weight    REAL,
            target_adherence INTEGER,
            membership_status TEXT DEFAULT 'Active',
            membership_end   TEXT
        );

        CREATE TABLE IF NOT EXISTS progress (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            week        TEXT NOT NULL,
            adherence   INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS workouts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name  TEXT NOT NULL,
            date         TEXT NOT NULL,
            workout_type TEXT NOT NULL,
            duration_min INTEGER,
            notes        TEXT
        );

        CREATE TABLE IF NOT EXISTS exercises (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER NOT NULL,
            name       TEXT NOT NULL,
            sets       INTEGER,
            reps       INTEGER,
            weight     REAL
        );

        CREATE TABLE IF NOT EXISTS metrics (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            date        TEXT NOT NULL,
            weight      REAL,
            waist       REAL,
            bodyfat     REAL
        );
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def calculate_bmi(weight_kg: float, height_cm: float) -> dict:
    if height_cm <= 0 or weight_kg <= 0:
        return {}
    h_m = height_cm / 100.0
    bmi = round(weight_kg / (h_m * h_m), 1)
    if bmi < 18.5:
        category, risk = "Underweight", "Potential nutrient deficiency"
    elif bmi < 25:
        category, risk = "Normal", "Low risk"
    elif bmi < 30:
        category, risk = "Overweight", "Moderate risk"
    else:
        category, risk = "Obese", "Higher risk; prioritise fat loss"
    return {"bmi": bmi, "category": category, "risk": risk}


def calculate_calories(weight_kg: float, program: str) -> int | None:
    prog = PROGRAMS.get(program)
    if not prog or not weight_kg:
        return None
    return int(weight_kg * prog["factor"])


# ---------------------------------------------------------------------------
# Routes – health & info
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return jsonify({
        "app": "ACEest Fitness & Gym",
        "version": APP_VERSION,
        "status": "running",
        "endpoints": [
            "GET  /health",
            "GET  /programs",
            "POST /clients",
            "GET  /clients",
            "GET  /clients/<name>",
            "PUT  /clients/<name>",
            "DELETE /clients/<name>",
            "POST /clients/<name>/progress",
            "GET  /clients/<name>/progress",
            "POST /clients/<name>/workouts",
            "GET  /clients/<name>/workouts",
            "POST /clients/<name>/metrics",
            "GET  /clients/<name>/metrics",
            "GET  /clients/<name>/bmi",
        ],
    })


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "version": APP_VERSION})


@app.route("/programs")
def programs():
    return jsonify(PROGRAMS)


# ---------------------------------------------------------------------------
# Client CRUD
# ---------------------------------------------------------------------------

@app.route("/clients", methods=["POST"])
def create_client():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    program = data.get("program", "")
    weight = data.get("weight")
    calories = calculate_calories(weight, program) if weight else None

    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO clients
               (name, age, height, weight, program, calories,
                target_weight, target_adherence, membership_status, membership_end)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                name,
                data.get("age"),
                data.get("height"),
                weight,
                program,
                calories,
                data.get("target_weight"),
                data.get("target_adherence"),
                data.get("membership_status", "Active"),
                data.get("membership_end"),
            ),
        )
        conn.commit()
        return jsonify({"message": "Client created", "name": name, "calories": calories}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Client already exists"}), 409
    finally:
        conn.close()


@app.route("/clients", methods=["GET"])
def list_clients():
    conn = get_db()
    rows = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/clients/<name>", methods=["GET"])
def get_client(name: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Client not found"}), 404
    return jsonify(dict(row))


@app.route("/clients/<name>", methods=["PUT"])
def update_client(name: str):
    data = request.get_json(force=True)
    conn = get_db()
    row = conn.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Client not found"}), 404

    current = dict(row)
    weight = data.get("weight", current["weight"])
    program = data.get("program", current["program"])
    calories = calculate_calories(weight, program) if weight else current["calories"]

    conn.execute(
        """UPDATE clients SET age=?, height=?, weight=?, program=?, calories=?,
           target_weight=?, target_adherence=?, membership_status=?, membership_end=?
           WHERE name=?""",
        (
            data.get("age", current["age"]),
            data.get("height", current["height"]),
            weight,
            program,
            calories,
            data.get("target_weight", current["target_weight"]),
            data.get("target_adherence", current["target_adherence"]),
            data.get("membership_status", current["membership_status"]),
            data.get("membership_end", current["membership_end"]),
            name,
        ),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Client updated", "name": name, "calories": calories})


@app.route("/clients/<name>", methods=["DELETE"])
def delete_client(name: str):
    conn = get_db()
    row = conn.execute("SELECT id FROM clients WHERE name=?", (name,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Client not found"}), 404
    conn.execute("DELETE FROM clients WHERE name=?", (name,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Client '{name}' deleted"})


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------

@app.route("/clients/<name>/progress", methods=["POST"])
def add_progress(name: str):
    data = request.get_json(force=True)
    adherence = data.get("adherence")
    if adherence is None:
        return jsonify({"error": "adherence is required"}), 400
    if not (0 <= int(adherence) <= 100):
        return jsonify({"error": "adherence must be 0-100"}), 400

    week = data.get("week", datetime.now().strftime("Week %U - %Y"))
    conn = get_db()
    conn.execute(
        "INSERT INTO progress (client_name, week, adherence) VALUES (?,?,?)",
        (name, week, int(adherence)),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Progress logged", "week": week, "adherence": adherence}), 201


@app.route("/clients/<name>/progress", methods=["GET"])
def get_progress(name: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT week, adherence FROM progress WHERE client_name=? ORDER BY id",
        (name,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ---------------------------------------------------------------------------
# Workouts
# ---------------------------------------------------------------------------

@app.route("/clients/<name>/workouts", methods=["POST"])
def add_workout(name: str):
    data = request.get_json(force=True)
    workout_date = data.get("date", date.today().isoformat())
    workout_type = data.get("workout_type", "")
    if not workout_type:
        return jsonify({"error": "workout_type is required"}), 400

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO workouts (client_name, date, workout_type, duration_min, notes) VALUES (?,?,?,?,?)",
        (name, workout_date, workout_type, data.get("duration_min", 60), data.get("notes", "")),
    )
    workout_id = cur.lastrowid

    for ex in data.get("exercises", []):
        conn.execute(
            "INSERT INTO exercises (workout_id, name, sets, reps, weight) VALUES (?,?,?,?,?)",
            (workout_id, ex.get("name"), ex.get("sets"), ex.get("reps"), ex.get("weight")),
        )
    conn.commit()
    conn.close()
    return jsonify({"message": "Workout logged", "workout_id": workout_id}), 201


@app.route("/clients/<name>/workouts", methods=["GET"])
def get_workouts(name: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, date, workout_type, duration_min, notes FROM workouts WHERE client_name=? ORDER BY date DESC",
        (name,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ---------------------------------------------------------------------------
# Body metrics
# ---------------------------------------------------------------------------

@app.route("/clients/<name>/metrics", methods=["POST"])
def add_metrics(name: str):
    data = request.get_json(force=True)
    metric_date = data.get("date", date.today().isoformat())
    conn = get_db()
    conn.execute(
        "INSERT INTO metrics (client_name, date, weight, waist, bodyfat) VALUES (?,?,?,?,?)",
        (name, metric_date, data.get("weight"), data.get("waist"), data.get("bodyfat")),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Metrics logged"}), 201


@app.route("/clients/<name>/metrics", methods=["GET"])
def get_metrics(name: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT date, weight, waist, bodyfat FROM metrics WHERE client_name=? ORDER BY date",
        (name,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ---------------------------------------------------------------------------
# BMI
# ---------------------------------------------------------------------------

@app.route("/clients/<name>/bmi", methods=["GET"])
def get_bmi(name: str):
    conn = get_db()
    row = conn.execute("SELECT weight, height FROM clients WHERE name=?", (name,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Client not found"}), 404
    result = calculate_bmi(row["weight"] or 0, row["height"] or 0)
    if not result:
        return jsonify({"error": "Insufficient data for BMI calculation"}), 400
    return jsonify(result)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
