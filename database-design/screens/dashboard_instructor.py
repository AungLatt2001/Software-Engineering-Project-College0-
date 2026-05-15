import customtkinter as ctk
from queries import get_instructor_profile, get_waitlist

class InstructorDashboard(ctk.CTkFrame):
    def __init__(self, master, user_data, on_logout):
        super().__init__(master, fg_color="transparent")
        self.user_data = user_data
        self.on_logout = on_logout
        self.profile   = get_instructor_profile(user_data['user_id'])
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 0))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text=f"Instructor Dashboard — "
                 f"{self.user_data['first_name']} "
                 f"{self.user_data['last_name']}",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, padx=16, pady=16, sticky="w")

        ctk.CTkButton(
            header, text="Logout", width=100,
            command=self.on_logout
        ).grid(row=0, column=1, padx=16, sticky="e")

        # Waitlist panel
        content = ctk.CTkFrame(self)
        content.grid(row=1, column=0, sticky="nsew",
                     padx=24, pady=24)

        ctk.CTkLabel(
            content,
            text="Waitlist for SEC-003 (CSC 21700)",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        waitlist = get_waitlist(3)  # section_id = 3

        if not waitlist:
            ctk.CTkLabel(
                content, text="No students on waitlist.",
                text_color="gray"
            ).grid(row=1, column=0, padx=16, pady=8, sticky="w")
        else:
            for i, entry in enumerate(waitlist):
                ctk.CTkLabel(
                    content,
                    text=f"#{entry['position']}  "
                         f"{entry['student_name']}  "
                         f"({entry['student_code']})",
                    font=ctk.CTkFont(size=13)
                ).grid(row=i+1, column=0,
                       padx=16, pady=4, sticky="w")

        ctk.CTkLabel(
            content,
            text="\nFull instructor features coming in next build.",
            text_color="gray", font=ctk.CTkFont(size=12)
        ).grid(row=10, column=0, padx=16, pady=8, sticky="w")