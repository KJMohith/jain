import cv2
import pickle
import numpy as np
import pandas as pd
from deepface import DeepFace
from datetime import datetime
import os

EMBEDDING_FILE = "database/embeddings.pkl"
ATTENDANCE_FILE = "database/attendance.csv"

THRESHOLD = 0.70

marked_today = set()


def cosine_similarity(vec1, vec2):
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


def mark_attendance(student_id, name, student_class, section):

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    if (student_id, date_str) in marked_today:
        return

    if os.path.exists(ATTENDANCE_FILE):
        df = pd.read_csv(ATTENDANCE_FILE)
        if ((df["id"] == student_id) & (df["date"] == date_str)).any():
            marked_today.add((student_id, date_str))
            print(f"{name} already marked today.")
            return

    attendance_data = pd.DataFrame([{
        "id": student_id,
        "name": name,
        "class": student_class,
        "section": section,
        "date": date_str,
        "time": time_str
    }])

    if os.path.exists(ATTENDANCE_FILE):
        attendance_data.to_csv(ATTENDANCE_FILE, mode='a', header=False, index=False)
    else:
        attendance_data.to_csv(ATTENDANCE_FILE, index=False)

    marked_today.add((student_id, date_str))
    print(f"✅ Attendance marked for {name}")


def recognize():

    if not os.path.exists(EMBEDDING_FILE):
        print("❌ No registered students found.")
        return

    with open(EMBEDDING_FILE, "rb") as f:
        db = pickle.load(f)

    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        try:
            result = DeepFace.represent(
                img_path=frame,
                model_name="Facenet",
                enforce_detection=True
            )

            captured_embedding = result[0]["embedding"]

            best_match_id = None
            best_score = -1

            for student_id, data in db.items():
                stored_embedding = data["embedding"]
                similarity = cosine_similarity(captured_embedding, stored_embedding)

                if similarity > best_score:
                    best_score = similarity
                    best_match_id = student_id

            if best_score >= THRESHOLD:
                student = db[best_match_id]

                name = student["name"]

                cv2.putText(
                    frame,
                    f"{name} ({best_score:.2f})",
                    (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2
                )

                mark_attendance(
                    best_match_id,
                    student["name"],
                    student["class"],
                    student["section"]
                )

            else:
                cv2.putText(
                    frame,
                    "Unknown",
                    (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2
                )

        except Exception:
            pass

        cv2.imshow("Face Recognition", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    recognize()