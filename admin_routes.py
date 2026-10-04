from flask import (
    Blueprint,
    render_template,
    request,
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

    try:

        print("====================================")
        print("CREATE EXAM REQUEST")
        print("====================================")

        # ----------------------------------------------------
        # Get form values
        # ----------------------------------------------------

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        duration_text = request.form.get(
            "duration_minutes",
            ""
        ).strip()

        passing_score_text = request.form.get(
            "passing_score",
            ""
        ).strip()

        print("TITLE:", title)
        print("DESCRIPTION:", description)
        print("DURATION:", duration_text)
        print("PASSING SCORE:", passing_score_text)

        # ----------------------------------------------------
        # Validation
        # ----------------------------------------------------

        if not title:

            flash(
                "Exam title is required.",
                "error"
            )

            return redirect(
                url_for("admin.create_exam")
            )

        if not duration_text:

            flash(
                "Duration is required.",
                "error"
            )

            return redirect(
                url_for("admin.create_exam")
            )

        if not passing_score_text:

            flash(
                "Passing score is required.",
                "error"
            )

            return redirect(
                url_for("admin.create_exam")
            )

        # ----------------------------------------------------
        # Convert duration
        # ----------------------------------------------------

        try:

            duration = int(
                duration_text
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
        # Convert passing score
        # ----------------------------------------------------

        try:

            passing_score = float(
                passing_score_text
            )

        except ValueError:

            flash(
                "Passing score must be a valid number.",
                "error"
            )

            return redirect(
                url_for("admin.create_exam")
            )

        if passing_score < 0 or passing_score > 100:

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

        print("Connecting to Supabase...")

        db = get_db()

        print("Supabase connection obtained.")

        # ----------------------------------------------------
        # Insert exam
        # ----------------------------------------------------

        exam_data = {
            "title": title,
            "description": description,
            "duration_minutes": duration,
            "passing_score": passing_score,
            "is_active": True
        }

        print("INSERT DATA:")
        print(exam_data)

        response = (
            db
            .table("exams")
            .insert(exam_data)
            .execute()
        )

        print("SUPABASE RESPONSE:")
        print(response)

        # ----------------------------------------------------
        # Check response
        # ----------------------------------------------------

        if not response.data:

            print(
                "ERROR: Supabase returned no data."
            )

            flash(
                "Exam could not be created.",
                "error"
            )

            return redirect(
                url_for("admin.create_exam")
            )

        # ----------------------------------------------------
        # Get ID
        # ----------------------------------------------------

        exam_id = response.data[0].get(
            "id"
        )

        if not exam_id:

            print(
                "ERROR: Exam ID was not returned."
            )

            flash(
                "Exam created but ID was not returned.",
                "error"
            )

            return redirect(
                url_for("admin.create_exam")
            )

        print(
            "EXAM CREATED:",
            exam_id
        )

        # ----------------------------------------------------
        # Success
        # ----------------------------------------------------

        flash(
            "Exam created successfully!",
            "success"
        )

        # Go to upload questions
        return redirect(
            url_for(
                "admin.upload_questions",
                exam_id=exam_id
            )
        )

    except Exception as e:

        # ----------------------------------------------------
        # IMPORTANT:
        # Print complete error in Vercel logs
        # ----------------------------------------------------

        print("====================================")
        print("CREATE EXAM FAILED")
        print("ERROR TYPE:")
        print(type(e).__name__)
        print("ERROR:")
        print(str(e))
        print("FULL ERROR:")
        print(repr(e))
        print("====================================")

        flash(
            "Could not create exam. "
            "Please check the Vercel logs.",
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
            db
            .table("exams")
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

    except Exception as e:

        print(
            "EXAM FETCH ERROR:",
            repr(e)
        )

        return (
            "Database error while loading exam.",
            500
        )

    if not exam:

        return (
            "Exam not found.",
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

    if not file or not file.filename:

        flash(
            "No file selected.",
            "error"
        )

        return redirect(
            request.url
        )

    if not allowed_file(
        file.filename
    ):

        flash(
            "Only Excel files (.xlsx, .xls) are allowed.",
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
        # Save Excel
        # ----------------------------------------------------

        file.save(filepath)

        # ----------------------------------------------------
        # Open Excel
        # ----------------------------------------------------

        workbook = openpyxl.load_workbook(
            filepath,
            read_only=True,
            data_only=True
        )

        sheet = workbook.active

        questions = []

        # ----------------------------------------------------
        # Read questions
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
        # Validate
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
        # Insert
        # ----------------------------------------------------

        response = (
            db
            .table("questions")
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

    try:

        db = get_db()

        exam_response = (
            db
            .table("exams")
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

        attempt_response = (
            db
            .table("student_attempts")
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
                db
                .table("users")
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

    except Exception as e:

        print(
            "VIEW RESULTS ERROR:",
            repr(e)
        )

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

    try:

        db = get_db()

        attempt_response = (
            db
            .table("student_attempts")
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

        user_response = (
            db
            .table("users")
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

        exam_response = (
            db
            .table("exams")
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

        logs_response = (
            db
            .table("monitoring_logs")
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

        report_response = (
            db
            .table("exam_reports")
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

    except Exception as e:

        print(
            "VIEW LOGS ERROR:",
            repr(e)
        )

        return (
            f"Could not load logs: {str(e)}",
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

    try:

        db = get_db()

        attempt_response = (
            db
            .table("student_attempts")
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

        for attempt_id in attempt_ids:

            (
                db
                .table("exam_reports")
                .delete()
                .eq(
                    "attempt_id",
                    attempt_id
                )
                .execute()
            )

            (
                db
                .table("monitoring_logs")
                .delete()
                .eq(
                    "attempt_id",
                    attempt_id
                )
                .execute()
            )

        (
            db
            .table("student_attempts")
            .delete()
            .eq(
                "exam_id",
                exam_id
            )
            .execute()
        )

        (
            db
            .table("questions")
            .delete()
            .eq(
                "exam_id",
                exam_id
            )
            .execute()
        )

        (
            db
            .table("exams")
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

    try:

        db = get_db()

        response = (
            db
            .table("monitoring_logs")
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

        for cell in sheet[1]:

            cell.font = Font(
                bold=True
            )

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