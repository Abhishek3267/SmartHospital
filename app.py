from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import uuid
from pathlib import Path
from datetime import date

app = Flask(__name__)
app.secret_key = "smart-hospital-demo-secret-key"

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "hospital.db"

DEPARTMENTS = [
    "Cardiology",
    "Orthopedics",
    "General Medicine",
    "Neurology"
]


def get_db():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id TEXT UNIQUE NOT NULL,
                patient_name TEXT NOT NULL,
                department TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


@app.route("/")
def home():
    return render_template(
        "index.html",
        departments=DEPARTMENTS,
        today=date.today().isoformat()
    )


@app.route("/book", methods=["POST"])
def book_appointment():
    patient_name = request.form.get("patient_name", "").strip()
    department = request.form.get("department", "").strip()
    appointment_date = request.form.get("appointment_date", "").strip()

    if not patient_name or len(patient_name) > 100:
        flash("Please enter a valid patient name.")
        return redirect(url_for("home") + "#booking")

    if department not in DEPARTMENTS:
        flash("Please select a valid department.")
        return redirect(url_for("home") + "#booking")

    try:
        selected_date = date.fromisoformat(appointment_date)

        if selected_date < date.today():
            flash("Please select today or a future date.")
            return redirect(url_for("home") + "#booking")

    except ValueError:
        flash("Please select a valid appointment date.")
        return redirect(url_for("home") + "#booking")

    booking_id = "SH-" + uuid.uuid4().hex[:10].upper()

    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO appointments (
                    booking_id,
                    patient_name,
                    department,
                    appointment_date
                )
                VALUES (?, ?, ?, ?)
            """, (
                booking_id,
                patient_name,
                department,
                appointment_date
            ))

        flash(f"Appointment booked! Booking ID: {booking_id}")

    except sqlite3.Error:
        app.logger.exception("Database booking error.")
        flash("Booking failed. Please try again.")

    return redirect(url_for("home") + "#booking")


@app.route("/search", methods=["GET", "POST"])
def search_appointment():
    appointment = None
    searched = False

    if request.method == "POST":
        searched = True
        booking_id = request.form.get(
            "booking_id", ""
        ).strip().upper()

        if booking_id:
            with get_db() as conn:
                appointment = conn.execute("""
                    SELECT booking_id, patient_name,
                           department, appointment_date
                    FROM appointments
                    WHERE booking_id = ?
                """, (booking_id,)).fetchone()

    return render_template(
        "search.html",
        appointment=appointment,
        searched=searched
    )


@app.route("/admin")
def admin_dashboard():
    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM appointments"
        ).fetchone()[0]

        department_stats = conn.execute("""
            SELECT department, COUNT(*) AS total
            FROM appointments
            GROUP BY department
            ORDER BY total DESC
        """).fetchall()

        appointments = conn.execute("""
            SELECT booking_id, patient_name,
                   department, appointment_date
            FROM appointments
            ORDER BY appointment_date DESC, id DESC
        """).fetchall()

    return render_template(
        "admin.html",
        total=total,
        department_stats=department_stats,
        appointments=appointments
    )


@app.route("/health")
def health():
    try:
        with get_db() as conn:
            conn.execute("SELECT 1")

        return {
            "status": "healthy",
            "application": "Smart Hospital",
            "database": "connected"
        }, 200

    except sqlite3.Error:
        app.logger.exception("Database health check failed.")

        return {
            "status": "unhealthy",
            "database": "disconnected"
        }, 503


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)