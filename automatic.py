"""Automatic absentee notification worker.

This script checks today's attendance records and sends SMS alerts to parents
for students who have not been marked present. It avoids duplicate alerts by
recording notifications per student/date/hour in a log file.
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Iterable

import pandas as pd
from twilio.base.exceptions import TwilioException
from twilio.rest import Client

# ==============================
# CONFIGURATION
# ==============================

DATABASE_DIR = "database"
STUDENTS_FILE = os.path.join(DATABASE_DIR, "students.csv")
ATTENDANCE_FILE = os.path.join(DATABASE_DIR, "attendance.csv")
LOG_FILE = os.path.join(DATABASE_DIR, "notification_log.csv")

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "3600"))

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER", "")

os.makedirs(DATABASE_DIR, exist_ok=True)

REQUIRED_STUDENT_COLUMNS = {"id", "name", "class", "section", "parent_phone"}
REQUIRED_ATTENDANCE_COLUMNS = {"id", "date"}
REQUIRED_LOG_COLUMNS = {"id", "date", "hour"}


def build_client() -> Client | None:
    """Create a Twilio client if all credentials are available."""
    if not ACCOUNT_SID or not AUTH_TOKEN or not TWILIO_NUMBER:
        print(
            "⚠️ Twilio credentials/number not fully configured. "
            "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_NUMBER."
        )
        return None
    return Client(ACCOUNT_SID, AUTH_TOKEN)


def ensure_columns(df: pd.DataFrame, required: set[str], label: str) -> bool:
    """Validate required columns and report clear errors."""
    missing = sorted(required - set(df.columns))
    if missing:
        print(f"❌ {label} is missing columns: {', '.join(missing)}")
        return False
    return True


def send_sms(client: Client | None, phone: str, student_name: str, student_class: str, section: str) -> bool:
    """Send a single absentee message."""
    if client is None:
        print(f"⚠️ Skipping SMS (no Twilio client) for {student_name} -> {phone}")
        return False

    body = (
        "Smart Attendance Alert 🚨\n\n"
        f"Student: {student_name}\n"
        f"Class: {student_class}-{section}\n"
        "Status: ABSENT\n\n"
        "If this is incorrect, please contact school."
    )

    try:
        client.messages.create(body=body, from_=TWILIO_NUMBER, to=phone)
        print(f"✅ SMS sent to {phone}")
        return True
    except TwilioException as exc:
        print(f"❌ Twilio SMS failed for {phone}: {exc}")
    except Exception as exc:  # defensive fallback for non-Twilio runtime errors
        print(f"❌ Unexpected SMS error for {phone}: {exc}")
    return False


def read_csv_safe(path: str, dtype: str = "str") -> pd.DataFrame | None:
    """Read a CSV and return None on failure with a readable message."""
    if not os.path.exists(path):
        return None

    try:
        return pd.read_csv(path, dtype=dtype)
    except Exception as exc:
        print(f"❌ Failed to read '{path}': {exc}")
        return None


def already_notified(log_df: pd.DataFrame, student_id: str, date_str: str, hour_str: str) -> bool:
    """Check if a student has already been notified for a specific hour."""
    return (
        (log_df["id"] == student_id)
        & (log_df["date"] == date_str)
        & (log_df["hour"] == hour_str)
    ).any()


def append_notification(student_id: str, date_str: str, hour_str: str) -> None:
    """Append one notification record to the log file."""
    row = pd.DataFrame([{"id": student_id, "date": date_str, "hour": hour_str}])
    if os.path.exists(LOG_FILE):
        row.to_csv(LOG_FILE, mode="a", header=False, index=False)
    else:
        row.to_csv(LOG_FILE, index=False)


def present_ids_today(attendance_df: pd.DataFrame | None, today_date: str) -> set[str]:
    """Extract present student IDs from today's attendance."""
    if attendance_df is None:
        return set()
    today = attendance_df[attendance_df["date"] == today_date]
    return set(today["id"].astype(str).tolist())


def iter_absentees(students_df: pd.DataFrame, present_ids: set[str]) -> Iterable[pd.Series]:
    """Yield student rows that are absent today."""
    for _, student in students_df.iterrows():
        student_id = str(student["id"])
        if student_id not in present_ids:
            yield student


def check_absentees(client: Client | None) -> None:
    """Run one absentee detection and notification pass."""
    students_df = read_csv_safe(STUDENTS_FILE)
    if students_df is None:
        print("⚠️ Students file not found; skipping check.")
        return

    if not ensure_columns(students_df, REQUIRED_STUDENT_COLUMNS, STUDENTS_FILE):
        return

    now = datetime.now()
    today_date = now.strftime("%Y-%m-%d")
    current_hour = now.strftime("%H")

    attendance_df = read_csv_safe(ATTENDANCE_FILE)
    if attendance_df is not None and not ensure_columns(attendance_df, REQUIRED_ATTENDANCE_COLUMNS, ATTENDANCE_FILE):
        return

    log_df = read_csv_safe(LOG_FILE)
    if log_df is None:
        log_df = pd.DataFrame(columns=sorted(REQUIRED_LOG_COLUMNS))
    elif not ensure_columns(log_df, REQUIRED_LOG_COLUMNS, LOG_FILE):
        return

    present_ids = present_ids_today(attendance_df, today_date)

    sent_count = 0
    skipped_count = 0
    absent_count = 0

    for student in iter_absentees(students_df, present_ids):
        absent_count += 1
        sid = str(student["id"])
        if already_notified(log_df, sid, today_date, current_hour):
            skipped_count += 1
            continue

        sms_sent = send_sms(
            client=client,
            phone=str(student["parent_phone"]),
            student_name=str(student["name"]),
            student_class=str(student["class"]),
            section=str(student["section"]),
        )

        if sms_sent:
            append_notification(sid, today_date, current_hour)
            log_df = pd.concat(
                [log_df, pd.DataFrame([{"id": sid, "date": today_date, "hour": current_hour}])],
                ignore_index=True,
            )
            sent_count += 1

    print(
        "Attendance check complete -> "
        f"absent: {absent_count}, "
        f"sent: {sent_count}, "
        f"already_notified_this_hour: {skipped_count}"
    )


def main() -> None:
    client = build_client()
    print("Automatic Attendance Notification System Started...")

    while True:
        print("Checking attendance...")
        check_absentees(client)
        print(f"Waiting for next run ({CHECK_INTERVAL_SECONDS} seconds)...\n")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
