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

# Vercel serverless functions can write only to /tmp
UPLOAD_FOLDER = "/tmp/uploads"

ALLOWED_EXTENSIONS = {
    "xlsx",
    "xls"
}


# ============================================================
# FILE CHECK
# ============================================================

def allowed_file(filename):

    if not filename:
        return False

    if "." not in filename:
        return False

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    return extension in ALLOWED_EXTENSIONS


# ============================================================
# ADMIN AUTHENTICATION
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
    # Check admin
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

    try:

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        duration_value = request.form.get(
            "duration_minutes",
            ""
        ).strip()

        passing_score_value = request.form.get(
            "passing_score",
            ""
        ).strip()

        # ----------------------------------------------------
        # Validate title
        # ----------------------------------------------------

        if not title:

            flash(
                "Exam title is required.",
                "error"
            )

            return redirect(
                url_for("admin.create_exam")
            )

        # ----------------------------------------------------
        # Validate duration
        # ----------------------------------------------------

        if not duration_value:

            flash(
                "Duration is required.",
                "error"
            )

            return redirect(
                url_for("admin.create_exam")
            )

        try:

            duration = int(
                duration_value
            )

        except ValueError:

            flash(
                "Duration must be a valid number.",
                "error"
            )

            return redirect(
                url_for("admin.create_exam")
            )

        if duration <= 0:

            flash(
                "Duration must be greater than 0.",
                "error"
            )

            return redirect(
                url_for("admin.create_exam")
            )

        # ----------------------------------------------------
        # Validate passing score
        # ----------------------------------------------------

        if not passing_score_value:

            flash(
                "Passing score is required.",
                "error"
            )

            return redirect(
                url_for("admin.create_exam")
            )

        try:

            passing_score = float(
                passing_score_value
            )

        except ValueError:

            flash(
                "Passing score must be a valid number.",
                "error"
            )

            return redirect(
                url_for("admin.create_exam")
            )

        if (
            passing_score < 0
            or passing_score > 100
        ):

            flash(
                "Passing score must be between 0 and 100.",
                "error"
            )

            return redirect(
                url_for("admin.create_exam")
            )

        # ----------------------------------------------------
        # Database
        # ----------------------------------------------------

        db = get_db()

        print("========================================")
        print("CREATE EXAM")
        print("Title:", title)
        print("Duration:", duration)
        print("Passing Score:", passing_score)
        print("========================================")

        response = (
            db.table("exams")
            .insert({

                "title": title,

                "description":
                    description,

                "duration_minutes":
                    duration,

                "passing_score":
                    passing_score,

                "is_active":
                    True

            })
            .execute()
        )

        # ----------------------------------------------------
        # Check response
        # ----------------------------------------------------

        if not response.data:

            print(
                "CREATE EXAM: EMPTY DATABASE RESPONSE"
            )

            flash(
                "Exam could not be created.",
                "error"
            )

            return redirect(
                url_for("admin.create_exam")
            )

        exam_id = response.data[0].get(
            "id"
        )

        if not exam_id:

            print(
                "CREATE EXAM: ID NOT FOUND"
            )

            flash(
                "Exam was created but ID was not returned.",
                "error"
            )

            return redirect(
                url_for("admin_dashboard")
            )

        print(
            "Exam created successfully:",
            exam_id
        )

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

        print("========================================")
        print("CREATE EXAM ERROR")
        print(repr(e))
        print("========================================")

        flash(
            f"Could not create exam: {str(e)}",
            "error"
        )

        return redirect(
            url_for("admin.create_exam")
        )


# ============================================================
# UPLOAD QUESTIONS
# ============================================================

@admin_bp.route(
    "/upload-questions/<int:exam_id>",
    methods=["GET", "POST"]
)
def upload_questions(exam_id):

    # --------------------------------------------------------
    # Check admin
    # --------------------------------------------------------

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )

    # --------------------------------------------------------
    # Create temporary directory
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
            .eq(
                "id",
                exam_id
            )
            .limit(1)
            .execute()
        )

        exam = (
            exam_response.data[0]
            if exam_response.data
            else None
        )

    except Exception as e:

        print(
            "EXAM FETCH ERROR:",
            repr(e)
        )

        flash(
            f"Could not load exam: {str(e)}",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
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
    # POST - Check file
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

    if not file:

        flash(
            "Invalid file.",
            "error"
        )

        return redirect(
            request.url
        )

    if not file.filename:

        flash(
            "No file selected.",
            "error"
        )

        return redirect(
            request.url
        )

    # --------------------------------------------------------
    # Validate extension
    # --------------------------------------------------------

    if not allowed_file(
        file.filename
    ):

        flash(
            "Only Excel files (.xlsx and .xls) are allowed.",
            "error"
        )

        return redirect(
            request.url
        )

    # --------------------------------------------------------
    # Secure filename
    # --------------------------------------------------------

    filename = secure_filename(
        file.filename
    )

    # Prevent filename collision
    timestamp = datetime.utcnow().strftime(
        "%Y%m%d%H%M%S%f"
    )

    filename = (
        f"{timestamp}_{filename}"
    )

    filepath = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    try:

        # ----------------------------------------------------
        # Save uploaded file
        # ----------------------------------------------------

        file.save(
            filepath
        )

        print(
            "Excel file saved:",
            filepath
        )

        # ----------------------------------------------------
        # Open Excel workbook
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
        #
        # Excel format:
        #
        # A = Question
        # B = Option A
        # C = Option B
        # D = Option C
        # E = Option D
        # F = Correct Answer
        #
        # First row = header
        # ----------------------------------------------------

        for row in sheet.iter_rows(
            min_row=2,
            values_only=True
        ):

            if not row:
                continue

            if len(row) < 6:
                continue

            # Question
            if row[0] is None:
                continue

            question_text = str(
                row[0]
            ).strip()

            if not question_text:
                continue

            # ------------------------------------------------
            # Options
            # ------------------------------------------------

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

            # ------------------------------------------------
            # Correct answer
            # ------------------------------------------------

            correct_answer = (
                str(row[5])
                .strip()
                .upper()
                if row[5] is not None
                else ""
            )

            if correct_answer not in {
                "A",
                "B",
                "C",
                "D"
            }:

                print(
                    "Invalid answer found:",
                    correct_answer
                )

                correct_answer = "A"

            # ------------------------------------------------
            # Question object
            # ------------------------------------------------

            questions.append({

                "exam_id":
                    exam_id,

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

                "marks":
                    1

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

        print(
            "Questions found:",
            len(questions)
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
                "Questions could not be inserted into database.",
                "error"
            )

            return redirect(
                request.url
            )

        print(
            "Questions inserted:",
            len(response.data)
        )

        flash(
            f"{len(questions)} questions successfully uploaded!",
            "success"
        )

        # ----------------------------------------------------
        # Go to results
        # ----------------------------------------------------

        return redirect(
            url_for(
                "admin.view_results",
                exam_id=exam_id
            )
        )

    except Exception as e:

        print("========================================")
        print("QUESTION UPLOAD ERROR")
        print(repr(e))
        print("========================================")

        flash(
            f"Error processing Excel file: {str(e)}",
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

                os.remove(
                    filepath
                )

                print(
                    "Temporary file removed."
                )

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

    try:

        # ----------------------------------------------------
        # Get exam
        # ----------------------------------------------------

        exam_response = (
            db.table("exams")
            .select("*")
            .eq(
                "id",
                exam_id
            )
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

        # ----------------------------------------------------
        # Get attempts
        # ----------------------------------------------------

        attempt_response = (
            db.table("student_attempts")
            .select("*")
            .eq(
                "exam_id",
                exam_id
            )
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

        # ----------------------------------------------------
        # Get students
        # ----------------------------------------------------

        for attempt in attempts:

            user_response = (
                db.table("users")
                .select(
                    "username,full_name"
                )
                .eq(
                    "id",
                    attempt.get(
                        "student_id"
                    )
                )
                .limit(1)
                .execute()
            )

            user = (
                user_response.data[0]
                if user_response.data
                else {}
            )

            result = dict(
                attempt
            )

            result["username"] = (
                user.get("username")
            )

            result["full_name"] = (
                user.get("full_name")
            )

            results.append(
                result
            )

        return render_template(
            "admin/view_results.html",
            exam=exam,
            results=results
        )

    except Exception as e:

        print("VIEW RESULTS ERROR:")
        print(repr(e))

        return (
            f"Could not load results: {str(e)}",
            500
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

    try:

        # ----------------------------------------------------
        # Attempt
        # ----------------------------------------------------

        attempt_response = (
            db.table("student_attempts")
            .select("*")
            .eq(
                "id",
                attempt_id
            )
            .limit(1)
            .execute()
        )

        if not attempt_response.data:

            return (
                "Attempt not found",
                404
            )

        attempt = (
            attempt_response.data[0]
        )

        # ----------------------------------------------------
        # Student
        # ----------------------------------------------------

        user_response = (
            db.table("users")
            .select(
                "username,full_name"
            )
            .eq(
                "id",
                attempt.get(
                    "student_id"
                )
            )
            .limit(1)
            .execute()
        )

        user = (
            user_response.data[0]
            if user_response.data
            else {}
        )

        # ----------------------------------------------------
        # Exam
        # ----------------------------------------------------

        exam_response = (
            db.table("exams")
            .select("title")
            .eq(
                "id",
                attempt.get(
                    "exam_id"
                )
            )
            .limit(1)
            .execute()
        )

        exam = (
            exam_response.data[0]
            if exam_response.data
            else {}
        )

        attempt["username"] = (
            user.get("username")
        )

        attempt["full_name"] = (
            user.get("full_name")
        )

        attempt["title"] = (
            exam.get("title")
        )

        # ----------------------------------------------------
        # Monitoring logs
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Report
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Time calculation
        # ----------------------------------------------------

        start_time = None
        end_time = None

        total_seconds = 0
        total_minutes = 0

        warning_logs = []

        def parse_time(ts):

            if not ts:
                return None

            try:

                if isinstance(
                    ts,
                    datetime
                ):

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

        # ----------------------------------------------------
        # Logs available
        # ----------------------------------------------------

        if logs:

            start_time = parse_time(
                logs[0].get(
                    "timestamp"
                )
            )

            end_time = parse_time(
                logs[-1].get(
                    "timestamp"
                )
            )

            if (
                start_time
                and end_time
            ):

                try:

                    # Handle timezone mismatch
                    if (
                        start_time.tzinfo
                        and not end_time.tzinfo
                    ):

                        end_time = end_time.replace(
                            tzinfo=start_time.tzinfo
                        )

                    elif (
                        end_time.tzinfo
                        and not start_time.tzinfo
                    ):

                        start_time = start_time.replace(
                            tzinfo=end_time.tzinfo
                        )

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

                except Exception as e:

                    print(
                        "TIME CALCULATION ERROR:",
                        repr(e)
                    )

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

    except Exception as e:

        print("========================================")
        print("VIEW LOGS ERROR")
        print(repr(e))
        print("========================================")

        return (
            f"Could not load monitoring logs: {str(e)}",
            500
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
        # Check exam
        # ----------------------------------------------------

        exam_response = (
            db.table("exams")
            .select("id")
            .eq(
                "id",
                exam_id
            )
            .limit(1)
            .execute()
        )

        if not exam_response.data:

            flash(
                "Exam not found.",
                "error"
            )

            return redirect(
                url_for("admin_dashboard")
            )

        # ----------------------------------------------------
        # Get attempts
        # ----------------------------------------------------

        attempt_response = (
            db.table("student_attempts")
            .select("id")
            .eq(
                "exam_id",
                exam_id
            )
            .execute()
        )

        attempts = (
            attempt_response.data
            or []
        )

        attempt_ids = [

            attempt.get("id")

            for attempt in attempts

            if attempt.get("id") is not None

        ]

        # ----------------------------------------------------
        # Delete reports and logs
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

        print("========================================")
        print("DELETE EXAM ERROR")
        print(repr(e))
        print("========================================")

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

        # ----------------------------------------------------
        # Get monitoring logs
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Headers
        # ----------------------------------------------------

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

        sheet.append(
            headers
        )

        # ----------------------------------------------------
        # Header style
        # ----------------------------------------------------

        for cell in sheet[1]:

            cell.font = Font(
                bold=True
            )

        # ----------------------------------------------------
        # Add data
        # ----------------------------------------------------

        for log in logs:

            sheet.append([

                log.get(
                    "id"
                ),

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
        # Column widths
        # ----------------------------------------------------

        widths = {

            "A": 10,

            "B": 15,

            "C": 25,

            "D": 15,

            "E": 20,

            "F": 20,

            "G": 18,

            "H": 50,

            "I": 25

        }

        for column, width in widths.items():

            sheet.column_dimensions[
                column
            ].width = width

        # ----------------------------------------------------
        # Temporary file
        # ----------------------------------------------------

        filename = (
            f"/tmp/monitoring_attempt_"
            f"{attempt_id}.xlsx"
        )

        workbook.save(
            filename
        )

        # ----------------------------------------------------
        # Send file
        # ----------------------------------------------------

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

        print("========================================")
        print("EXPORT MONITORING ERROR")
        print(repr(e))
        print("========================================")

        return (
            f"Could not export monitoring logs: {str(e)}",
            500
        )