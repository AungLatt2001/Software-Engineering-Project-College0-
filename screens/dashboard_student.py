# ============================================================
# College0 — Student Dashboard
# File: screens/dashboard_student.py
#
# What this screen shows:
#   - Welcome banner with student name, GPA, warnings
#   - Currently enrolled courses
#   - Navigation buttons to other features
# ============================================================

import customtkinter as ctk
from queries import (
    get_student_profile,
    get_available_sections,
    get_top_gpa_students,
    get_highest_rated_sections,
    get_lowest_rated_sections,
    enroll_student,
    add_to_waitlist
)


class StudentDashboard(ctk.CTkFrame):
    """
    Main dashboard shown to a logged-in student.

    Parameters:
        master       — the root app window
        user_data    — dict from the users table (from login)
        on_logout    — callback to return to login screen
    """

    def __init__(self, master, user_data, on_logout):
        super().__init__(master, fg_color="transparent")
        self.user_data  = user_data
        self.on_logout  = on_logout
        self.user_id    = user_data['user_id']

        # Load the full student profile (includes GPA, honors, etc.)
        self.profile = get_student_profile(self.user_id)

        self._build_ui()

    def _build_ui(self):
        """Build the student dashboard layout."""

        # ── OUTER GRID: sidebar + main content ───────────────
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(8, weight=1)

        # Sidebar: app name
        ctk.CTkLabel(
            sidebar,
            text="College0",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(24, 4))

        ctk.CTkLabel(
            sidebar,
            text="Student Portal",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).grid(row=1, column=0, padx=20, pady=(0, 24))

        # Sidebar: navigation buttons
        nav_items = [
            ("🏠  Dashboard",       self._show_home),
            ("📚  My Courses",       self._show_my_courses),
            ("➕  Register",         self._show_registration),
            ("⭐  Reviews",          self._show_reviews),
            ("🎓  Graduation",       self._show_graduation),
            ("🤖  AI Assistant",     self._show_ai),
        ]

        for i, (label, command) in enumerate(nav_items):
            ctk.CTkButton(
                sidebar,
                text=label,
                anchor="w",
                height=40,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray85", "gray25"),
                command=command
            ).grid(row=i + 2, column=0, padx=12, pady=2,
                   sticky="ew")

        # Sidebar: logout at bottom
        ctk.CTkButton(
            sidebar,
            text="🚪  Logout",
            anchor="w",
            height=40,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray85", "gray25"),
            command=self.on_logout
        ).grid(row=9, column=0, padx=12, pady=(0, 20), sticky="ew")

        # Main content area
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew",
                            padx=24, pady=24)
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(1, weight=1)

        # Start on the home view
        self._show_home()

    def _clear_main(self):
        """Remove all widgets from the main content area."""
        for w in self.main_area.winfo_children():
            w.destroy()

    def _show_home(self):
        """Home view — welcome banner + stats + public data."""
        self._clear_main()
        p = self.profile

        # Welcome banner
        banner = ctk.CTkFrame(self.main_area)
        banner.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        banner.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            banner,
            text=f"Welcome back, {p['first_name']} 👋",
            font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(16, 4), sticky="w")

        ctk.CTkLabel(
            banner,
            text=f"Student ID: {p['student_code']}",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        ).grid(row=1, column=0, padx=20, pady=(0, 16), sticky="w")

        # Stat cards row
        stats_frame = ctk.CTkFrame(self.main_area,
                                   fg_color="transparent")
        stats_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        for i in range(4):
            stats_frame.grid_columnconfigure(i, weight=1)

        stats = [
            ("Cumulative GPA",  f"{p['cumulative_gpa']:.2f}",  "#1F6AA5"),
            ("Semester GPA",    f"{p['semester_gpa']:.2f}",    "#2E8B57"),
            ("Warnings",        str(p['warning_count']),
             "#CC4444" if p['warning_count'] > 0 else "#444"),
            ("Honors",          str(p['honor_count']),         "#B8860B"),
        ]

        for col, (label, value, color) in enumerate(stats):
            card = ctk.CTkFrame(stats_frame)
            card.grid(row=0, column=col, padx=6, sticky="nsew")
            ctk.CTkLabel(
                card, text=value,
                font=ctk.CTkFont(size=28, weight="bold"),
                text_color=color
            ).grid(row=0, column=0, padx=16, pady=(16, 4))
            ctk.CTkLabel(
                card, text=label,
                font=ctk.CTkFont(size=11),
                text_color="gray"
            ).grid(row=1, column=0, padx=16, pady=(0, 16))

        # Public dashboard data
        public_frame = ctk.CTkFrame(self.main_area,
                                    fg_color="transparent")
        public_frame.grid(row=2, column=0, sticky="nsew")
        public_frame.grid_columnconfigure(0, weight=1)
        public_frame.grid_columnconfigure(1, weight=1)

        # Top GPA students
        gpa_box = ctk.CTkFrame(public_frame)
        gpa_box.grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        ctk.CTkLabel(
            gpa_box,
            text="🏆 Top GPA Students",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, padx=16, pady=(14, 8), sticky="w")

        top_students = get_top_gpa_students()
        for i, s in enumerate(top_students):
            ctk.CTkLabel(
                gpa_box,
                text=f"{i+1}. {s['first_name']} {s['last_name']} "
                     f"— {s['cumulative_gpa']:.2f}",
                font=ctk.CTkFont(size=12)
            ).grid(row=i+1, column=0, padx=16, pady=2, sticky="w")

        # Highest rated sections
        rated_box = ctk.CTkFrame(public_frame)
        rated_box.grid(row=0, column=1, padx=(10, 0), sticky="nsew")

        ctk.CTkLabel(
            rated_box,
            text="⭐ Highest Rated Courses",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, padx=16, pady=(14, 8), sticky="w")

        top_sections = get_highest_rated_sections()
        for i, s in enumerate(top_sections):
            ctk.CTkLabel(
                rated_box,
                text=f"{s['course_code']} — {s['avg_rating']} ★  "
                     f"({s['review_count']} reviews)",
                font=ctk.CTkFont(size=12)
            ).grid(row=i+1, column=0, padx=16, pady=2, sticky="w")

    def _show_my_courses(self):
        """Shows the student's current enrollments."""
        self._clear_main()

        ctk.CTkLabel(
            self.main_area,
            text="My Courses",
            font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, pady=(0, 16), sticky="w")

        sections = get_available_sections(1)  # semester_id=1

        # Filter to only the sections this student is enrolled in
        # In a full app, you would have a get_student_enrollments() query
        ctk.CTkLabel(
            self.main_area,
            text="Your enrolled sections are shown in the "
                 "registration screen.",
            text_color="gray"
        ).grid(row=1, column=0, sticky="w")

    def _show_registration(self):
        """Launch the course registration view inline."""
        self._clear_main()

        ctk.CTkLabel(
            self.main_area,
            text="Course Registration",
            font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, pady=(0, 6), sticky="w")

        ctk.CTkLabel(
            self.main_area,
            text="Click a course to register. "
                 "Full sections offer a waitlist.",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        ).grid(row=1, column=0, pady=(0, 16), sticky="w")

        # Result message label
        self.reg_result = ctk.CTkLabel(
            self.main_area, text="",
            font=ctk.CTkFont(size=13)
        )
        self.reg_result.grid(row=2, column=0, pady=(0, 12), sticky="w")

        # Scrollable frame for section cards
        scroll = ctk.CTkScrollableFrame(self.main_area, height=460)
        scroll.grid(row=3, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(3, weight=1)

        sections = get_available_sections(1)  # semester_id = 1

        for i, sec in enumerate(sections):
            card = ctk.CTkFrame(scroll)
            card.grid(row=i, column=0, sticky="ew",
                      padx=4, pady=6)
            card.grid_columnconfigure(1, weight=1)

            # Status color
            status_colors = {
                'open':      ("#2E8B57", "#2E8B57"),
                'full':      ("#CC4444", "#CC4444"),
                'cancelled': ("#888",    "#888"),
                'completed': ("#666",    "#666"),
            }
            sc = sec['status']
            color = status_colors.get(sc, ("#888", "#888"))

            # Course code + title
            ctk.CTkLabel(
                card,
                text=f"{sec['course_code']} — {sec['title']}",
                font=ctk.CTkFont(size=14, weight="bold")
            ).grid(row=0, column=0, padx=14, pady=(12, 2), sticky="w")

            # Details line
            ctk.CTkLabel(
                card,
                text=f"Instructor: {sec['instructor_name']}  |  "
                     f"Room: {sec['room'] or 'TBA'}  |  "
                     f"{'CORE' if sec['is_core'] else 'Elective'}",
                font=ctk.CTkFont(size=11),
                text_color="gray"
            ).grid(row=1, column=0, padx=14, pady=(0, 2), sticky="w")

            # Capacity line
            ctk.CTkLabel(
                card,
                text=f"Seats: {sec['current_enrollment']}"
                     f"/{sec['capacity']}  "
                     f"({sec['seats_remaining']} remaining)",
                font=ctk.CTkFont(size=11),
                text_color="gray"
            ).grid(row=2, column=0, padx=14, pady=(0, 12), sticky="w")

            # Status badge
            ctk.CTkLabel(
                card,
                text=sc.upper(),
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=color
            ).grid(row=0, column=1, padx=14, pady=(12, 2), sticky="e")

            # Action button
            if sc == 'open':
                btn = ctk.CTkButton(
                    card,
                    text="Register",
                    width=100, height=32,
                    command=lambda s=sec: self._try_enroll(s)
                )
            elif sc == 'full':
                btn = ctk.CTkButton(
                    card,
                    text="Join Waitlist",
                    width=120, height=32,
                    fg_color="#CC6600",
                    hover_color="#AA5500",
                    command=lambda s=sec: self._try_waitlist(s)
                )
            else:
                btn = ctk.CTkButton(
                    card,
                    text=sc.capitalize(),
                    width=100, height=32,
                    state="disabled"
                )

            btn.grid(row=1, column=1, rowspan=2,
                     padx=14, pady=8, sticky="e")

    def _try_enroll(self, section):
        """Called when student clicks Register on a section."""
        result = enroll_student(
            student_id  = self.user_id,
            section_id  = section['section_id'],
            semester_id = 1
        )

        if result['success']:
            self.reg_result.configure(
                text=f"✓ {result['message']}",
                text_color="#2E8B57"
            )
            # Refresh the section list to show updated seat counts
            self._show_registration()
        elif result.get('offer_waitlist'):
            self.reg_result.configure(
                text="Section is full. Click 'Join Waitlist' to queue.",
                text_color="#CC6600"
            )
        else:
            self.reg_result.configure(
                text=f"✗ {result['message']}",
                text_color="#CC4444"
            )

    def _try_waitlist(self, section):
        """Called when student clicks Join Waitlist."""
        result = add_to_waitlist(
            student_id = self.user_id,
            section_id = section['section_id']
        )

        if result['success']:
            self.reg_result.configure(
                text=f"✓ Added to waitlist at position #{result['position']}",
                text_color="#CC6600"
            )
        else:
            self.reg_result.configure(
                text=f"✗ {result['message']}",
                text_color="#CC4444"
            )

    def _show_reviews(self):
        self._clear_main()
        ctk.CTkLabel(
            self.main_area,
            text="Review Submission — coming in next build",
            font=ctk.CTkFont(size=16)
        ).grid(row=0, column=0, pady=20)

    def _show_graduation(self):
        from queries import check_graduation_eligibility
        self._clear_main()

        ctk.CTkLabel(
            self.main_area,
            text="Graduation Eligibility Check",
            font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, pady=(0, 20), sticky="w")

        result = check_graduation_eligibility(self.user_id)

        status_text = "✓ You are eligible to graduate!" \
                      if result['eligible'] \
                      else "✗ You do not yet meet graduation requirements."
        status_color = "#2E8B57" if result['eligible'] else "#CC4444"

        ctk.CTkLabel(
            self.main_area, text=status_text,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=status_color
        ).grid(row=1, column=0, pady=(0, 20), sticky="w")

        items = [
            ("Courses completed",
             f"{result['total_completed']} / 8  "
             f"(need {result['needs_courses']} more)"),
            ("Core courses completed",
             f"{result['core_completed']} / 4  "
             f"(need {result['needs_core']} more)"),
            ("Cumulative GPA",
             f"{result['cumulative_gpa']:.2f}  "
             f"({'✓ above 2.0' if result['gpa_ok'] else '✗ below 2.0'})"),
        ]

        for i, (label, value) in enumerate(items):
            row_frame = ctk.CTkFrame(self.main_area)
            row_frame.grid(row=i + 2, column=0,
                           sticky="ew", pady=4)
            row_frame.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                row_frame, text=label,
                font=ctk.CTkFont(size=13, weight="bold"),
                width=200, anchor="w"
            ).grid(row=0, column=0, padx=16, pady=12, sticky="w")
            ctk.CTkLabel(
                row_frame, text=value,
                font=ctk.CTkFont(size=13)
            ).grid(row=0, column=1, padx=16, pady=12, sticky="w")

    def _show_ai(self):
        self._clear_main()
        ctk.CTkLabel(
            self.main_area,
            text="AI Assistant — coming in next build",
            font=ctk.CTkFont(size=16)
        ).grid(row=0, column=0, pady=20)