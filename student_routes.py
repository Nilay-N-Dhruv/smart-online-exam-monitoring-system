from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for
)

import json
import random

from datetime import datetime

from database import get_db


student_bp = Blueprint(
    "student",
    __name__,
    url_prefix="/student"
)


# ============================================================
# START EXAM
# ============================================================

@student_bp.route(
    "/start-exam/<int:exam_id>"
)
def start_exam(exam_id):

    if session.get("role") != "student":

        return redirect(
            url_for("student_login")
        )

    try:

        db = get_db()

        # ----------------------------------------------------
        # CHECK EXISTING ATTEMPT
        # ----------------------------------------------------

        response = (
            db.table("student_attempts")
            .select("*")
            .eq(
                "student_id",
                session["user_id"]
            )
            .eq(
                "exam_id",
                exam_id
            )
            .limit(1)
            .execute()
        )

        existing_attempt = (
            response.data[0]
            if response.data
            else None
        )

        if existing_attempt:

            return (
                "You have already attempted this exam",
                403
            )

        # ----------------------------------------------------
        # GET EXAM
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

        if not exam_response.data:

            return (
                "Exam not found",
                404
            )

        exam = exam_response.data[0]

        # ----------------------------------------------------
        # GET QUESTIONS
        # ----------------------------------------------------

        question_response = (
            db.table("questions")
            .select("*")
            .eq(
                "exam_id",
                exam_id
            )
            .execute()
        )

        questions = (
            question_response.data
            or []
        )

        random.shuffle(
            questions
        )

        if not questions:

            return (
                "No questions available for this exam",
                400
            )

        # ----------------------------------------------------
        # TOTAL MARKS
        # ----------------------------------------------------

        total_marks = sum(
            int(
                question.get(
                    "marks"
                ) or 1
            )
            for question in questions
        )

        # ----------------------------------------------------
        # CREATE ATTEMPT
        # ----------------------------------------------------

        attempt_response = (
            db.table("student_attempts")
            .insert({

                "student_id":
                    session["user_id"],

                "exam_id":
                    exam_id,

                "total_marks":
                    total_marks,

                "answers":
                    {},

                "status":
                    "in_progress",

                "warnings_count":
                    0

            })
            .execute()
        )

        if not attempt_response.data:

            return (
                "Could not create exam attempt",
                500
            )

        attempt_id = (
            attempt_response
            .data[0]["id"]
        )

        session["attempt_id"] = (
            attempt_id
        )

        session["exam_id"] = (
            exam_id
        )

        return render_template(
            "student/exam_interface.html",
            exam=exam,
            questions=questions,
            attempt_id=attempt_id
        )

    except Exception as e:

        print(
            "START EXAM ERROR:",
            e
        )

        return (
            "Unable to start exam.",
            500
        )


# ============================================================
# SUBMIT ANSWER
# ============================================================

@student_bp.route(
    "/submit-answer",
    methods=["POST"]
)
def submit_answer():

    if session.get("role") != "student":

        return jsonify({
            "error":
                "Unauthorized"
        }), 403

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    question_id = (
        data.get("question_id")
    )

    answer = (
        data.get("answer")
    )

    attempt_id = (
        session.get("attempt_id")
    )

    if not attempt_id:

        return jsonify({
            "error":
                "No active exam"
        }), 400

    try:

        db = get_db()

        response = (
            db.table("student_attempts")
            .select("*")
            .eq(
                "id",
                attempt_id
            )
            .limit(1)
            .execute()
        )

        if not response.data:

            return jsonify({
                "error":
                    "Attempt not found"
            }), 404

        attempt = response.data[0]

        answers = (
            attempt.get("answers")
            or {}
        )

        if isinstance(
            answers,
            str
        ):

            try:

                answers = json.loads(
                    answers
                )

            except Exception:

                answers = {}

        answers[
            str(question_id)
        ] = answer

        (
            db.table(
                "student_attempts"
            )
            .update({
                "answers":
                    answers
            })
            .eq(
                "id",
                attempt_id
            )
            .execute()
        )

        return jsonify({
            "success":
                True
        })

    except Exception as e:

        print(
            "SUBMIT ANSWER ERROR:",
            e
        )

        return jsonify({
            "error":
                "Could not save answer"
        }), 500


# ============================================================
# LOG MONITORING
# ============================================================

@student_bp.route(
    "/log-monitoring",
    methods=["POST"]
)
def log_monitoring():

    if session.get("role") != "student":

        return jsonify({
            "error":
                "Unauthorized"
        }), 403

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    attempt_id = (
        session.get("attempt_id")
    )

    if not attempt_id:

        return jsonify({
            "error":
                "No active exam"
        }), 400

    try:

        db = get_db()

        db.table(
            "monitoring_logs"
        ).insert({

            "attempt_id":
                attempt_id,

            "event_type":
                data.get(
                    "event_type",
                    "UNKNOWN"
                ),

            "face_detected":
                data.get(
                    "face_detected"
                ),

            "gaze_direction":
                data.get(
                    "gaze_direction"
                ),

            "head_pose":
                data.get(
                    "head_pose"
                ),

            "warning_issued":
                data.get(
                    "warning_issued",
                    0
                ),

            "details":
                data.get(
                    "details",
                    ""
                )

        }).execute()

        return jsonify({
            "success":
                True
        })

    except Exception as e:

        print(
            "MONITORING LOG ERROR:",
            e
        )

        return jsonify({
            "error":
                "Could not save monitoring log"
        }), 500


# ============================================================
# ISSUE WARNING
# ============================================================

@student_bp.route(
    "/issue-warning",
    methods=["POST"]
)
def issue_warning():

    if session.get("role") != "student":

        return jsonify({
            "error":
                "Unauthorized"
        }), 403

    attempt_id = (
        session.get("attempt_id")
    )

    if not attempt_id:

        return jsonify({
            "error":
                "No active exam"
        }), 400

    try:

        db = get_db()

        response = (
            db.table("student_attempts")
            .select(
                "warnings_count"
            )
            .eq(
                "id",
                attempt_id
            )
            .limit(1)
            .execute()
        )

        if not response.data:

            return jsonify({
                "error":
                    "Attempt not found"
            }), 404

        current_count = (
            response.data[0].get(
                "warnings_count"
            )
            or 0
        )

        new_count = (
            current_count + 1
        )

        (
            db.table(
                "student_attempts"
            )
            .update({
                "warnings_count":
                    new_count
            })
            .eq(
                "id",
                attempt_id
            )
            .execute()
        )

        db.table(
            "monitoring_logs"
        ).insert({

            "attempt_id":
                attempt_id,

            "event_type":
                "WARNING",

            "warning_issued":
                1,

            "details":
                f"Warning {new_count} issued"

        }).execute()

        if new_count >= 3:

            return jsonify({

                "success":
                    True,

                "terminate":
                    True,

                "warnings":
                    new_count

            })

        return jsonify({

            "success":
                True,

            "terminate":
                False,

            "warnings":
                new_count

        })

    except Exception as e:

        print(
            "WARNING ERROR:",
            e
        )

        return jsonify({
            "error":
                "Could not issue warning"
        }), 500


# ============================================================
# SUBMIT EXAM
# ============================================================

@student_bp.route(
    "/submit-exam",
    methods=["POST"]
)
def submit_exam():

    if session.get("role") != "student":

        return jsonify({
            "error":
                "Unauthorized"
        }), 403

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    attempt_id = (
        session.get("attempt_id")
    )

    reason = (
        data.get(
            "reason",
            "manual_submit"
        )
    )

    if not attempt_id:

        return jsonify({
            "error":
                "No active exam"
        }), 400

    try:

        db = get_db()

        # ----------------------------------------------------
        # GET ATTEMPT
        # ----------------------------------------------------

        response = (
            db.table("student_attempts")
            .select("*")
            .eq(
                "id",
                attempt_id
            )
            .limit(1)
            .execute()
        )

        if not response.data:

            return jsonify({
                "error":
                    "Attempt not found"
            }), 404

        attempt = (
            response.data[0]
        )

        # ----------------------------------------------------
        # ANSWERS
        # ----------------------------------------------------

        answers = (
            attempt.get("answers")
            or {}
        )

        if isinstance(
            answers,
            str
        ):

            try:

                answers = json.loads(
                    answers
                )

            except Exception:

                answers = {}

        # ----------------------------------------------------
        # QUESTIONS
        # ----------------------------------------------------

        question_response = (
            db.table("questions")
            .select("*")
            .eq(
                "exam_id",
                attempt["exam_id"]
            )
            .execute()
        )

        questions = (
            question_response.data
            or []
        )

        # ----------------------------------------------------
        # SCORE
        # ----------------------------------------------------

        score = 0

        for question in questions:

            student_answer = (
                answers.get(
                    str(question["id"])
                )
            )

            correct_answer = (
                question.get(
                    "correct_answer"
                )
            )

            if (
                student_answer
                and correct_answer
                and str(
                    student_answer
                ).upper()
                ==
                str(
                    correct_answer
                ).upper()
            ):

                score += int(
                    question.get(
                        "marks"
                    ) or 1
                )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        status = (
            "terminated"
            if reason == "violations"
            else "completed"
        )

        # ----------------------------------------------------
        # UPDATE ATTEMPT
        # ----------------------------------------------------

        (
            db.table(
                "student_attempts"
            )
            .update({

                "score":
                    score,

                "submitted_at":
                    datetime.utcnow()
                    .isoformat(),

                "status":
                    status,

                "violation_reason":
                    reason

            })
            .eq(
                "id",
                attempt_id
            )
            .execute()
        )

        # ----------------------------------------------------
        # MONITORING LOG
        # ----------------------------------------------------

        db.table(
            "monitoring_logs"
        ).insert({

            "attempt_id":
                attempt_id,

            "event_type":
                "EXAM_SUBMITTED",

            "details":
                f"Reason: {reason}"

        }).execute()

        # ----------------------------------------------------
        # CLEAR SESSION
        # ----------------------------------------------------

        session.pop(
            "attempt_id",
            None
        )

        session.pop(
            "exam_id",
            None
        )

        return jsonify({

            "success":
                True,

            "score":
                score,

            "total":
                len(questions)

        })

    except Exception as e:

        print(
            "SUBMIT EXAM ERROR:",
            e
        )

        return jsonify({
            "error":
                "Could not submit exam"
        }), 500