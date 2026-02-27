import tkinter as tk
from tkinter import ttk, messagebox
import threading
import recognise
import regsiter


# ---------------- LOADING WINDOW ----------------
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


# ---------------- REGISTER ----------------
def open_register_window():
    reg_win = tk.Toplevel(root)
    reg_win.title("Register Student")
    reg_win.geometry("400x400")

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

    def submit():
        sid = entry_id.get()
        name = entry_name.get()
        student_class = entry_class.get()
        section = entry_section.get()

        if not sid or not name:
            messagebox.showerror("Error", "ID and Name required")
            return

        reg_win.destroy()
        loading = show_loading("Opening Camera...")

        def run_register():
            # Exit fullscreen so camera appears properly
            root.after(0, lambda: root.attributes("-fullscreen", False))

            regsiter.register_student(
                sid, name, student_class, section
            )

            # Restore fullscreen after camera closes
            root.after(0, lambda: root.attributes("-fullscreen", True))
            root.after(0, loading.destroy)

        root.after(300, lambda: threading.Thread(target=run_register).start())

    tk.Button(reg_win, text="Register",
              command=submit).pack(pady=20)


# ---------------- RECOGNITION ----------------
def start_recognition():

    loading = show_loading("Starting Recognition...")

    def run_recognition():
        # Exit fullscreen so camera shows on top
        root.after(0, lambda: root.attributes("-fullscreen", False))

        recognise.recognize()

        # Restore fullscreen after camera closes
        root.after(0, lambda: root.attributes("-fullscreen", True))
        root.after(0, loading.destroy)

    root.after(300, lambda: threading.Thread(target=run_recognition).start())


# ---------------- EXIT ----------------
def exit_app():
    root.destroy()
    


# ---------------- MAIN GUI ----------------
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