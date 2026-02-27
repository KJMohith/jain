import cv2
import os
import pickle
import pandas as pd
from deepface import DeepFace

os.makedirs("images", exist_ok=True)
os.makedirs("database", exist_ok=True)

EMBEDDING_FILE = "database/embeddings.pkl"
STUDENT_FILE = "database/students.csv"


def register_student(student_id, name, student_class, section):
    cap = cv2.VideoCapture(0)

    print("\nPress SPACE to capture image")
    print("Press ESC to cancel\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to access camera")
            return

        cv2.imshow("Register Student", frame)

        key = cv2.waitKey(1)

        if key == 27:  
            print("Registration cancelled")
            cap.release()
            cv2.destroyAllWindows()
            return

        elif key == 32:  
            break

    cap.release()
    cv2.destroyAllWindows()

    
    image_path = f"images/{student_id}_{name}.jpg"
    cv2.imwrite(image_path, frame)
    print("Image saved.")

    
    try:
        embedding = DeepFace.represent(
            img_path=image_path,
            model_name="Facenet",
            enforce_detection=True
        )[0]["embedding"]
    except Exception as e:
        print("Face not detected properly. Try again.")
        os.remove(image_path)
        return

    
    if os.path.exists(EMBEDDING_FILE):
        with open(EMBEDDING_FILE, "rb") as f:
            db = pickle.load(f)
    else:
        db = {}

    db[student_id] = {
        "name": name,
        "class": student_class,
        "section": section,
        "embedding": embedding
    }

    
    with open(EMBEDDING_FILE, "wb") as f:
        pickle.dump(db, f)

    print("Embedding stored.")

    student_data = pd.DataFrame([{
        "id": student_id,
        "name": name,
        "class": student_class,
        "section": section
    }])

    if os.path.exists(STUDENT_FILE):
        student_data.to_csv(STUDENT_FILE, mode='a', header=False, index=False)
    else:
        student_data.to_csv(STUDENT_FILE, index=False)

    print("Student Registered Successfully!\n")


if __name__ == "__main__":
    sid = input("Enter Student ID: ")
    name = input("Enter Name: ")
    student_class = input("Enter Class: ")
    section = input("Enter Section: ")

    register_student(sid, name, student_class, section)