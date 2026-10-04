import cv2
import mediapipe as mp
import time
import numpy as np

# =========================
# State Variables
# =========================
last_warning_time = 0
face_detection_count = 0
no_face_count = 0
look_away_count = 0
warning_count = 0
monitoring_active = True

WARNING_COOLDOWN = 5  # seconds

# =========================
# MediaPipe Setup
# =========================
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# =========================
# Helper Functions
# =========================
def handle_violation(message):
    global last_warning_time, warning_count, monitoring_active

    now = time.time()
    if now - last_warning_time < WARNING_COOLDOWN:
        return

    last_warning_time = now
    warning_count += 1

    print(f"[WARNING {warning_count}] {message}")

    # 🔴 Send to backend here if needed
    # requests.post("/student/issue-warning")

    if warning_count >= 3:
        print("❌ Exam terminated due to multiple violations.")
        monitoring_active = False


def analyze_gaze(landmarks):
    left_eye = landmarks[33]
    right_eye = landmarks[263]
    nose = landmarks[1]

    eye_center_x = (left_eye.x + right_eye.x) / 2
    eye_center_y = (left_eye.y + right_eye.y) / 2

    horizontal_diff = abs(eye_center_x - nose.x)
    vertical_diff = abs(eye_center_y - nose.y)

    if horizontal_diff > 0.05 or vertical_diff > 0.08:
        return "Away"

    return "Center"


def analyze_head_pose(landmarks):
    left_ear = landmarks[234]
    right_ear = landmarks[454]
    nose = landmarks[1]

    ear_distance = abs(left_ear.x - right_ear.x)

    if ear_distance < 0.25:
        return "Looking Away"

    if nose.y < 0.15 or nose.y > 0.9:
        return "Head Tilted"

    return "Forward"


# =========================
# OpenCV Webcam Loop
# =========================
cap = cv2.VideoCapture(0)

while cap.isOpened() and monitoring_active:
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = face_mesh.process(rgb)

    h, w, _ = frame.shape

    if results.multi_face_landmarks:
        face_detection_count += 1
        no_face_count = 0

        landmarks = results.multi_face_landmarks[0].landmark

        gaze = analyze_gaze(landmarks)
        head_pose = analyze_head_pose(landmarks)

        if gaze == "Away" or head_pose == "Looking Away":
            look_away_count += 1
            if look_away_count > 10:
                handle_violation("Looking away from screen")
                look_away_count = 0
            status_text = "⚠ Looking Away"
            color = (0, 0, 255)
        else:
            look_away_count = 0
            status_text = "✓ Face & Gaze OK"
            color = (0, 255, 0)

        cv2.putText(frame, status_text, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    else:
        no_face_count += 1
        if no_face_count > 15:
            handle_violation("Face not detected")
            no_face_count = 0

        cv2.putText(frame, "⚠ No Face Detected", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow("Exam Proctoring", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

# =========================
# Cleanup
# =========================
cap.release()
cv2.destroyAllWindows()
face_mesh.close()
