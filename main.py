import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import recognise
import regsiter
import os
import signal


def show_loading(text="Loading..."):
    loading = tk.Toplevel(root)
    loading.geometry("300x120")
    loading.title(text)
    loading.grab_set()
    loading.transient(root)

    tk.Label(loading, text=text).pack(pady=10)

    progress = ttk.Progressbar(
        loading,
        mode="indeterminate",
        length=200
    )
    progress.pack(pady=10)
    progress.start(10)

    return loading


def open_register_window():
    reg_win = tk.Toplevel(root)
    reg_win.title("Register Student")
    reg_win.geometry("400x450")

    tk.Label(reg_win, text="Student ID").pack(pady=5)
    entry_id = tk.Entry(reg_win)
    entry_id.pack(pady=5)

    tk.Label(reg_win, text="Name").pack(pady=5)
    entry_name = tk.Entry(reg_win)
    entry_name.pack(pady=5)

    tk.Label(reg_win, text="Class").pack(pady=5)
    entry_class = tk.Entry(reg_win)
    entry_class.pack(pady=5)

    tk.Label(reg_win, text="Section").pack(pady=5)
    entry_section = tk.Entry(reg_win)
    entry_section.pack(pady=5)

    tk.Label(reg_win, text="Parent Phone (+CountryCode)").pack(pady=5)
    entry_phone = tk.Entry(reg_win)
    entry_phone.pack(pady=5)

    def submit():
        sid = entry_id.get()
        name = entry_name.get()
        student_class = entry_class.get()
        section = entry_section.get()
        phone = entry_phone.get()

        if not sid or not name or not phone:
            messagebox.showerror("Error", "ID, Name and Phone are required")
            return

        if not phone.startswith("+"):
            messagebox.showerror(
                "Error",
                "Phone must include country code. Example: +919876543210"
            )
            return

        reg_win.destroy()
        loading = show_loading("Opening Camera...")

        def run_register():
            root.after(0, lambda: root.attributes("-fullscreen", False))

            regsiter.register_student(
                sid, name, student_class, section, phone
            )

            root.after(0, lambda: root.attributes("-fullscreen", True))
            root.after(0, loading.destroy)

        root.after(300, lambda: threading.Thread(target=run_register).start())

    tk.Button(reg_win, text="Register", command=submit).pack(pady=20)


def start_recognition():
    duration_minutes = simpledialog.askinteger(
        "Recognition Duration",
        "Run recognition for how many minutes?",
        minvalue=1,
        initialvalue=5,
        parent=root,
    )

    if duration_minutes is None:
        return

    loading = show_loading("Starting Recognition...")

    def run_recognition():
        root.after(0, lambda: root.attributes("-fullscreen", False))
        recognise.recognize(session_duration_seconds=duration_minutes * 60)
        root.after(0, lambda: root.attributes("-fullscreen", True))
        root.after(0, loading.destroy)

    root.after(300, lambda: threading.Thread(target=run_recognition).start())


def exit_app():
    try:
        root.destroy()
    except:
        pass
    os.kill(os.getpid(), signal.SIGTERM)


root = tk.Tk()
root.title("Smart Attendance System")
root.attributes("-fullscreen", True)

frame = tk.Frame(root)
frame.pack(expand=True)

tk.Label(
    frame,
    text="SMART ATTENDANCE SYSTEM",
    font=("Arial", 35)
).pack(pady=40)

tk.Button(
    frame,
    text="Add Student",
    height=3,
    width=25,
    command=open_register_window
).pack(pady=20)

tk.Button(
    frame,
    text="Start Recognition",
    height=3,
    width=25,
    command=start_recognition
).pack(pady=20)

tk.Button(
    frame,
    text="Exit",
    height=3,
    width=25,
    command=exit_app
).pack(pady=20)

root.mainloop()
