import customtkinter as ctk
from queries import get_top_gpa_students, get_students_needing_standing_review

class RegistrarDashboard(ctk.CTkFrame):
    def __init__(self, master, user_data, on_logout):
        super().__init__(master, fg_color="transparent")
        self.user_data = user_data
        self.on_logout = on_logout
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
            text="Registrar Dashboard — Full System Access",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, padx=16, pady=16, sticky="w")

        ctk.CTkButton(
            header, text="Logout", width=100,
            command=self.on_logout
        ).grid(row=0, column=1, padx=16, sticky="e")

        # Academic standing panel
        content = ctk.CTkScrollableFrame(self)
        content.grid(row=1, column=0, sticky="nsew",
                     padx=24, pady=24)
        content.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            content,
            text="Academic Standing Review",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, pady=(0, 12), sticky="w")

        students = get_students_needing_standing_review()

        action_colors = {
            'TERMINATE':  "#CC4444",
            'WARNING':    "#CC6600",
            'HONOR_ROLL': "#2E8B57",
            'OK':         "gray",
        }

        for i, s in enumerate(students):
            card = ctk.CTkFrame(content)
            card.grid(row=i+1, column=0,
                      sticky="ew", pady=4)
            card.grid_columnconfigure(1, weight=1)

            color = action_colors.get(s['standing_action'], "gray")

            ctk.CTkLabel(
                card,
                text=s['full_name'],
                font=ctk.CTkFont(size=13, weight="bold")
            ).grid(row=0, column=0, padx=14, pady=10, sticky="w")

            ctk.CTkLabel(
                card,
                text=f"GPA: {s['cumulative_gpa']:.2f}  |  "
                     f"Warnings: {s['warning_count']}",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            ).grid(row=0, column=1, padx=14, pady=10)

            ctk.CTkLabel(
                card,
                text=s['standing_action'],
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=color
            ).grid(row=0, column=2, padx=14, pady=10, sticky="e")