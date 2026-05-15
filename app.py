# ============================================================
# College0 — Main Application Entry Point
# File: app.py
# Run with: python3 app.py
# ============================================================

import customtkinter as ctk
from screens.login import LoginScreen

# ── APPEARANCE SETTINGS ──────────────────────────────────────
# "System" follows the OS dark/light mode preference
# You can also use "Dark" or "Light" explicitly
ctk.set_appearance_mode("System")

# "blue" is the default theme — options: "blue", "green", "dark-blue"
ctk.set_default_color_theme("blue")


class College0App(ctk.CTk):
    """
    The root application window.
    All screens are shown inside this window by swapping frames.
    We never open multiple windows — everything happens in one.

    The 'current_user' dict stores the logged-in user's data
    and is passed between screens so every screen knows who
    is logged in without re-querying the database.
    """

    def __init__(self):
        super().__init__()

        # ── WINDOW CONFIGURATION ─────────────────────────────
        self.title("College0 — Academic Management System")
        self.geometry("1100x700")
        self.minsize(900, 600)

        # Store the logged-in user here after login succeeds.
        # None means no user is logged in (showing public/login screens).
        self.current_user = None

        # ── GRID LAYOUT ───────────────────────────────────────
        # The window uses a 1x1 grid so the screen frame
        # always fills the entire window
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── START ON LOGIN SCREEN ─────────────────────────────
        self.show_login()

    def show_login(self):
        """Switch to the login screen."""
        self._clear_screen()
        frame = LoginScreen(self, self.on_login_success)
        frame.grid(row=0, column=0, sticky="nsew")

    def on_login_success(self, user_data):
        """
        Called by LoginScreen when login succeeds.
        user_data is the row returned by get_user_by_email().
        Stores the user and routes to the correct dashboard.
        """
        self.current_user = dict(user_data)  # convert Row to dict
        role = self.current_user['role']

        if role == 'student':
            self.show_student_dashboard()
        elif role == 'instructor':
            self.show_instructor_dashboard()
        elif role == 'registrar':
            self.show_registrar_dashboard()

    def show_student_dashboard(self):
        """Switch to the student dashboard."""
        self._clear_screen()
        from screens.dashboard_student import StudentDashboard
        frame = StudentDashboard(self, self.current_user, self.logout)
        frame.grid(row=0, column=0, sticky="nsew")

    def show_instructor_dashboard(self):
        """Switch to the instructor dashboard."""
        self._clear_screen()
        from screens.dashboard_instructor import InstructorDashboard
        frame = InstructorDashboard(self, self.current_user, self.logout)
        frame.grid(row=0, column=0, sticky="nsew")

    def show_registrar_dashboard(self):
        """Switch to the registrar dashboard."""
        self._clear_screen()
        from screens.dashboard_registrar import RegistrarDashboard
        frame = RegistrarDashboard(self, self.current_user, self.logout)
        frame.grid(row=0, column=0, sticky="nsew")

    def logout(self):
        """Clear the current user and return to login screen."""
        self.current_user = None
        self.show_login()

    def _clear_screen(self):
        """Remove all widgets from the window before showing a new screen."""
        for widget in self.winfo_children():
            widget.destroy()


# ── ENTRY POINT ───────────────────────────────────────────────
if __name__ == "__main__":
    app = College0App()
    app.mainloop()