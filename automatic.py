import pandas as pd
from datetime import datetime
from twilio.rest import Client
import time
import os


ACCOUNT_SID = "AC151c6b601ff1edf3a341ca479dcc8004"
AUTH_TOKEN = "683e7d62be77ae8cbd40caf7cef65b11"
TWILIO_NUMBER = "+18777804236"

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# ==============================
# FILE PATHS
# ==============================

STUDENTS_FILE = "database/students.csv"
ATTENDANCE_FILE = "database/attendance.csv"
LOG_FILE = "database/notification_log.csv"

os.makedirs("database", exist_ok=True)




def send_sms(phone, student_name, student_class, section):
    try:
        message = client.messages.create(
            body=f"""
Smart Attendance Alert 🚨

Student: {student_name}
Class: {student_class}-{section}
Status: ABSENT

If this is incorrect, please contact school.
""",
            from_=TWILIO_NUMBER,
            to=phone
        )
        print(f"SMS sent to {phone}")
    except Exception as e:
        print("SMS failed:", e)


def already_notified(student_id, date_str, hour_str):
    if not os.path.exists(LOG_FILE):
        return False

    log_df = pd.read_csv(LOG_FILE, dtype=str)

    return (
        (log_df["id"] == str(student_id)) &
        (log_df["date"] == date_str) &
        (log_df["hour"] == hour_str)
    ).any()


def log_notification(student_id, date_str, hour_str):
    log_data = pd.DataFrame([{
        "id": student_id,
        "date": date_str,
        "hour": hour_str
    }])

    if os.path.exists(LOG_FILE):
        log_data.to_csv(LOG_FILE, mode='a', header=False, index=False)
    else:
        log_data.to_csv(LOG_FILE, index=False)


def check_absentees():

    if not os.path.exists(STUDENTS_FILE):
        print("Students file not found.")
        return

    students_df = pd.read_csv(STUDENTS_FILE, dtype=str)

    today_date = datetime.now().strftime("%Y-%m-%d")
    current_hour = datetime.now().strftime("%H")

    if os.path.exists(ATTENDANCE_FILE):
        attendance_df = pd.read_csv(ATTENDANCE_FILE, dtype=str)
        today_attendance = attendance_df[attendance_df["date"] == today_date]
        present_ids = today_attendance["id"].astype(str).tolist()
    else:
        present_ids = []

    for _, student in students_df.iterrows():
        sid = str(student["id"])

        if sid not in present_ids:

            if not already_notified(sid, today_date, current_hour):

                send_sms(
                    student["parent_phone"],
                    student["name"],
                    student["class"],
                    student["section"]
                )

                log_notification(sid, today_date, current_hour)


if __name__ == "__main__":
    print("Automatic Attendance Notification System Started...")

    while True:
        print("Checking attendance...")
        check_absentees()
        print("Waiting for next hour...\n")
        time.sleep(10)  