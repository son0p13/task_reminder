import tkinter as tk
from tkinter import ttk, messagebox
from autostart_manager import AutoStartManager
from multi_reminder_dialog import (
    AVAILABLE_REMINDER_STAGES,
    PRESET_COMBOS,
    format_reminders_text,
    minutes_to_label,
)

PRESET_INTERVALS = [
    ("15 giây", 15),
    ("30 giây (Khuyến nghị)", 30),
    ("1 phút", 60),
    ("2 phút", 120),
    ("5 phút", 300),
]


class SettingsDialog:
    """Hộp thoại cấu hình cài đặt hệ thống & mốc nhắc nhở nhiều lần mặc định."""

    def __init__(self, parent, config_manager, notification_service, on_save_callback=None):
        self.parent = parent
        self.config_manager = config_manager
        self.notification_service = notification_service
        self.on_save_callback = on_save_callback

        self.win = tk.Toplevel(parent)
        self.win.title("Cài Đặt Hệ Thống & Nhắc Nhở Deadline")
        self.win.geometry("580x640")
        self.win.minsize(540, 580)
        self.win.configure(bg="#f8fafc")
        self.win.transient(parent)
        self.win.grab_set()

        self._center_window()
        self._create_widgets()
        self._load_current_values()

    def _center_window(self):
        self.win.update_idletasks()
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()
        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()

        w = 580
        h = 640
        x = px + max(0, (pw - w) // 2)
        y = py + max(0, (ph - h) // 2)
        self.win.geometry(f"{w}x{h}+{x}+{y}")

    def _create_widgets(self):
        # Header
        header = tk.Frame(self.win, bg="#1e293b", pady=10, padx=16)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="⚙️ CÀI ĐẶT HỆ THỐNG & NHẮC NHỞ NHIỀU LẦN",
            font=("Segoe UI", 12, "bold"),
            fg="#f8fafc",
            bg="#1e293b",
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Cấu hình các mốc nhắc nhiều lần (3 ngày, 1 ngày, 1 tiếng,...), chạy ngầm và khởi động",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#1e293b",
        ).pack(anchor="w")

        content = tk.Frame(self.win, bg="#f8fafc", padx=16, pady=10)
        content.pack(fill=tk.BOTH, expand=True)

        # 1. Nhóm cấu hình nhắc nhiều lần mặc định
        grp_reminder = tk.LabelFrame(
            content,
            text=" ⏰ Các mốc nhắc nhở mặc định (Multi-stage Reminders) ",
            font=("Segoe UI", 10, "bold"),
            bg="#f8fafc",
            fg="#1e293b",
            padx=12,
            pady=8,
        )
        grp_reminder.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            grp_reminder,
            text="Chọn các mốc hệ thống sẽ tự động nhắc nhở trước deadline:",
            font=("Segoe UI", 8),
            fg="#475569",
            bg="#f8fafc",
        ).pack(anchor="w", pady=(0, 4))

        # Checkbox grid cho các mốc
        chk_box = tk.Frame(grp_reminder, bg="#f8fafc")
        chk_box.pack(fill=tk.X)

        self.stage_vars = {}
        for idx, (label, mins) in enumerate(AVAILABLE_REMINDER_STAGES):
            var = tk.BooleanVar(value=False)
            self.stage_vars[mins] = var
            r = idx // 2
            c = idx % 2
            tk.Checkbutton(
                chk_box,
                text=label,
                variable=var,
                font=("Segoe UI", 9),
                bg="#f8fafc",
                activebackground="#f8fafc",
                command=self._update_reminder_preview,
            ).grid(row=r, column=c, sticky="w", padx=4, pady=2)

        # Nút combo chọn nhanh
        combo_row = tk.Frame(grp_reminder, bg="#f8fafc")
        combo_row.pack(fill=tk.X, pady=(6, 4))

        tk.Label(combo_row, text="Mẫu nhanh:", font=("Segoe UI", 8, "bold"), bg="#f8fafc").pack(side=tk.LEFT)
        for name, preset_list in [
            ("Chuẩn (1 ngày, 1h, 30p)", [1440, 60, 30]),
            ("Dự án (3 ngày, 1 ngày, 2h)", [4320, 1440, 120]),
            ("Gấp (2h, 1h, 30p, 5p)", [120, 60, 30, 5]),
        ]:
            tk.Button(
                combo_row,
                text=name,
                font=("Segoe UI", 8),
                bg="#e2e8f0",
                relief=tk.FLAT,
                cursor="hand2",
                command=lambda p=preset_list: self._apply_stage_preset(p),
            ).pack(side=tk.LEFT, padx=3)

        self.lbl_stage_preview = tk.Label(
            grp_reminder,
            text="",
            font=("Segoe UI", 8, "italic"),
            fg="#2563eb",
            bg="#f8fafc",
            anchor="w",
        )
        self.lbl_stage_preview.pack(fill=tk.X, pady=(2, 2))

        # Chu kỳ quét
        scan_row = tk.Frame(grp_reminder, bg="#f8fafc")
        scan_row.pack(fill=tk.X, pady=(4, 0))

        tk.Label(scan_row, text="Chu kỳ quét deadline:", font=("Segoe UI", 9), bg="#f8fafc").pack(
            side=tk.LEFT
        )
        self.interval_var = tk.StringVar()
        self.combo_interval = ttk.Combobox(
            scan_row,
            textvariable=self.interval_var,
            values=[label for label, _ in PRESET_INTERVALS],
            state="readonly",
            font=("Segoe UI", 9),
            width=22,
        )
        self.combo_interval.pack(side=tk.LEFT, padx=8)

        # 2. Nhóm Chạy dưới nền & Khởi động cùng Windows
        grp_system = tk.LabelFrame(
            content,
            text=" 🚀 Tự khởi động & Chạy dưới nền ",
            font=("Segoe UI", 10, "bold"),
            bg="#f8fafc",
            fg="#1e293b",
            padx=12,
            pady=8,
        )
        grp_system.pack(fill=tk.X, pady=(0, 10))

        self.autostart_var = tk.BooleanVar()
        tk.Checkbutton(
            grp_system,
            text="Tự động chạy khi mở máy tính (Windows Startup)",
            variable=self.autostart_var,
            font=("Segoe UI", 9, "bold"),
            bg="#f8fafc",
            activebackground="#f8fafc",
        ).pack(anchor="w")

        tk.Label(
            grp_system,
            text="   ↳ Tự động chạy ẩn dưới khay hệ thống mỗi khi máy tính bật lên.",
            font=("Segoe UI", 8),
            fg="#64748b",
            bg="#f8fafc",
        ).pack(anchor="w", pady=(0, 4))

        self.min_tray_var = tk.BooleanVar()
        tk.Checkbutton(
            grp_system,
            text="Thu nhỏ xuống khay hệ thống (System Tray) khi bấm nút đóng [X]",
            variable=self.min_tray_var,
            font=("Segoe UI", 9),
            bg="#f8fafc",
            activebackground="#f8fafc",
        ).pack(anchor="w")

        # 3. Nhóm Thông báo & Âm thanh
        grp_notify = tk.LabelFrame(
            content,
            text=" 🔔 Thông báo & Âm thanh ",
            font=("Segoe UI", 10, "bold"),
            bg="#f8fafc",
            fg="#1e293b",
            padx=12,
            pady=8,
        )
        grp_notify.pack(fill=tk.X, pady=(0, 10))

        self.sound_var = tk.BooleanVar()
        tk.Checkbutton(
            grp_notify,
            text="Phát chuông âm thanh khi có thông báo deadline",
            variable=self.sound_var,
            font=("Segoe UI", 9),
            bg="#f8fafc",
            activebackground="#f8fafc",
        ).pack(anchor="w")

        self.overdue_notify_var = tk.BooleanVar()
        tk.Checkbutton(
            grp_notify,
            text="Thông báo cảnh báo khi công việc đã quá hạn",
            variable=self.overdue_notify_var,
            font=("Segoe UI", 9),
            bg="#f8fafc",
            activebackground="#f8fafc",
        ).pack(anchor="w")

        # Bottom Action Bar
        btn_bar = tk.Frame(self.win, bg="#f1f5f9", padx=16, pady=10)
        btn_bar.pack(side=tk.BOTTOM, fill=tk.X)

        tk.Button(
            btn_bar,
            text="🧪 Thử gửi thông báo ngay",
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg="#1e293b",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._on_test_notification,
        ).pack(side=tk.LEFT)

        tk.Button(
            btn_bar,
            text="Đóng",
            font=("Segoe UI", 9),
            bg="#cbd5e1",
            fg="#1e293b",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.win.destroy,
        ).pack(side=tk.RIGHT, padx=(8, 0))

        tk.Button(
            btn_bar,
            text="💾 Lưu cài đặt",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="white",
            padx=14,
            pady=4,
            cursor="hand2",
            command=self._on_save,
        ).pack(side=tk.RIGHT)

    def _load_current_values(self):
        # 1. Multi-stage reminders
        cur_reminders = self.config_manager.get("default_reminders", [1440, 60, 30])
        cur_set = set(int(m) for m in cur_reminders if int(m) > 0)
        for mins, var in self.stage_vars.items():
            var.set(mins in cur_set)
        self._update_reminder_preview()

        # 2. Check interval
        interval_sec = self.config_manager.get("check_interval_seconds", 30)
        matched_interval = None
        for label, val in PRESET_INTERVALS:
            if val == interval_sec:
                matched_interval = label
                break
        if matched_interval:
            self.interval_var.set(matched_interval)
        else:
            self.interval_var.set(PRESET_INTERVALS[1][0])

        # 3. Autostart from Registry
        reg_enabled = AutoStartManager.is_autostart_enabled()
        self.autostart_var.set(reg_enabled)

        # 4. Minimize to tray
        self.min_tray_var.set(self.config_manager.get("minimize_to_tray_on_close", True))

        # 5. Sound & Overdue
        self.sound_var.set(self.config_manager.get("play_sound", True))
        self.overdue_notify_var.set(self.config_manager.get("notify_overdue", True))

    def _apply_stage_preset(self, preset_list):
        pset = set(preset_list)
        for mins, var in self.stage_vars.items():
            var.set(mins in pset)
        self._update_reminder_preview()

    def _update_reminder_preview(self):
        sel = [mins for mins, var in self.stage_vars.items() if var.get()]
        if not sel:
            self.lbl_stage_preview.config(text="⚠️ Chưa chọn mốc nào (sẽ không nhắc trước deadline)")
        else:
            sorted_sel = sorted(sel, reverse=True)
            self.lbl_stage_preview.config(text=f"Đã chọn: {format_reminders_text(sorted_sel)}")

    def _on_test_notification(self):
        sound = self.sound_var.get()
        sample_task = {
            "title": "Báo cáo thử nghiệm thông báo Task Reminder",
            "priority": "Cao",
            "deadline": "Hôm nay 23:59",
        }
        sent = self.notification_service.notify_due_soon(
            sample_task, 60, stage_label="1 tiếng trước", sound_enabled=sound
        )
        if sent:
            messagebox.showinfo("Thông báo", "Đã gửi thông báo Windows Toast thành công!")
        else:
            messagebox.showwarning(
                "Thông báo",
                "Đã phát âm thanh cảnh báo (Thông báo Windows Toast có thể đang bị chế độ Focus Assist của Windows chặn).",
            )

    def _on_save(self):
        sel_stages = sorted([mins for mins, var in self.stage_vars.items() if var.get()], reverse=True)
        if not sel_stages:
            confirm = messagebox.askyesno(
                "Cảnh báo", "Bạn chưa chọn mốc nhắc nhở nào. Ứng dụng sẽ không phát thông báo trước deadline. Vẫn lưu?"
            )
            if not confirm:
                return

        sel_interval_label = self.interval_var.get()
        interval_sec = 30
        for label, val in PRESET_INTERVALS:
            if label == sel_interval_label:
                interval_sec = val
                break

        new_autostart = self.autostart_var.get()
        reg_success = AutoStartManager.set_autostart(new_autostart)
        if not reg_success:
            messagebox.showwarning(
                "Cảnh báo Registry",
                "Không thể thay đổi thiết lập khởi động cùng Windows. Hãy kiểm tra quyền hệ thống.",
            )

        self.config_manager.update(
            {
                "default_reminders": sel_stages,
                "reminder_advance_minutes": sel_stages[0] if sel_stages else 30,
                "check_interval_seconds": interval_sec,
                "autostart": new_autostart,
                "minimize_to_tray_on_close": self.min_tray_var.get(),
                "play_sound": self.sound_var.get(),
                "notify_overdue": self.overdue_notify_var.get(),
            }
        )

        if callable(self.on_save_callback):
            self.on_save_callback()

        messagebox.showinfo("Thành công", "Đã lưu toàn bộ cài đặt hệ thống và các mốc nhắc nhở!")
        self.win.destroy()
