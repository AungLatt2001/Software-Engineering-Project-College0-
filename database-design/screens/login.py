# ============================================================
# College0 — Login Screen
# File: screens/login.py
#
# What this screen does:
#   1. Shows email + password fields
#   2. Calls get_user_by_email() to find the user
#   3. Compares the password (plain text for now — see note)
#   4. Checks account status (suspended/terminated blocks login)
#   5. Calls on_success(user_data) to hand off to the app
# ============================================================

import customtkinter as ctk
from queries import get_user_by_email

# NOTE ON PASSWORDS:
# In production you would use bcrypt to hash passwords.
# For this demo, we compare plain text against the stored hash.
# To make this work with your seed data, we need to update
# the seed passwords to plain text — see note at bottom of file.


class LoginScreen(ctk.CTkFrame):
    """
    The login screen frame.
    Shown when the app starts or after logout.

    Parameters:
        master      — the root app window (College0App)
        on_success  — callback function called when login works
                      receives the user row as its argument
    """

    def __init__(self, master, on_success):
        super().__init__(master, fg_color="transparent")
        self.on_success = on_success
        self._build_ui()

    def _build_ui(self):
        """Build all the widgets for the login screen."""

        # ── OUTER LAYOUT: left panel + right decorative panel ─
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left panel — the actual login form
        left = ctk.CTkFrame(self, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # Right panel — decorative banner
        right = ctk.CTkFrame(self, fg_color=("#1F6AA5", "#1F6AA5"),
                              corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # Right panel content
        ctk.CTkLabel(
            right,
            text="College0",
            font=ctk.CTkFont(size=42, weight="bold"),
            text_color="white"
        ).grid(row=0, column=0, pady=(0, 10))

        ctk.CTkLabel(
            right,
            text="AI-Enabled Academic\nManagement System",
            font=ctk.CTkFont(size=16),
            text_color="#CCDDFF",
            justify="center"
        ).grid(row=1, column=0, pady=(0, 40))

        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=0)
        right.grid_rowconfigure(2, weight=1)

        # ── LEFT PANEL: login form ────────────────────────────
        form = ctk.CTkFrame(left, fg_color="transparent")
        form.place(relx=0.5, rely=0.5, anchor="center")

        # Title
        ctk.CTkLabel(
            form,
            text="Welcome Back",
            font=ctk.CTkFont(size=28, weight="bold")
        ).grid(row=0, column=0, pady=(0, 6), sticky="w")

        ctk.CTkLabel(
            form,
            text="Sign in to continue",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        ).grid(row=1, column=0, pady=(0, 30), sticky="w")

        # Email field
        ctk.CTkLabel(form, text="Email address",
                     font=ctk.CTkFont(size=13)
                     ).grid(row=2, column=0, sticky="w", pady=(0, 4))

        self.email_entry = ctk.CTkEntry(
            form, width=320, height=40,
            placeholder_text="you@college0.edu"
        )
        self.email_entry.grid(row=3, column=0, pady=(0, 16))

        # Password field
        ctk.CTkLabel(form, text="Password",
                     font=ctk.CTkFont(size=13)
                     ).grid(row=4, column=0, sticky="w", pady=(0, 4))

        self.password_entry = ctk.CTkEntry(
            form, width=320, height=40,
            placeholder_text="Enter your password",
            show="•"   # hides characters as they are typed
        )
        self.password_entry.grid(row=5, column=0, pady=(0, 8))

        # Error message label (hidden until needed)
        self.error_label = ctk.CTkLabel(
            form, text="", text_color="#FF4444",
            font=ctk.CTkFont(size=12)
        )
        self.error_label.grid(row=6, column=0, pady=(0, 12))

        # Login button
        self.login_btn = ctk.CTkButton(
            form,
            text="Sign In",
            width=320, height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._attempt_login
        )
        self.login_btn.grid(row=7, column=0, pady=(0, 20))

        # Demo accounts hint
        ctk.CTkLabel(
            form,
            text="Demo accounts — email: any from seed data  |  password: demo123",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).grid(row=8, column=0)

        # Bind Enter key to login attempt
        self.email_entry.bind("<Return>", lambda e: self._attempt_login())
        self.password_entry.bind("<Return>", lambda e: self._attempt_login())

    def _attempt_login(self):
        """
        Called when the user clicks Sign In or presses Enter.
        Validates credentials and calls on_success if correct.
        """
        email    = self.email_entry.get().strip()
        password = self.password_entry.get().strip()

        # Basic validation — fields cannot be empty
        if not email or not password:
            self._show_error("Please enter both email and password.")
            return

        # Look up the user in the database
        user = get_user_by_email(email)

        if user is None:
            self._show_error("No account found with that email.")
            return

        # Check password
        # For demo: we compare against "demo123" for all users.
        # In production: use bcrypt.checkpw(password, user['password_hash'])
        if password != "demo123":
            self._show_error("Incorrect password.")
            return

        # Check account status before allowing in
        if user['status'] == 'suspended':
            self._show_error(
                "Your account is suspended. "
                "Please pay your fine and contact the registrar."
            )
            return

        if user['status'] == 'terminated':
            self._show_error(
                "Your account has been terminated. "
                "Please contact the registrar."
            )
            return

        # All checks passed — hand off to the app
        self.on_success(user)

    def _show_error(self, message):
        """Display an error message below the password field."""
        self.error_label.configure(text=message)