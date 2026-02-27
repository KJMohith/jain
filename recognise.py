import os
import pickle
from datetime import datetime, timedelta

import cv2
import numpy as np
import pandas as pd
from deepface import DeepFace

import automatic

EMBEDDING_FILE = "database/embeddings.pkl"
ATTENDANCE_FILE = "database/attendance.csv"
STUDENTS_FILE = "database/students.csv"

THRESHOLD = 0.78
SLOT_MINUTES = 60
PRESENT_WITHIN_MINUTES = 5
LATE_WITHIN_MINUTES = 10


marked_slots = set()


def cosine_similarity(vec1, vec2):
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


def slot_start_for(now: datetime) -> datetime:
    return now.replace(minute=0, second=0, microsecond=0)


def load_students() -> dict[str, dict]:
    if not os.path.exists(STUDENTS_FILE):
        return {}

    try:
        students_df = pd.read_csv(STUDENTS_FILE, dtype=str)
    except Exception as exc:
        print(f"❌ Could not read students list: {exc}")
        return {}

    required = {"id", "name", "class", "section", "parent_phone"}
    if not required.issubset(students_df.columns):
        print("❌ students.csv is missing required columns.")
        return {}

    students = {}
    for _, row in students_df.iterrows():
        sid = str(row["id"])
        students[sid] = {
            "id": sid,
            "name": str(row["name"]),
            "class": str(row["class"]),
            "section": str(row["section"]),
            "parent_phone": str(row["parent_phone"]),
        }
    return students


def initialize_marked_slots_cache() -> None:
    if not os.path.exists(ATTENDANCE_FILE):
        return

    try:
        df = pd.read_csv(ATTENDANCE_FILE, dtype=str)
    except Exception:
        return

    if not {"id", "date", "slot_start"}.issubset(df.columns):
        return

    for _, row in df.iterrows():
        marked_slots.add((str(row["id"]), str(row["date"]), str(row["slot_start"])))


def status_for_seen_time(first_seen_at: datetime, slot_start: datetime) -> str:
    diff_minutes = (first_seen_at - slot_start).total_seconds() / 60
    if diff_minutes <= PRESENT_WITHIN_MINUTES:
        return "present"
    if diff_minutes <= LATE_WITHIN_MINUTES:
        return "late"
    return "absent"


def mark_attendance(student: dict, status: str, slot_start: datetime, recorded_at: datetime):
    date_str = slot_start.strftime("%Y-%m-%d")
    time_str = recorded_at.strftime("%H:%M:%S")
    slot_start_str = slot_start.strftime("%H:%M")

    key = (student["id"], date_str, slot_start_str)
    if key in marked_slots:
        return

    attendance_data = pd.DataFrame([
        {
            "id": student["id"],
            "name": student["name"],
            "class": student["class"],
            "section": student["section"],
            "date": date_str,
            "time": time_str,
            "slot_start": slot_start_str,
            "status": status,
        }
    ])

    needs_header = (not os.path.exists(ATTENDANCE_FILE)) or os.path.getsize(ATTENDANCE_FILE) == 0
    attendance_data.to_csv(
        ATTENDANCE_FILE,
        mode="a" if not needs_header else "w",
        header=needs_header,
        index=False,
    )

    marked_slots.add(key)
    print(f"✅ {student['name']} marked {status.upper()} for slot {slot_start_str}")


def make_slot_tracker(students: dict[str, dict]):
    return {
        sid: {
            "student": student,
            "first_seen": None,
            "attendance_written": False,
            "sms_sent": False,
        }
        for sid, student in students.items()
    }


def finalize_slot_if_needed(slot_tracker, current_slot_start, client):
    now = datetime.now()
    minutes_from_slot_start = (now - current_slot_start).total_seconds() / 60

    for sid, info in slot_tracker.items():
        if info["attendance_written"]:
            continue

        first_seen = info["first_seen"]
        student = info["student"]

        if first_seen is not None:
            status = status_for_seen_time(first_seen, current_slot_start)
            mark_attendance(student, status, current_slot_start, first_seen)
            info["attendance_written"] = True
            continue

        if minutes_from_slot_start > LATE_WITHIN_MINUTES:
            mark_attendance(student, "absent", current_slot_start, now)
            info["attendance_written"] = True

            if not info["sms_sent"]:
                automatic.send_sms(
                    client=client,
                    phone=student["parent_phone"],
                    student_name=student["name"],
                    student_class=student["class"],
                    section=student["section"],
                )
                info["sms_sent"] = True


def match_student(captured_embedding, db, slot_tracker):
    best_match_id = None
    best_score = -1

    for student_id, data in db.items():
        stored_embedding = data["embedding"]
        similarity = cosine_similarity(captured_embedding, stored_embedding)

        if similarity > best_score:
            best_score = similarity
            best_match_id = student_id

    if best_score >= THRESHOLD and best_match_id in slot_tracker:
        return best_match_id, best_score

    return None, best_score


def recognize(session_duration_seconds=None):
    if not os.path.exists(EMBEDDING_FILE):
        print("❌ No registered students found.")
        return

    with open(EMBEDDING_FILE, "rb") as f:
        db = pickle.load(f)

    students = load_students()
    if not students:
        print("❌ No students found in database/students.csv.")
        return

    initialize_marked_slots_cache()
    client = automatic.build_client()

    cap = cv2.VideoCapture(0)
    start_time = datetime.now()

    current_slot_start = slot_start_for(datetime.now())
    slot_tracker = make_slot_tracker(students)

    while True:
        now = datetime.now()
        if now >= current_slot_start + timedelta(minutes=SLOT_MINUTES):
            current_slot_start = slot_start_for(now)
            slot_tracker = make_slot_tracker(students)
            print(f"🕒 New attendance slot started: {current_slot_start.strftime('%H:%M')}")

        ret, frame = cap.read()
        if not ret:
            break

        try:
            result = DeepFace.represent(
                img_path=frame,
                model_name="Facenet",
                enforce_detection=True,
            )

            found_known_face = False

            for face in result:
                captured_embedding = face["embedding"]
                facial_area = face.get("facial_area", {})
                x = int(facial_area.get("x", 50))
                y = int(facial_area.get("y", 50))
                w = int(facial_area.get("w", 120))
                h = int(facial_area.get("h", 120))

                matched_id, score = match_student(captured_embedding, db, slot_tracker)

                if matched_id is None:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    cv2.putText(
                        frame,
                        "Unknown",
                        (x, max(25, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2,
                    )
                    continue

                found_known_face = True
                student = students[matched_id]

                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    f"{student['name']} ({score:.2f})",
                    (x, max(25, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )

                if slot_tracker[matched_id]["first_seen"] is None:
                    slot_tracker[matched_id]["first_seen"] = now

            if not found_known_face:
                cv2.putText(
                    frame,
                    "No registered student recognized",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                )

        except Exception:
            pass

        finalize_slot_if_needed(slot_tracker, current_slot_start, client)

        cv2.imshow("Face Recognition", frame)

        if (
            session_duration_seconds is not None
            and (datetime.now() - start_time).total_seconds() >= session_duration_seconds
        ):
            print("⏱️ Recognition session completed.")
            break

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    recognize()
