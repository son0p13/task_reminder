import calendar
import ctypes
from datetime import datetime
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from task_manager import TaskManager, parse_deadline_datetime
from config_manager import ConfigManager
from autostart_manager import AutoStartManager
from notification_service import NotificationService
from reminder_engine import ReminderEngine, get_task_status_info
from tray_manager import TrayManager
from settings_dialog import SettingsDialog
from multi_reminder_dialog import MultiReminderDialog, format_reminders_text

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


class TodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Reminder - Quản Lý & Nhắc Nhở Công Việc")

        # Khởi tạo các module nghiệp vụ và dịch vụ
        self.manager = TaskManager()
        self.config_manager = ConfigManager()
        self.notification_service = NotificationService(app_id="Task Reminder")
        self.reminder_engine = ReminderEngine(
            self.manager, self.config_manager, self.notification_service
        )

        self._is_terminating = False
        self.timer_job = None
        self.cal_win = None
        self.sort_col = "id"
        self.sort_desc = False

        # Quản lý mốc nhắc nhở nhiều lần của công việc đang tạo/sửa
        self.current_task_reminders = None  # None = theo cài đặt chung

        self.col_titles = {
            "id": "ID",
            "title": "Tên công việc",
            "priority": "Mức ưu tiên",
            "deadline": "Hạn chót",
            "time_left": "Thời gian còn lại",
            "status": "Trạng thái",
        }

        # Thiết lập cửa sổ, kiểu dáng và menu
        self._setup_window_geometry()
        self._setup_window_icon()
        self._setup_styles()
        self._create_menu_bar()
        self._create_widgets()

        # Khởi động biểu tượng khay hệ thống (System Tray)
        self._setup_tray_manager()

        # Nạp dữ liệu và đặt lịch kiểm tra deadline
        self._update_reminder_display()
        self.refresh_table()
        self._schedule_periodic_check()

        # Xử lý sự kiện đóng cửa sổ [X]
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_window)

        # Kiểm tra tham số dòng lệnh khởi động cùng Windows
        if "--startup" in sys.argv or "--minimized" in sys.argv:
            self.root.withdraw()
            self.notification_service.notify_info(
                "Task Reminder",
                "Đã tự động khởi động cùng Windows và đang chạy ngầm trong khay hệ thống.",
            )

    def _setup_window_geometry(self):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = max(960, int(screen_w * 0.66))
        win_h = max(660, int(screen_h * 0.74))
        pos_x = (screen_w - win_w) // 2
        pos_y = (screen_h - win_h) // 2
        self.root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        self.root.minsize(880, 540)
        self.root.configure(bg="#f4f6f9")

    def _setup_window_icon(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ico_path = os.path.join(base_dir, "app_icon.ico")
        png_path = os.path.join(base_dir, "app_icon.png")
        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass
        elif os.path.exists(png_path):
            try:
                photo = tk.PhotoImage(file=png_path)
                self.root.iconphoto(False, photo)
            except Exception:
                pass

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Treeview", font=("Segoe UI", 10), rowheight=32)
        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 10, "bold"),
            background="#e2e8f0",
            foreground="#1e293b",
            padding=(6, 6),
        )
        style.map("Treeview.Heading", background=[("active", "#cbd5e1")])
        style.map(
            "Treeview",
            background=[("selected", "#bfdbfe")],
            foreground=[("selected", "#0f172a")],
        )

    def _setup_tray_manager(self):
        self.tray_manager = TrayManager(
            on_open=self.restore_window_from_tray,
            on_check_now=self.check_deadlines_from_tray,
            on_settings=self.open_settings_from_tray,
            on_toggle_startup=self.toggle_autostart_from_tray,
            on_exit=self.exit_application_from_tray,
            is_startup_enabled=AutoStartManager.is_autostart_enabled,
        )
        self.tray_manager.start()

    def _create_menu_bar(self):
        menubar = tk.Menu(self.root)

        # Menu Hệ thống
        menu_system = tk.Menu(menubar, tearoff=0)
        menu_system.add_command(
            label="⚙️ Cài đặt hệ thống & Nhắc nhở", command=self.open_settings_dialog
        )
        menu_system.add_command(
            label="🚀 Tự khởi động cùng Windows", command=self.toggle_autostart
        )
        menu_system.add_command(
            label="📤 Xuất danh sách ra CSV (Excel)...", command=self.on_export_csv
        )
        menu_system.add_separator()
        menu_system.add_command(
            label="📥 Thu nhỏ xuống khay hệ thống", command=self.minimize_to_tray
        )
        menu_system.add_command(
            label="❌ Thoát ứng dụng hoàn toàn", command=self.exit_application
        )
        menubar.add_cascade(label="📁 Hệ thống", menu=menu_system)

        # Menu Quản lý công việc
        menu_tasks = tk.Menu(menubar, tearoff=0)
        menu_tasks.add_command(label="➕ Thêm công việc mới", command=self.on_add_task)
        menu_tasks.add_command(label="💾 Cập nhật việc đang chọn", command=self.on_update_task)
        menu_tasks.add_command(
            label="✔ Đánh dấu Xong / Chưa xong", command=self.on_toggle_task
        )
        menu_tasks.add_command(label="🗑 Xóa công việc", command=self.on_delete_task)
        menu_tasks.add_separator()
        menu_tasks.add_command(
            label="🔔 Quét kiểm tra deadline ngay (F5)", command=self.on_manual_check_deadlines
        )
        menubar.add_cascade(label="📋 Quản lý", menu=menu_tasks)

        # Menu Trợ giúp
        menu_help = tk.Menu(menubar, tearoff=0)
        menu_help.add_command(label="💡 Hướng dẫn sử dụng", command=self.show_user_guide)
        menu_help.add_command(label="ℹ️ Giới thiệu đề tài", command=self.show_about)
        menubar.add_cascade(label="❓ Trợ giúp", menu=menu_help)

        self.root.config(menu=menubar)
        self.root.bind("<F5>", lambda e: self.on_manual_check_deadlines())

    def _create_widgets(self):
        # 1. Header Bar
        header = tk.Frame(self.root, bg="#2563eb", padx=16, pady=8)
        header.pack(fill=tk.X)

        lbl_title = tk.Label(
            header,
            text="📋 QUẢN LÝ CÔNG VIỆC (TASK REMINDER)",
            font=("Segoe UI", 14, "bold"),
            bg="#2563eb",
            fg="white",
        )
        lbl_title.pack(side=tk.LEFT, pady=2)

        # Nút tiện ích bên phải header
        btn_box_header = tk.Frame(header, bg="#2563eb")
        btn_box_header.pack(side=tk.RIGHT)

        tk.Button(
            btn_box_header,
            text="🔔 Quét deadline",
            font=("Segoe UI", 9, "bold"),
            bg="#1d4ed8",
            fg="white",
            relief=tk.FLAT,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.on_manual_check_deadlines,
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_box_header,
            text="⚙️ Cài đặt",
            font=("Segoe UI", 9, "bold"),
            bg="#1e40af",
            fg="white",
            relief=tk.FLAT,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.open_settings_dialog,
        ).pack(side=tk.LEFT, padx=4)

        self.tray_on_close_var = tk.BooleanVar(
            value=self.config_manager.get("minimize_to_tray_on_close", True)
        )
        chk_tray = tk.Checkbutton(
            btn_box_header,
            text="Chạy ngầm khi tắt",
            variable=self.tray_on_close_var,
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="white",
            selectcolor="#1e40af",
            activebackground="#2563eb",
            activeforeground="white",
            cursor="hand2",
            command=self._on_toggle_tray_on_close,
        )
        chk_tray.pack(side=tk.LEFT, padx=(8, 0))

        # 2. Input Frame
        input_frame = tk.LabelFrame(
            self.root,
            text=" Thông tin công việc ",
            font=("Segoe UI", 10, "bold"),
            bg="#f4f6f9",
            fg="#1e293b",
            padx=12,
            pady=8,
        )
        input_frame.pack(fill=tk.X, padx=15, pady=(10, 4))

        # Dòng 0: Tên công việc
        tk.Label(input_frame, text="Tên công việc:", font=("Segoe UI", 10), bg="#f4f6f9").grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.title_var = tk.StringVar()
        self.entry_title = tk.Entry(
            input_frame, textvariable=self.title_var, font=("Segoe UI", 10), width=48
        )
        self.entry_title.grid(row=0, column=1, columnspan=5, sticky="we", padx=8, pady=4)
        self.entry_title.bind("<Return>", lambda event: self.on_add_task())

        # Dòng 1: Mức ưu tiên | Hạn chót | Nhắc nhở nhiều lần
        tk.Label(input_frame, text="Mức ưu tiên:", font=("Segoe UI", 10), bg="#f4f6f9").grid(
            row=1, column=0, sticky="w", pady=4
        )
        self.priority_var = tk.StringVar(value="Trung bình")
        self.combo_priority = ttk.Combobox(
            input_frame,
            textvariable=self.priority_var,
            values=["Cao", "Trung bình", "Thấp"],
            state="readonly",
            font=("Segoe UI", 10),
            width=12,
        )
        self.combo_priority.grid(row=1, column=1, sticky="w", padx=8, pady=4)

        tk.Label(input_frame, text="Hạn chót:", font=("Segoe UI", 10), bg="#f4f6f9").grid(
            row=1, column=2, sticky="e", pady=4
        )
        deadline_box = tk.Frame(input_frame, bg="#f4f6f9")
        deadline_box.grid(row=1, column=3, sticky="w", padx=8, pady=4)

        now_str = datetime.now().strftime("%d/%m/%Y 23:59")
        self.deadline_var = tk.StringVar(value=now_str)
        self.entry_deadline = tk.Entry(
            deadline_box, textvariable=self.deadline_var, font=("Segoe UI", 10), width=16
        )
        self.entry_deadline.pack(side=tk.LEFT)

        tk.Button(
            deadline_box,
            text="📅 Chọn lịch",
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg="#1e293b",
            padx=6,
            cursor="hand2",
            command=self.open_date_picker,
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Khung chọn nhiều mốc nhắc nhở (3 ngày, 1 ngày, 1 tiếng,...)
        tk.Label(input_frame, text="Nhắc nhở:", font=("Segoe UI", 10), bg="#f4f6f9").grid(
            row=1, column=4, sticky="e", pady=4
        )
        reminder_box = tk.Frame(input_frame, bg="#f4f6f9")
        reminder_box.grid(row=1, column=5, sticky="w", padx=8, pady=4)

        self.reminder_display_var = tk.StringVar(value="Theo cài đặt chung")
        self.entry_reminder_disp = tk.Entry(
            reminder_box,
            textvariable=self.reminder_display_var,
            font=("Segoe UI", 9),
            width=26,
            state="readonly",
            cursor="hand2",
        )
        self.entry_reminder_disp.pack(side=tk.LEFT)
        self.entry_reminder_disp.bind("<Button-1>", lambda e: self.open_multi_reminder_dialog())

        tk.Button(
            reminder_box,
            text="⚙️ Chọn mốc",
            font=("Segoe UI", 9, "bold"),
            bg="#e0e7ff",
            fg="#3730a3",
            padx=6,
            cursor="hand2",
            command=self.open_multi_reminder_dialog,
        ).pack(side=tk.LEFT, padx=(5, 0))

        input_frame.columnconfigure(1, weight=1)

        # Dòng 2: Nút thao tác
        btn_input_box = tk.Frame(input_frame, bg="#f4f6f9")
        btn_input_box.grid(row=2, column=0, columnspan=6, sticky="w", pady=(8, 2))

        tk.Button(
            btn_input_box,
            text="➕ Thêm mới",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="white",
            width=14,
            pady=3,
            cursor="hand2",
            command=self.on_add_task,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_input_box,
            text="💾 Cập nhật",
            font=("Segoe UI", 9, "bold"),
            bg="#0d9488",
            fg="white",
            width=14,
            pady=3,
            cursor="hand2",
            command=self.on_update_task,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_input_box,
            text="🗑 Xóa việc",
            font=("Segoe UI", 9, "bold"),
            bg="#dc2626",
            fg="white",
            width=14,
            pady=3,
            cursor="hand2",
            command=self.on_delete_task,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_input_box,
            text="🧹 Làm mới ô nhập",
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg="#1e293b",
            width=14,
            pady=3,
            cursor="hand2",
            command=self.clear_inputs,
        ).pack(side=tk.LEFT)

        # 3. Filter Bar
        filter_frame = tk.Frame(self.root, bg="#f4f6f9")
        filter_frame.pack(fill=tk.X, padx=15, pady=4)

        tk.Label(filter_frame, text="🔍 Tìm kiếm:", font=("Segoe UI", 10), bg="#f4f6f9").pack(
            side=tk.LEFT
        )
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_table())
        tk.Entry(filter_frame, textvariable=self.search_var, font=("Segoe UI", 10), width=24).pack(
            side=tk.LEFT, padx=(6, 16)
        )

        tk.Label(filter_frame, text="Lọc trạng thái:", font=("Segoe UI", 10), bg="#f4f6f9").pack(
            side=tk.LEFT
        )
        self.filter_var = tk.StringVar(value="Tất cả")
        combo_filter = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_var,
            values=["Tất cả", "Chưa xong", "Sắp đến hạn", "Quá hạn", "Đã xong"],
            state="readonly",
            font=("Segoe UI", 10),
            width=14,
        )
        combo_filter.pack(side=tk.LEFT, padx=6)
        combo_filter.bind("<<ComboboxSelected>>", lambda event: self.refresh_table())

        # 4. Table Frame
        table_frame = tk.Frame(self.root, bg="#f4f6f9")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=4)

        columns = ("id", "title", "priority", "deadline", "time_left", "status")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse", height=8
        )

        for col_name in columns:
            self.tree.heading(
                col_name,
                text=self.col_titles[col_name],
                command=lambda c=col_name: self.on_sort_column(c),
            )
        self._update_column_headers()

        self.tree.column("id", width=55, anchor="center")
        self.tree.column("title", width=330, anchor="w")
        self.tree.column("priority", width=105, anchor="center")
        self.tree.column("deadline", width=135, anchor="center")
        self.tree.column("time_left", width=135, anchor="center")
        self.tree.column("status", width=125, anchor="center")

        # Cấu hình màu sắc nhãn (tags)
        self.tree.tag_configure(
            "overdue",
            foreground="#b91c1c",
            background="#fee2e2",
            font=("Segoe UI", 10, "bold"),
        )
        self.tree.tag_configure(
            "due_soon",
            foreground="#b45309",
            background="#fef3c7",
            font=("Segoe UI", 10, "bold"),
        )
        self.tree.tag_configure("done", foreground="#64748b", background="#f8fafc")
        self.tree.tag_configure("pending", foreground="#0f172a")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Context Menu chuột phải
        self.context_menu = tk.Menu(self.root, tearoff=0, font=("Segoe UI", 9))
        self.context_menu.add_command(
            label="✔ Đánh dấu Xong / Chưa xong", command=self.on_toggle_task
        )
        self.context_menu.add_command(
            label="🔔 Tùy chỉnh mốc nhắc việc này", command=self.open_multi_reminder_dialog
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="🗑 Xóa công việc này", foreground="#dc2626", command=self.on_delete_task
        )

        self.tree.bind("<<TreeviewSelect>>", self.on_select_row)
        self.tree.bind("<Double-1>", lambda event: self.on_toggle_task())
        self.tree.bind("<Delete>", lambda event: self.on_delete_task())
        self.tree.bind("<Button-3>", self.on_right_click_row)

        # 5. Bottom Frame
        bottom_frame = tk.Frame(self.root, bg="#f4f6f9", pady=8)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15)

        tk.Button(
            bottom_frame,
            text="✔ Đánh dấu Xong / Chưa xong",
            font=("Segoe UI", 9, "bold"),
            bg="#16a34a",
            fg="white",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.on_toggle_task,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            bottom_frame,
            text="Dọn việc đã xong",
            font=("Segoe UI", 9),
            bg="#f59e0b",
            fg="white",
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.on_clear_completed,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            bottom_frame,
            text="Xóa tất cả",
            font=("Segoe UI", 9),
            bg="#7f1d1d",
            fg="white",
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.on_clear_all,
        ).pack(side=tk.LEFT)

        self.lbl_stats = tk.Label(
            bottom_frame,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg="#f4f6f9",
            fg="#1e293b",
        )
        self.lbl_stats.pack(side=tk.RIGHT)

    def _update_reminder_display(self):
        """Cập nhật nhãn hiển thị các mốc nhắc nhở của công việc."""
        default_reminders = self.config_manager.get("default_reminders", [1440, 60, 30])
        default_summary = format_reminders_text(default_reminders)
        text = format_reminders_text(self.current_task_reminders, default_summary=default_summary)
        self.reminder_display_var.set(text)

    def open_multi_reminder_dialog(self):
        """Mở popup chọn nhiều mốc nhắc nhở (3 ngày, 1 ngày, 1 tiếng,...)."""
        default_reminders = self.config_manager.get("default_reminders", [1440, 60, 30])
        MultiReminderDialog(
            parent=self.root,
            current_reminders=self.current_task_reminders,
            on_apply=self._on_apply_reminders,
            default_reminders=default_reminders,
        )

    def _on_apply_reminders(self, selected_reminders):
        self.current_task_reminders = selected_reminders
        self._update_reminder_display()

    def _schedule_periodic_check(self):
        """Lên lịch tự động kiểm tra deadline theo chu kỳ đã cấu hình."""
        if self._is_terminating:
            return

        interval_sec = self.config_manager.get("check_interval_seconds", 30)
        self.reminder_engine.check_deadlines()
        self.refresh_table()

        default_reminders = self.config_manager.get("default_reminders", [1440, 60, 30])
        stats = self.manager.get_detailed_statistics(default_reminders=default_reminders)
        self.tray_manager.update_tooltip(
            pending_count=stats["pending"], overdue_count=stats["overdue"]
        )

        self.timer_job = self.root.after(interval_sec * 1000, self._schedule_periodic_check)

    def on_manual_check_deadlines(self):
        """Kích hoạt kiểm tra deadline thủ công."""
        alerts = self.reminder_engine.check_deadlines()
        self.refresh_table()
        if alerts:
            count = len(alerts)
            messagebox.showinfo(
                "Quét Deadline",
                f"Đã phát hiện và gửi thông báo nhắc nhở cho {count} công việc sắp hoặc quá hạn!",
            )
        else:
            messagebox.showinfo(
                "Quét Deadline",
                "Tất cả công việc đều trong tiến độ bình thường, chưa có việc nào sắp hoặc quá hạn.",
            )

    def open_date_picker(self):
        """Mở bộ chọn ngày và giờ hiện đại."""
        if self.cal_win is not None and self.cal_win.winfo_exists():
            self.cal_win.lift()
            self.cal_win.focus_force()
            return

        today = datetime.now()
        cur_text = self.deadline_var.get().strip()
        parsed_dt = parse_deadline_datetime(cur_text)
        init_dt = parsed_dt if parsed_dt is not None else today

        state = {
            "year": init_dt.year,
            "month": init_dt.month,
            "selected_day": init_dt.day,
            "hour": init_dt.hour,
            "minute": init_dt.minute,
        }

        win = tk.Toplevel(self.root)
        win.title("Chọn Hạn Chót (Deadline)")
        win.resizable(False, False)
        win.configure(bg="#ffffff", padx=12, pady=10)
        win.transient(self.root)
        self.cal_win = win

        x = self.entry_deadline.winfo_rootx()
        y = self.entry_deadline.winfo_rooty() + self.entry_deadline.winfo_height() + 4
        win.geometry(f"+{x}+{y}")

        top_bar = tk.Frame(win, bg="#ffffff")
        top_bar.pack(fill=tk.X, pady=(0, 8))

        month_var = tk.StringVar(value=f"Tháng {state['month']}")
        year_var = tk.StringVar(value=str(state["year"]))

        days_frame = tk.Frame(win, bg="#ffffff")
        days_frame.pack()

        def apply_selection():
            try:
                h = int(sp_hour.get())
                m = int(sp_min.get())
                h = max(0, min(23, h))
                m = max(0, min(59, m))
            except ValueError:
                h, m = 23, 59

            d = state["selected_day"]
            mo = state["month"]
            y = state["year"]
            self.deadline_var.set(f"{d:02d}/{mo:02d}/{y:04d} {h:02d}:{m:02d}")
            win.destroy()

        def set_preset_time(h, m):
            sp_hour.delete(0, tk.END)
            sp_hour.insert(0, f"{h:02d}")
            sp_min.delete(0, tk.END)
            sp_min.insert(0, f"{m:02d}")

        def render_days():
            for widget in days_frame.winfo_children():
                widget.destroy()

            weekdays = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
            for col, name in enumerate(weekdays):
                fg_color = "#dc2626" if col == 6 else "#475569"
                tk.Label(
                    days_frame,
                    text=name,
                    font=("Segoe UI", 9, "bold"),
                    bg="#ffffff",
                    fg=fg_color,
                    width=4,
                ).grid(row=0, column=col, pady=(0, 4))

            weeks = calendar.monthcalendar(state["year"], state["month"])
            for r_idx, week in enumerate(weeks, start=1):
                for c_idx, day in enumerate(week):
                    if day == 0:
                        tk.Label(days_frame, text="", bg="#ffffff", width=4).grid(
                            row=r_idx, column=c_idx
                        )
                        continue

                    is_selected = (
                        day == state["selected_day"]
                        and state["month"] == init_dt.month
                        and state["year"] == init_dt.year
                    )
                    is_today = (
                        day == today.day
                        and state["month"] == today.month
                        and state["year"] == today.year
                    )

                    bg_btn = "#f8fafc"
                    fg_btn = "#dc2626" if c_idx == 6 else "#0f172a"
                    if is_selected:
                        bg_btn = "#2563eb"
                        fg_btn = "#ffffff"
                    elif is_today:
                        bg_btn = "#dbeafe"
                        fg_btn = "#1d4ed8"

                    def on_day_click(d=day):
                        state["selected_day"] = d
                        render_days()

                    tk.Button(
                        days_frame,
                        text=str(day),
                        font=("Segoe UI", 9, "bold" if (is_selected or is_today) else "normal"),
                        bg=bg_btn,
                        fg=fg_btn,
                        relief=tk.FLAT,
                        width=4,
                        pady=3,
                        cursor="hand2",
                        command=on_day_click,
                    ).grid(row=r_idx, column=c_idx, padx=1, pady=1)

        def on_change_month_year(*args):
            try:
                m_val = int(month_var.get().replace("Tháng ", ""))
                y_val = int(year_var.get())
                if 1 <= m_val <= 12 and 1900 <= y_val <= 2100:
                    state["month"] = m_val
                    state["year"] = y_val
                    render_days()
            except ValueError:
                pass

        def shift_month(delta):
            m = state["month"] + delta
            y = state["year"]
            if m < 1:
                m = 12
                y -= 1
            elif m > 12:
                m = 1
                y += 1
            state["month"] = m
            state["year"] = y
            month_var.set(f"Tháng {m}")
            year_var.set(str(y))
            render_days()

        tk.Button(
            top_bar,
            text="◀",
            font=("Segoe UI", 9, "bold"),
            bg="#f1f5f9",
            relief=tk.FLAT,
            width=3,
            cursor="hand2",
            command=lambda: shift_month(-1),
        ).pack(side=tk.LEFT)

        cb_month = ttk.Combobox(
            top_bar,
            textvariable=month_var,
            values=[f"Tháng {i}" for i in range(1, 13)],
            state="readonly",
            font=("Segoe UI", 9),
            width=9,
        )
        cb_month.pack(side=tk.LEFT, padx=5)
        cb_month.bind("<<ComboboxSelected>>", on_change_month_year)

        sp_year = tk.Spinbox(
            top_bar,
            from_=2020,
            to=2035,
            textvariable=year_var,
            font=("Segoe UI", 9),
            width=6,
            command=on_change_month_year,
        )
        sp_year.pack(side=tk.LEFT, padx=(0, 5))
        sp_year.bind("<Return>", on_change_month_year)

        tk.Button(
            top_bar,
            text="▶",
            font=("Segoe UI", 9, "bold"),
            bg="#f1f5f9",
            relief=tk.FLAT,
            width=3,
            cursor="hand2",
            command=lambda: shift_month(1),
        ).pack(side=tk.LEFT)

        render_days()

        time_frame = tk.LabelFrame(
            win, text=" Giờ đến hạn ", font=("Segoe UI", 9, "bold"), bg="#ffffff", padx=8, pady=6
        )
        time_frame.pack(fill=tk.X, pady=(8, 4))

        tf_spin = tk.Frame(time_frame, bg="#ffffff")
        tf_spin.pack()

        tk.Label(tf_spin, text="Giờ:", font=("Segoe UI", 9), bg="#ffffff").pack(side=tk.LEFT)
        sp_hour = tk.Spinbox(
            tf_spin, from_=0, to=23, format="%02.0f", width=4, font=("Segoe UI", 10)
        )
        sp_hour.delete(0, tk.END)
        sp_hour.insert(0, f"{state['hour']:02d}")
        sp_hour.pack(side=tk.LEFT, padx=(4, 8))

        tk.Label(tf_spin, text="Phút:", font=("Segoe UI", 9), bg="#ffffff").pack(side=tk.LEFT)
        sp_min = tk.Spinbox(
            tf_spin, from_=0, to=59, format="%02.0f", width=4, font=("Segoe UI", 10)
        )
        sp_min.delete(0, tk.END)
        sp_min.insert(0, f"{state['minute']:02d}")
        sp_min.pack(side=tk.LEFT, padx=4)

        preset_frame = tk.Frame(time_frame, bg="#ffffff")
        preset_frame.pack(pady=(6, 2))

        for lbl, h, m in [
            ("23:59 (Cuối ngày)", 23, 59),
            ("17:00 (Tan sở)", 17, 0),
            ("12:00 (Trưa)", 12, 0),
            ("08:30 (Sáng)", 8, 30),
        ]:
            tk.Button(
                preset_frame,
                text=lbl,
                font=("Segoe UI", 8),
                bg="#f1f5f9",
                relief=tk.FLAT,
                cursor="hand2",
                command=lambda h=h, m=m: set_preset_time(h, m),
            ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            win,
            text="✔ Chọn ngày & giờ này",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="white",
            relief=tk.FLAT,
            pady=5,
            cursor="hand2",
            command=apply_selection,
        ).pack(fill=tk.X, pady=(6, 0))

    def _validate_inputs(self):
        title = self.title_var.get().strip()
        deadline = self.deadline_var.get().strip()

        if not title:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập tên công việc!")
            self.entry_title.focus_set()
            return False

        if deadline:
            dt = parse_deadline_datetime(deadline)
            if dt is None:
                messagebox.showwarning(
                    "Sai định dạng hạn chót",
                    "Hạn chót cần đúng định dạng 'dd/mm/yyyy' hoặc 'dd/mm/yyyy HH:MM'!\nVí dụ: 25/12/2026 17:30",
                )
                self.entry_deadline.focus_set()
                return False

        return True

    def _get_selected_task_id(self):
        selected = self.tree.selection()
        if not selected:
            return None
        values = self.tree.item(selected[0], "values")
        return int(values[0])

    def on_add_task(self):
        if not self._validate_inputs():
            return

        self.manager.add_task(
            title=self.title_var.get(),
            priority=self.priority_var.get(),
            deadline=self.deadline_var.get(),
            reminders=self.current_task_reminders,
        )
        self.clear_inputs()
        self.refresh_table()

    def on_update_task(self):
        task_id = self._get_selected_task_id()
        if task_id is None:
            messagebox.showinfo("Chưa chọn việc", "Hãy chọn một công việc trong bảng để cập nhật!")
            return

        if not self._validate_inputs():
            return

        self.manager.update_task(
            task_id=task_id,
            new_title=self.title_var.get(),
            new_priority=self.priority_var.get(),
            new_deadline=self.deadline_var.get(),
            new_reminders=self.current_task_reminders,
        )
        self.reminder_engine.reset_task_notification(task_id)
        self.refresh_table()
        messagebox.showinfo("Thành công", "Đã cập nhật thông tin công việc và các mốc nhắc nhở!")

    def on_toggle_task(self):
        task_id = self._get_selected_task_id()
        if task_id is None:
            messagebox.showinfo("Chưa chọn việc", "Hãy chọn một công việc để đánh dấu!")
            return

        self.manager.toggle_task(task_id)
        self.reminder_engine.reset_task_notification(task_id)
        self.refresh_table()

    def on_delete_task(self):
        task_id = self._get_selected_task_id()
        if task_id is None:
            messagebox.showinfo("Chưa chọn việc", "Hãy chọn một công việc cần xóa!")
            return

        confirm = messagebox.askyesno("Xác nhận xóa", "Bạn có chắc muốn xóa công việc này không?")
        if confirm:
            self.manager.delete_task(task_id)
            self.reminder_engine.reset_task_notification(task_id)
            self.clear_inputs()
            self.refresh_table()

    def on_clear_completed(self):
        _, done_count, _ = self.manager.get_statistics()
        if done_count == 0:
            messagebox.showinfo("Thông báo", "Hiện chưa có công việc nào hoàn thành để dọn!")
            return

        confirm = messagebox.askyesno(
            "Xác nhận", f"Bạn muốn xóa toàn bộ {done_count} công việc đã hoàn thành?"
        )
        if confirm:
            self.manager.clear_completed()
            self.clear_inputs()
            self.refresh_table()

    def on_clear_all(self):
        total_count, _, _ = self.manager.get_statistics()
        if total_count == 0:
            messagebox.showinfo("Thông báo", "Danh sách hiện đang trống!")
            return

        confirm = messagebox.askyesno(
            "Xác nhận xóa tất cả",
            f"Bạn có chắc chắn muốn xóa toàn bộ {total_count} công việc không?",
        )
        if confirm:
            self.manager.clear_all()
            self.reminder_engine.clear_cache()
            self.clear_inputs()
            self.refresh_table()

    def on_export_csv(self):
        """Xuất toàn bộ danh sách công việc ra file CSV cho Microsoft Excel."""
        if not self.manager.tasks:
            messagebox.showinfo("Thông báo", "Danh sách công việc đang trống, không có dữ liệu để xuất!")
            return

        init_name = f"Danh_sach_cong_viec_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Tệp CSV (Excel)", "*.csv"), ("Tất cả các tệp", "*.*")],
            initialfile=init_name,
            title="Xuất Danh Sách Công Việc Ra CSV",
        )
        if filepath:
            try:
                self.manager.export_to_csv(filepath)
                messagebox.showinfo(
                    "Xuất thành công",
                    f"Đã xuất danh sách công việc thành công ra file:\n{filepath}\n\n(Tệp được mã hóa UTF-8 with BOM hiển thị tiếng Việt hoàn hảo trên Excel).",
                )
            except Exception as e:
                messagebox.showerror("Lỗi xuất file", f"Không thể xuất file: {e}")

    def on_right_click_row(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
            self.on_select_row(None)
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def on_select_row(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        task_id = int(values[0])
        task = self.manager.find_task_by_id(task_id)
        if task:
            self.title_var.set(task.get("title", ""))
            self.priority_var.set(task.get("priority", "Trung bình"))
            self.deadline_var.set(task.get("deadline", ""))

            # Nạp mốc nhắc nhở của công việc
            if "reminders" in task:
                self.current_task_reminders = task["reminders"]
            elif task.get("reminder_minutes") is not None:
                val = int(task["reminder_minutes"])
                self.current_task_reminders = [val] if val > 0 else []
            else:
                self.current_task_reminders = None

            self._update_reminder_display()

    def clear_inputs(self):
        self.title_var.set("")
        self.priority_var.set("Trung bình")
        self.deadline_var.set(datetime.now().strftime("%d/%m/%Y 23:59"))
        self.current_task_reminders = None
        self._update_reminder_display()
        self.tree.selection_remove(self.tree.selection())
        self.entry_title.focus_set()

    def _update_column_headers(self):
        for col_name, base_title in self.col_titles.items():
            if col_name == self.sort_col:
                arrow = "▼" if self.sort_desc else "▲"
                self.tree.heading(col_name, text=f"{base_title} {arrow}")
            else:
                self.tree.heading(col_name, text=f"{base_title} ⇅")

    def on_sort_column(self, col_name):
        if self.sort_col == col_name:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = col_name
            self.sort_desc = False

        self._update_column_headers()
        self.refresh_table()

    def refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        filtered = self.manager.filter_tasks(
            status_filter=self.filter_var.get(),
            keyword=self.search_var.get(),
        )
        sorted_tasks = self.manager.sort_tasks(
            filtered, sort_col=self.sort_col, descending=self.sort_desc
        )

        default_reminders = self.config_manager.get("default_reminders", [1440, 60, 30])

        for task in sorted_tasks:
            info = get_task_status_info(task, default_reminders=default_reminders)

            self.tree.insert(
                "",
                tk.END,
                values=(
                    task["id"],
                    task["title"],
                    task["priority"],
                    task["deadline"],
                    info["time_str"],
                    info["text"],
                ),
                tags=(info["tag"],),
            )

        detailed = self.manager.get_detailed_statistics(default_reminders=default_reminders)
        self.lbl_stats.config(
            text=(
                f"Tổng: {detailed['total']}  |  "
                f"Chưa xong: {detailed['pending']}  |  "
                f"⏰ Sắp đến hạn: {detailed['due_soon']}  |  "
                f"🚨 Quá hạn: {detailed['overdue']}  |  "
                f"Đã xong: {detailed['done']}"
            )
        )

    # ================= CÁC TÍNH NĂNG CHẠY NỀN & KHỞI ĐỘNG =================

    def _on_toggle_tray_on_close(self):
        """Lưu lại trạng thái tùy chọn chạy ngầm khi tắt."""
        new_val = self.tray_on_close_var.get()
        self.config_manager.set("minimize_to_tray_on_close", new_val)

    def minimize_to_tray(self):
        """Thu nhỏ ứng dụng xuống khay hệ thống (System Tray)."""
        self.root.withdraw()
        if not self.config_manager.get("has_shown_tray_hint", False):
            self.notification_service.notify_info(
                "Task Reminder đang chạy ngầm",
                "Ứng dụng đã thu nhỏ xuống khay hệ thống và tiếp tục theo dõi deadline. Nhấp đúp vào biểu tượng để mở lại.",
            )
            self.config_manager.set("has_shown_tray_hint", True)

    def restore_window(self):
        """Khôi phục cửa sổ từ khay hệ thống."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.state("normal")

    def restore_window_from_tray(self):
        self.root.after(0, self.restore_window)

    def check_deadlines_from_tray(self):
        self.root.after(0, self.on_manual_check_deadlines)

    def open_settings_from_tray(self):
        self.root.after(0, self.open_settings_dialog)

    def toggle_autostart_from_tray(self):
        self.root.after(0, self.toggle_autostart)

    def exit_application_from_tray(self):
        self.root.after(0, self.exit_application)

    def on_close_window(self):
        """Xử lý khi người dùng nhấn nút đóng [X] ở góc trên cửa sổ."""
        if self.tray_on_close_var.get():
            # Tự động chuyển vào chế độ chạy ngầm
            self.minimize_to_tray()
        else:
            confirm = messagebox.askyesno(
                "Xác nhận thoát",
                "Bạn có chắc muốn tắt hoàn toàn Task Reminder?\n(Tích vào ô 'Chạy ngầm khi tắt' trên thanh tiêu đề nếu muốn ứng dụng tự động chạy ngầm dưới khay hệ thống).",
            )
            if confirm:
                self.exit_application()

    def exit_application(self):
        """Dừng hoàn toàn ứng dụng và gỡ bỏ biểu tượng khay hệ thống."""
        self._is_terminating = True
        if self.timer_job:
            try:
                self.root.after_cancel(self.timer_job)
            except Exception:
                pass
        try:
            self.tray_manager.stop()
        except Exception:
            pass
        self.root.destroy()
        sys.exit(0)

    def toggle_autostart(self):
        """Bật / tắt nhanh tính năng khởi động cùng Windows."""
        cur = AutoStartManager.is_autostart_enabled()
        new_state = not cur
        success = AutoStartManager.set_autostart(new_state)
        if success:
            self.config_manager.set("autostart", new_state)
            status_text = "BẬT" if new_state else "TẮT"
            messagebox.showinfo(
                "Khởi động cùng Windows",
                f"Đã {status_text} tính năng tự động chạy khi mở máy tính!",
            )
        else:
            messagebox.showwarning(
                "Lỗi", "Không thể thay đổi thiết lập khởi động cùng Windows trong Registry."
            )

    def open_settings_dialog(self):
        """Mở cửa sổ cài đặt hệ thống & thời gian nhắc nhở."""
        SettingsDialog(
            parent=self.root,
            config_manager=self.config_manager,
            notification_service=self.notification_service,
            on_save_callback=self._on_settings_saved,
        )

    def _on_settings_saved(self):
        self.tray_on_close_var.set(self.config_manager.get("minimize_to_tray_on_close", True))
        self._update_reminder_display()
        self.refresh_table()

    def show_user_guide(self):
        guide = (
            "📖 HƯỚNG DẪN SỬ DỤNG TASK REMINDER v2.0:\n\n"
            "1. Chế độ chạy ngầm khi tắt ứng dụng:\n"
            "   - Tích chọn ô 'Chạy ngầm khi tắt' trên thanh tiêu đề (hoặc trong Cài đặt).\n"
            "   - Khi bấm nút [X] tắt cửa sổ, ứng dụng sẽ tự động chuyển sang chế độ chạy ngầm dưới khay hệ thống (System Tray).\n"
            "   - Nhấp đúp chuột vào icon ở khay đồng hồ để mở lại ứng dụng bất cứ lúc nào.\n\n"
            "2. Nhắc nhở nhiều lần (Multi-stage Reminders):\n"
            "   - Bấm nút '⚙️ Chọn mốc' để tích chọn các đợt nhắc trước deadline:\n"
            "     (VD: 3 ngày trước, 1 ngày trước, 1 tiếng trước, 15 phút trước...).\n"
            "   - Hệ thống sẽ phát thông báo theo từng mốc thời gian đã chọn.\n\n"
            "3. Tự động chạy khi mở máy:\n"
            "   - Vào '⚙️ Cài đặt' -> Tích chọn 'Tự động chạy khi mở máy tính'."
        )
        messagebox.showinfo("Hướng dẫn sử dụng", guide)

    def show_about(self):
        about = (
            "📋 TASK REMINDER v2.0\n"
            "Ứng dụng Quản lý & Nhắc nhở Công việc Cá nhân Đa Mốc\n\n"
            "Đề tài Bài tập lớn môn: Lập trình Python\n"
            "Các tính năng vượt trội:\n"
            "  ✔ Nhắc nhiều lần (3 ngày, 1 ngày, 1 tiếng, 15 phút,...)\n"
            "  ✔ Chạy ngầm trong khay hệ thống (System Tray)\n"
            "  ✔ Tự động khởi động cùng Windows (Auto-start on boot)\n"
            "  ✔ Thông báo Windows Toast gốc kèm âm thanh cảnh báo\n"
            "  ✔ Bộ chọn ngày & giờ thông minh kết hợp bảng lịch tháng"
        )
        messagebox.showinfo("Giới thiệu", about)


if __name__ == "__main__":
    root_window = tk.Tk()
    app = TodoApp(root_window)
    root_window.mainloop()
