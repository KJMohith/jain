import threading
import tkinter as tk
from tkinter import simpledialog
import recognise
import regsiter
import time

recognition_thread = None
recognition_running = False


def start_recognition():
    global recognition_thread, recognition_running

    if recognition_running:
        return

    recognition_running = True

    recognition_thread = threading.Thread(target=recognise.recognize)
    recognition_thread.start()


def stop_recognition():
    global recognition_running
    recognition_running = False
    # recognize.py must exit when 'q' pressed
    time.sleep(1)


def add_student():
    stop_recognition()
    time.sleep(1)

    sid = simpledialog.askstring("Input", "Enter Student ID")
    name = simpledialog.askstring("Input", "Enter Name")
    student_class = simpledialog.askstring("Input", "Enter Class")
    section = simpledialog.askstring("Input", "Enter Section")

    regsiter.register_student(sid, name, student_class, section)

    start_recognition()


def exit_app():
    stop_recognition()
    root.destroy()


root = tk.Tk()
root.title("Smart Attendance System")
root.geometry("300x200")

tk.Button(root, text="Start Recognition", command=start_recognition).pack(pady=10)
tk.Button(root, text="Add Student", command=add_student).pack(pady=10)
tk.Button(root, text="Exit", command=exit_app).pack(pady=10)

root.mainloop()