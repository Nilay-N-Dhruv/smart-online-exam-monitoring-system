from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    flash,
    send_file
)

import os
import openpyxl

from werkzeug.utils import secure_filename
from openpyxl.styles import Font
from datetime import datetime

from database import get_db


# ============================================================
# BLUEPRINT
# ============================================================

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)


# ============================================================
# CONFIGURATION
# ============================================================

UPLOAD_FOLDER = "/tmp/uploads"

ALLOWED_EXTENSIONS = {
    "xlsx",
    "xls"
}


# ============================================================
# FILE CHECK
# ============================================================

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ============================================================
# ADMIN AUTHENTICATION HELPER
# ============================================================

def admin_required():

    return session.get("role") == "admin"


# ============================================================
# CREATE EXAM
# ============================================================

@admin_bp.route(
    "/create-exam",
    methods=["GET", "POST"]
)
def create_exam():

    # --------------------------------------------------------
    # Check admin login
    # --------------------------------------------------------

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    if request.method == "GET":

        return render_template(
            "admin/create_exam.html"
        )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    title = (
        request.form.get("title") or ""
    ).strip()

    description = (
        request.form.get("description") or ""
    ).strip()

    duration = (
        request.form.get("duration_minutes") or ""
    ).strip()

    passing_score = (
        request.form.get("passing_score") or ""
    ).strip()

    # --------------------------------------------------------
    # Validate title
    # --------------------------------------------------------

    if not title:

        flash(
            "Exam title is required.",
            "error"
        )

        return redirect(
            request.url
        )

    # --------------------------------------------------------
    # Validate duration
    # --------------------------------------------------------

    try:

        duration_value = int(duration)

        if duration_value <= 0:

            raise ValueError

    except (ValueError, TypeError):

        flash(
            "Duration must be a valid positive number.",
            "error"
        )

        return redirect(
            request.url
        )

    # --------------------------------------------------------
    # Validate passing score
    # --------------------------------------------------------

    passing_score_value = None

    if passing_score:

        try:

            passing_score_value = float(
                passing_score
            )

            if passing_score_value < 0:

                raise ValueError

        except (ValueError, TypeError):

            flash(
                "Passing score must be a valid number.",
                "error"
            )

            return redirect(
                request.url
            )

    # --------------------------------------------------------
    # Database
    # --------------------------------------------------------

    try:

        db = get_db()

        response = (
            db.table("exams")
            .insert({
                "title": title,
                "description": description,
                "duration_minutes": duration_value,
                "passing_score": passing_score_value,
                "is_active": True
            })
            .execute()
        )

        # ----------------------------------------------------
        # Check response
        # ----------------------------------------------------

        if not response.data:

            flash(
                "Could not create exam.",
                "error"
            )

            return redirect(
                request.url
            )

        exam_id = response.data[0]["id"]

        flash(
            "Exam created successfully!",
            "success"
        )

        return redirect(
            url_for(
                "admin.upload_questions",
                exam_id=exam_id
            )
        )

    except Exception as e:

        print(
            "CREATE EXAM ERROR:",
            repr(e)
        )

        flash(
            f"Database error: {str(e)}",
            "error"
        )

        return redirect(
            request.url
        )


# ============================================================
# UPLOAD QUESTIONS
# ============================================================

@admin_bp.route(
    "/upload-questions/<int:exam_id>",
    methods=["GET", "POST"]
)
def upload_questions(exam_id):

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )

    # --------------------------------------------------------
    # Make sure temporary upload directory exists
    # --------------------------------------------------------

    try:

        os.makedirs(
            UPLOAD_FOLDER,
            exist_ok=True
        )

    except Exception as e:

        print(
            "UPLOAD DIRECTORY ERROR:",
            repr(e)
        )

    db = get_db()

    # --------------------------------------------------------
    # Get exam
    # --------------------------------------------------------

    try:

        exam_response = (
            db.table("exams")
            .select("*")
            .eq("id", exam_id)
            .limit(1)
            .execute()
        )

    except Exception as e:

        print(
            "EXAM FETCH ERROR:",
            repr(e)
        )

        return (
            "Database error while loading exam.",
            500
        )

    exam = (
        exam_response.data[0]
        if exam_response.data
        else None
    )

    if not exam:

        return (
            "Exam not found",
            404
        )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    if request.method == "GET":

        return render_template(
            "admin/upload_questions.html",
            exam=exam
        )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if "file" not in request.files:

        flash(
            "No file uploaded.",
            "error"
        )

        return redirect(
            request.url
        )

    file = request.files["file"]

    if not file or file.filename == "":

        flash(
            "No file selected.",
            "error"
        )

        return redirect(
            request.url
        )

    if not allowed_file(file.filename):

        flash(
            "Only Excel files (.xlsx, .xls) are allowed!",
            "error"
        )

        return redirect(
            request.url
        )

    filename = secure_filename(
        file.filename
    )

    filepath = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    try:

        # ----------------------------------------------------
        # Save file
        # ----------------------------------------------------

        file.save(filepath)

        # ----------------------------------------------------
        # Open workbook
        # ----------------------------------------------------

        workbook = openpyxl.load_workbook(
            filepath,
            read_only=True,
            data_only=True
        )

        sheet = workbook.active

        questions = []

        # ----------------------------------------------------
        # Read rows
        # ----------------------------------------------------

        for row in sheet.iter_rows(
            min_row=2,
            values_only=True
        ):

            if not row:
                continue

            if len(row) < 6:
                continue

            if row[0] is None:
                continue

            question_text = str(
                row[0]
            ).strip()

            if not question_text:
                continue

            option_a = (
                str(row[1]).strip()
                if row[1] is not None
                else ""
            )

            option_b = (
                str(row[2]).strip()
                if row[2] is not None
                else ""
            )

            option_c = (
                str(row[3]).strip()
                if row[3] is not None
                else ""
            )

            option_d = (
                str(row[4]).strip()
                if row[4] is not None
                else ""
            )

            correct_answer = (
                str(row[5]).strip().upper()
                if row[5] is not None
                else ""
            )

            # ------------------------------------------------
            # Validate answer
            # ------------------------------------------------

            if correct_answer not in {
                "A",
                "B",
                "C",
                "D"
            }:

                correct_answer = "A"

            questions.append({

                "exam_id": exam_id,

                "question_text":
                    question_text,

                "option_a":
                    option_a,

                "option_b":
                    option_b,

                "option_c":
                    option_c,

                "option_d":
                    option_d,

                "correct_answer":
                    correct_answer,

                "marks": 1

            })

        workbook.close()

        # ----------------------------------------------------
        # Check questions
        # ----------------------------------------------------

        if not questions:

            flash(
                "No valid questions found in Excel file.",
                "error"
            )

            return redirect(
                request.url
            )

        # ----------------------------------------------------
        # Insert questions
        # ----------------------------------------------------

        response = (
            db.table("questions")
            .insert(questions)
            .execute()
        )

        if not response.data:

            flash(
                "Questions could not be inserted.",
                "error"
            )

            return redirect(
                request.url
            )

        flash(
            f"{len(questions)} questions successfully uploaded!",
            "success"
        )

        return redirect(
            url_for(
                "admin.view_results",
                exam_id=exam_id
            )
        )

    except Exception as e:

        print(
            "QUESTION UPLOAD ERROR:",
            repr(e)
        )

        flash(
            f"Error processing file: {str(e)}",
            "error"
        )

        return redirect(
            request.url
        )

    finally:

        # ----------------------------------------------------
        # Remove temporary file
        # ----------------------------------------------------

        if os.path.exists(filepath):

            try:

                os.remove(filepath)

            except Exception as e:

                print(
                    "TEMP FILE DELETE ERROR:",
                    repr(e)
                )


# ============================================================
# VIEW RESULTS
# ============================================================

@admin_bp.route(
    "/view-results/<int:exam_id>"
)
def view_results(exam_id):

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )

    db = get_db()

    # --------------------------------------------------------
    # Exam
    # --------------------------------------------------------

    exam_response = (
        db.table("exams")
        .select("*")
        .eq("id", exam_id)
        .limit(1)
        .execute()
    )

    exam = (
        exam_response.data[0]
        if exam_response.data
        else None
    )

    if not exam:

        return (
            "Exam not found",
            404
        )

    # --------------------------------------------------------
    # Attempts
    # --------------------------------------------------------

    attempt_response = (
        db.table("student_attempts")
        .select("*")
        .eq("exam_id", exam_id)
        .in_(
            "status",
            [
                "completed",
                "terminated"
            ]
        )
        .order(
            "submitted_at",
            desc=True
        )
        .execute()
    )

    attempts = (
        attempt_response.data
        or []
    )

    results = []

    for attempt in attempts:

        user_response = (
            db.table("users")
            .select(
                "username,full_name"
            )
            .eq(
                "id",
                attempt["student_id"]
            )
            .limit(1)
            .execute()
        )

        user = (
            user_response.data[0]
            if user_response.data
            else {}
        )

        result = dict(attempt)

        result["username"] = user.get(
            "username"
        )

        result["full_name"] = user.get(
            "full_name"
        )

        results.append(result)

    return render_template(
        "admin/view_results.html",
        exam=exam,
        results=results
    )


# ============================================================
# VIEW LOGS
# ============================================================

@admin_bp.route(
    "/view-logs/<int:attempt_id>"
)
def view_logs(attempt_id):

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )

    db = get_db()

    # --------------------------------------------------------
    # Attempt
    # --------------------------------------------------------

    attempt_response = (
        db.table("student_attempts")
        .select("*")
        .eq("id", attempt_id)
        .limit(1)
        .execute()
    )

    if not attempt_response.data:

        return (
            "Attempt not found",
            404
        )

    attempt = attempt_response.data[0]

    # --------------------------------------------------------
    # Student
    # --------------------------------------------------------

    user_response = (
        db.table("users")
        .select(
            "username,full_name"
        )
        .eq(
            "id",
            attempt["student_id"]
        )
        .limit(1)
        .execute()
    )

    user = (
        user_response.data[0]
        if user_response.data
        else {}
    )

    # --------------------------------------------------------
    # Exam
    # --------------------------------------------------------

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

    attempt["username"] = user.get(
        "username"
    )

    attempt["full_name"] = user.get(
        "full_name"
    )

    attempt["title"] = exam.get(
        "title"
    )

    # --------------------------------------------------------
    # Monitoring logs
    # --------------------------------------------------------

    logs_response = (
        db.table("monitoring_logs")
        .select("*")
        .eq(
            "attempt_id",
            attempt_id
        )
        .order(
            "timestamp",
            desc=False
        )
        .execute()
    )

    logs = (
        logs_response.data
        or []
    )

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    report_response = (
        db.table("exam_reports")
        .select("*")
        .eq(
            "attempt_id",
            attempt_id
        )
        .order(
            "timestamp",
            desc=True
        )
        .limit(1)
        .execute()
    )

    report = (
        report_response.data[0]
        if report_response.data
        else None
    )

    # --------------------------------------------------------
    # Time calculation
    # --------------------------------------------------------

    start_time = None
    end_time = None

    total_seconds = 0
    total_minutes = 0

    warning_logs = []

    def parse_time(ts):

        if not ts:
            return None

        try:

            if isinstance(ts, datetime):

                return ts

            return datetime.fromisoformat(
                str(ts).replace(
                    "Z",
                    "+00:00"
                )
            )

        except Exception:

            try:

                return datetime.strptime(
                    str(ts),
                    "%Y-%m-%d %H:%M:%S"
                )

            except Exception:

                return None

    if logs:

        start_time = parse_time(
            logs[0].get("timestamp")
        )

        end_time = parse_time(
            logs[-1].get("timestamp")
        )

        if start_time and end_time:

            try:

                total_seconds = max(
                    0,
                    round(
                        (
                            end_time
                            - start_time
                        ).total_seconds()
                    )
                )

                total_minutes = round(
                    total_seconds / 60,
                    1
                )

            except Exception:

                total_seconds = 0
                total_minutes = 0

        warning_logs = [

            log

            for log in logs

            if log.get(
                "warning_issued"
            ) in (
                1,
                True,
                "1",
                "true",
                "True"
            )

        ]

    return render_template(
        "admin/view_logs.html",
        attempt=attempt,
        logs=logs,
        warning_logs=warning_logs,
        report=report,
        total_seconds=total_seconds,
        total_minutes=total_minutes,
        start_time=start_time,
        end_time=end_time
    )


# ============================================================
# DELETE EXAM
# ============================================================

@admin_bp.route(
    "/delete-exam/<int:exam_id>"
)
def delete_exam(exam_id):

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )

    db = get_db()

    try:

        # ----------------------------------------------------
        # Get attempts
        # ----------------------------------------------------

        attempt_response = (
            db.table("student_attempts")
            .select("id")
            .eq("exam_id", exam_id)
            .execute()
        )

        attempts = (
            attempt_response.data
            or []
        )

        attempt_ids = [
            attempt["id"]
            for attempt in attempts
        ]

        # ----------------------------------------------------
        # Delete reports/logs
        # ----------------------------------------------------

        for attempt_id in attempt_ids:

            (
                db.table("exam_reports")
                .delete()
                .eq(
                    "attempt_id",
                    attempt_id
                )
                .execute()
            )

            (
                db.table("monitoring_logs")
                .delete()
                .eq(
                    "attempt_id",
                    attempt_id
                )
                .execute()
            )

        # ----------------------------------------------------
        # Delete attempts
        # ----------------------------------------------------

        (
            db.table("student_attempts")
            .delete()
            .eq(
                "exam_id",
                exam_id
            )
            .execute()
        )

        # ----------------------------------------------------
        # Delete questions
        # ----------------------------------------------------

        (
            db.table("questions")
            .delete()
            .eq(
                "exam_id",
                exam_id
            )
            .execute()
        )

        # ----------------------------------------------------
        # Delete exam
        # ----------------------------------------------------

        (
            db.table("exams")
            .delete()
            .eq(
                "id",
                exam_id
            )
            .execute()
        )

        flash(
            "Exam deleted successfully.",
            "success"
        )

    except Exception as e:

        print(
            "DELETE EXAM ERROR:",
            repr(e)
        )

        flash(
            f"Could not delete exam: {str(e)}",
            "error"
        )

    return redirect(
        url_for("admin_dashboard")
    )


# ============================================================
# EXPORT MONITORING
# ============================================================

@admin_bp.route(
    "/export-monitoring/<int:attempt_id>"
)
def export_monitoring(attempt_id):

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )

    db = get_db()

    try:

        response = (
            db.table("monitoring_logs")
            .select("*")
            .eq(
                "attempt_id",
                attempt_id
            )
            .order(
                "id",
                desc=False
            )
            .execute()
        )

        logs = (
            response.data
            or []
        )

        # ----------------------------------------------------
        # Create workbook
        # ----------------------------------------------------

        workbook = openpyxl.Workbook()

        sheet = workbook.active

        sheet.title = "Monitoring Logs"

        headers = [

            "ID",
            "Attempt ID",
            "Event Type",
            "Face Detected",
            "Gaze Direction",
            "Head Pose",
            "Warning Issued",
            "Details",
            "Timestamp"

        ]

        sheet.append(headers)

        # ----------------------------------------------------
        # Header style
        # ----------------------------------------------------

        for cell in sheet[1]:

            cell.font = Font(
                bold=True
            )

        # ----------------------------------------------------
        # Data
        # ----------------------------------------------------

        for log in logs:

            sheet.append([

                log.get("id"),

                log.get(
                    "attempt_id"
                ),

                log.get(
                    "event_type"
                ),

                log.get(
                    "face_detected"
                ),

                log.get(
                    "gaze_direction"
                ),

                log.get(
                    "head_pose"
                ),

                log.get(
                    "warning_issued"
                ),

                log.get(
                    "details"
                ),

                log.get(
                    "timestamp"
                )

            ])

        # ----------------------------------------------------
        # Temporary Vercel file
        # ----------------------------------------------------

        filename = (
            f"/tmp/monitoring_attempt_"
            f"{attempt_id}.xlsx"
        )

        workbook.save(filename)

        return send_file(
            filename,
            as_attachment=True,
            download_name=(
                f"monitoring_attempt_"
                f"{attempt_id}.xlsx"
            ),
            mimetype=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            )
        )

    except Exception as e:

        print(
            "EXPORT ERROR:",
            repr(e)
        )

        return (
            f"Could not export monitoring logs: {str(e)}",
            500
        )