from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    flash
)

from flask_cors import CORS
from werkzeug.security import check_password_hash
from datetime import datetime
import os
import secrets

from database import get_db
from admin_routes import admin_bp
from student_routes import student_bp


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SESSION_SECRET",
    secrets.token_hex(32)
)

app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

CORS(app)


# ============================================================
# BLUEPRINTS
# ============================================================

app.register_blueprint(admin_bp)
app.register_blueprint(student_bp)


# ============================================================
# UPLOAD DIRECTORY
# ============================================================

try:
    os.makedirs(
        app.config["UPLOAD_FOLDER"],
        exist_ok=True
    )
except Exception:
    pass


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


# ============================================================
# ADMIN LOGIN
# ============================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Please enter username and password.", "error")
            return render_template("admin_login.html")

        try:

            db = get_db()

            response = (
                db.table("users")
                .select("*")
                .eq("username", username)
                .eq("role", "admin")
                .limit(1)
                .execute()
            )

            admin = (
                response.data[0]
                if response.data
                else None
            )

            if admin and check_password_hash(
                admin["password"],
                password
            ):

                session["user_id"] = admin["id"]
                session["username"] = admin["username"]
                session["role"] = "admin"

                return redirect(
                    url_for("admin_dashboard")
                )

            flash(
                "Invalid admin credentials.",
                "error"
            )

        except Exception as e:

            print("ADMIN LOGIN ERROR:", e)

            flash(
                "Unable to login. Please try again.",
                "error"
            )

    return render_template("admin_login.html")


# ============================================================
# STUDENT LOGIN
# ============================================================

@app.route("/student/login", methods=["GET", "POST"])
def student_login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:

            flash(
                "Please enter username and password.",
                "error"
            )

            return render_template(
                "student_login.html"
            )

        try:

            db = get_db()

            response = (
                db.table("users")
                .select("*")
                .eq("username", username)
                .eq("role", "student")
                .limit(1)
                .execute()
            )

            student = (
                response.data[0]
                if response.data
                else None
            )

            if student and check_password_hash(
                student["password"],
                password
            ):

                session["user_id"] = student["id"]
                session["username"] = student["username"]
                session["role"] = "student"

                return redirect(
                    url_for("student_dashboard")
                )

            flash(
                "Invalid student credentials.",
                "error"
            )

        except Exception as e:

            print("STUDENT LOGIN ERROR:", e)

            flash(
                "Unable to login. Please try again.",
                "error"
            )

    return render_template(
        "student_login.html"
    )


# ============================================================
# STUDENT REGISTER
# ============================================================

@app.route(
    "/student/register",
    methods=["GET", "POST"]
)
def student_register():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        email = request.form.get(
            "email",
            ""
        ).strip()

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        if not username or not password:

            flash(
                "Username and password are required.",
                "error"
            )

            return render_template(
                "student_register.html"
            )

        try:

            db = get_db()

            # ------------------------------------------------
            # Check username
            # ------------------------------------------------

            response = (
                db.table("users")
                .select("id")
                .eq(
                    "username",
                    username
                )
                .limit(1)
                .execute()
            )

            if response.data:

                flash(
                    "Username already exists.",
                    "error"
                )

                return render_template(
                    "student_register.html"
                )

            # ------------------------------------------------
            # Create student
            # ------------------------------------------------

            from werkzeug.security import (
                generate_password_hash
            )

            hashed_password = (
                generate_password_hash(password)
            )

            db.table("users").insert({

                "username": username,

                "password": hashed_password,

                "email": email,

                "full_name": full_name,

                "role": "student"

            }).execute()

            flash(
                "Registration successful! Please login.",
                "success"
            )

            return redirect(
                url_for("student_login")
            )

        except Exception as e:

            print(
                "STUDENT REGISTRATION ERROR:",
                e
            )

            flash(
                "Registration failed. Please try again.",
                "error"
            )

    return render_template(
        "student_register.html"
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin/dashboard")
def admin_dashboard():

    if session.get("role") != "admin":

        return redirect(
            url_for("admin_login")
        )

    try:

        db = get_db()

        response = (
            db.table("exams")
            .select("*")
            .order(
                "created_at",
                desc=True
            )
            .execute()
        )

        exams = response.data or []

    except Exception as e:

        print(
            "ADMIN DASHBOARD ERROR:",
            e
        )

        exams = []

        flash(
            "Unable to load exams.",
            "error"
        )

    return render_template(
        "admin_dashboard.html",
        exams=exams
    )


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@app.route("/student/dashboard")
def student_dashboard():

    if session.get("role") != "student":

        return redirect(
            url_for("student_login")
        )

    try:

        db = get_db()

        # ----------------------------------------------------
        # Active exams
        # ----------------------------------------------------

        exam_response = (
            db.table("exams")
            .select("*")
            .eq(
                "is_active",
                1
            )
            .order(
                "created_at",
                desc=True
            )
            .execute()
        )

        exams = exam_response.data or []

        available_exams = []

        # ----------------------------------------------------
        # Check previous attempts
        # ----------------------------------------------------

        for exam in exams:

            attempt_response = (
                db.table("student_attempts")
                .select("id")
                .eq(
                    "student_id",
                    session["user_id"]
                )
                .eq(
                    "exam_id",
                    exam["id"]
                )
                .limit(1)
                .execute()
            )

            if not attempt_response.data:

                available_exams.append(exam)

        # ----------------------------------------------------
        # Completed exams
        # ----------------------------------------------------

        attempt_response = (
            db.table("student_attempts")
            .select("*")
            .eq(
                "student_id",
                session["user_id"]
            )
            .order(
                "submitted_at",
                desc=True
            )
            .execute()
        )

        attempts = (
            attempt_response.data or []
        )

        completed = []

        for attempt in attempts:

            exam_response = (
                db.table("exams")
                .select("title")
                .eq(
                    "id",
                    attempt["exam_id"]
                )
                .limit(1)
                .execute()
            )

            exam = (
                exam_response.data[0]
                if exam_response.data
                else {}
            )

            completed.append({

                "title": exam.get(
                    "title",
                    "Unknown Exam"
                ),

                "score": attempt.get(
                    "score"
                ),

                "submitted_at": attempt.get(
                    "submitted_at"
                )

            })

    except Exception as e:

        print(
            "STUDENT DASHBOARD ERROR:",
            e
        )

        available_exams = []
        completed = []

        flash(
            "Unable to load dashboard.",
            "error"
        )

    return render_template(
        "student_dashboard.html",
        available_exams=available_exams,
        completed=completed
    )


# ============================================================
# DATETIME FILTER
# ============================================================

@app.template_filter("datetimeformat")
def datetimeformat(
    value,
    format="%H:%M:%S"
):

    if not value:
        return "-"

    try:

        if isinstance(value, datetime):

            dt = value

        elif isinstance(value, str):

            if "T" in value:

                dt = datetime.fromisoformat(
                    value.replace(
                        "Z",
                        "+00:00"
                    )
                )

            else:

                dt = datetime.strptime(
                    value,
                    "%Y-%m-%d %H:%M:%S"
                )

        else:

            return value

        return dt.strftime(format)

    except Exception:

        return value


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("index")
    )


# ============================================================
# VERCEL ENTRY POINT
# ============================================================

# IMPORTANT:
# Do NOT put the Flask app inside a function.
# Vercel needs this top-level variable:
#
# app = Flask(__name__)
#
# The variable already exists above.


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )