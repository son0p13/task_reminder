import tkinter as tk
from tkinter import ttk, messagebox

AVAILABLE_REMINDER_STAGES = [
    ("3 ngày trước", 4320),
    ("2 ngày trước", 2880),
    ("1 ngày trước (24h)", 1440),
    ("12 tiếng trước", 720),
    ("6 tiếng trước", 360),
    ("2 tiếng trước", 120),
    ("1 tiếng trước (60p)", 60),
    ("30 phút trước", 30),
    ("15 phút trước", 15),
    ("5 phút trước", 5),
]

PRESET_COMBOS = [
    ("⭐ Chuẩn (1 ngày, 1 tiếng, 15p)", [1440, 60, 15]),
    ("📅 Dự án (3 ngày, 1 ngày, 2 tiếng)", [4320, 1440, 120]),
    ("⚡ Gấp rút (2 tiếng, 1 tiếng, 30p, 5p)", [120, 60, 30, 5]),
    ("🔔 Theo cài đặt chung", None),
    ("❌ Không nhắc", []),
]


def minutes_to_label(minutes):
    """Chuyển đổi số phút thành chuỗi mô tả thân thiện."""
    if minutes >= 1440:
        d = minutes // 1440
        rem = minutes % 1440
        return f"{d} ngày" if rem == 0 else f"{d} ngày {rem // 60}h"
    elif minutes >= 60:
        h = minutes // 60
        rem = minutes % 60
        return f"{h} tiếng" if rem == 0 else f"{h}h {rem}p"
    else:
        return f"{minutes} phút"


def format_reminders_text(reminders, default_summary=""):
    """Định dạng danh sách các mốc nhắc thành chuỗi hiển thị gọn trên giao diện."""
    if reminders is None:
        if default_summary:
            return f"Cài đặt chung ({default_summary})"
        return "Theo cài đặt chung"

    if not reminders or reminders == [0]:
        return "Không nhắc"

    sorted_rem = sorted([int(x) for x in reminders if int(x) > 0], reverse=True)
    if not sorted_rem:
        return "Không nhắc"

    labels = [minutes_to_label(m) for m in sorted_rem]
    count = len(labels)
    joined = ", ".join(labels)
    return f"{joined} trước ({count} lần)"


class MultiReminderDialog:
    """Hộp thoại chọn nhiều mốc nhắc nhở (Multi-stage reminder picker)."""

    def __init__(self, parent, current_reminders=None, on_apply=None, default_reminders=None):
        self.parent = parent
        self.on_apply = on_apply
        self.default_reminders = default_reminders or [1440, 60, 30]

        # Khởi tạo tập hợp các phút đã chọn
        self.is_use_default = current_reminders is None
        if self.is_use_default:
            self.selected_minutes = set(self.default_reminders)
        else:
            self.selected_minutes = set(int(m) for m in current_reminders if int(m) > 0)

        self.win = tk.Toplevel(parent)
        self.win.title("Cài Đặt Nhắc Nhở Nhiều Lần")
        self.win.resizable(False, False)
        self.win.configure(bg="#f8fafc", padx=14, pady=12)
        self.win.transient(parent)
        self.win.grab_set()

        self._center_window()
        self._create_widgets()
        self._update_summary()

    def _center_window(self):
        self.win.update_idletasks()
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()
        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()

        w = 460
        h = 560
        x = px + max(0, (pw - w) // 2)
        y = py + max(0, (ph - h) // 2)
        self.win.geometry(f"{w}x{h}+{x}+{y}")

    def _create_widgets(self):
        # Header
        header = tk.Frame(self.win, bg="#1e293b", padx=12, pady=8)
        header.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            header,
            text="🔔 CÁC MỐC NHẮC NHỞ TRƯỚC DEADLINE",
            font=("Segoe UI", 11, "bold"),
            fg="#f8fafc",
            bg="#1e293b",
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Chọn nhiều mốc để nhận thông báo từng đợt (3 ngày, 1 ngày, 1 tiếng,...)",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#1e293b",
        ).pack(anchor="w")

        # Khung các bộ chọn nhanh (Presets)
        preset_frame = tk.LabelFrame(
            self.win,
            text=" Mẫu cấu hình nhanh ",
            font=("Segoe UI", 9, "bold"),
            bg="#f8fafc",
            padx=8,
            pady=6,
        )
        preset_frame.pack(fill=tk.X, pady=(0, 8))

        for name, preset_list in PRESET_COMBOS:
            btn = tk.Button(
                preset_frame,
                text=name,
                font=("Segoe UI", 8),
                bg="#f1f5f9",
                fg="#1e293b",
                relief=tk.FLAT,
                cursor="hand2",
                anchor="w",
                pady=2,
                command=lambda p=preset_list: self._apply_preset(p),
            )
            btn.pack(fill=tk.X, pady=1)

        # Khung danh sách các mốc bằng Checkbox (2 cột)
        chk_frame = tk.LabelFrame(
            self.win,
            text=" Danh sách các mốc nhắc nhở ",
            font=("Segoe UI", 9, "bold"),
            bg="#f8fafc",
            padx=10,
            pady=8,
        )
        chk_frame.pack(fill=tk.X, pady=(0, 8))

        self.check_vars = {}
        for idx, (label, mins) in enumerate(AVAILABLE_REMINDER_STAGES):
            var = tk.BooleanVar(value=(mins in self.selected_minutes and not self.is_use_default))
            self.check_vars[mins] = var

            r = idx // 2
            c = idx % 2
            chk = tk.Checkbutton(
                chk_frame,
                text=label,
                variable=var,
                font=("Segoe UI", 9),
                bg="#f8fafc",
                activebackground="#f8fafc",
                command=self._on_check_changed,
            )
            chk.grid(row=r, column=c, sticky="w", padx=6, pady=3)

        # Mốc tùy chỉnh thêm
        custom_row = tk.Frame(chk_frame, bg="#f8fafc")
        custom_row.grid(row=(len(AVAILABLE_REMINDER_STAGES) + 1) // 2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        tk.Label(custom_row, text="Thêm mốc tùy chỉnh:", font=("Segoe UI", 8), bg="#f8fafc").pack(side=tk.LEFT)
        self.custom_mins_entry = tk.Entry(custom_row, font=("Segoe UI", 8), width=7)
        self.custom_mins_entry.pack(side=tk.LEFT, padx=4)
        tk.Label(custom_row, text="phút", font=("Segoe UI", 8), bg="#f8fafc").pack(side=tk.LEFT)

        tk.Button(
            custom_row,
            text="+ Thêm",
            font=("Segoe UI", 8, "bold"),
            bg="#2563eb",
            fg="white",
            relief=tk.FLAT,
            padx=6,
            cursor="hand2",
            command=self._add_custom_stage,
        ).pack(side=tk.LEFT, padx=(6, 0))

        # Tùy chọn sử dụng cài đặt chung
        self.use_default_var = tk.BooleanVar(value=self.is_use_default)
        chk_default = tk.Checkbutton(
            self.win,
            text="Sử dụng cấu hình nhắc nhở chung của hệ thống",
            variable=self.use_default_var,
            font=("Segoe UI", 9, "bold"),
            bg="#f8fafc",
            activebackground="#f8fafc",
            command=self._on_toggle_use_default,
        )
        chk_default.pack(anchor="w", pady=(0, 6))

        # Tóm tắt
        self.lbl_summary = tk.Label(
            self.win,
            text="",
            font=("Segoe UI", 9, "italic"),
            fg="#2563eb",
            bg="#f8fafc",
            wraplength=420,
            justify="left",
        )
        self.lbl_summary.pack(fill=tk.X, pady=(0, 8))

        # Action Buttons
        btn_box = tk.Frame(self.win, bg="#f8fafc")
        btn_box.pack(fill=tk.X)

        tk.Button(
            btn_box,
            text="Hủy",
            font=("Segoe UI", 9),
            bg="#cbd5e1",
            fg="#1e293b",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.win.destroy,
        ).pack(side=tk.RIGHT, padx=(6, 0))

        tk.Button(
            btn_box,
            text="✔ Áp dụng",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="white",
            padx=14,
            pady=3,
            cursor="hand2",
            command=self._on_confirm,
        ).pack(side=tk.RIGHT)

    def _apply_preset(self, preset_list):
        if preset_list is None:
            self.is_use_default = True
            self.use_default_var.set(True)
            self.selected_minutes = set(self.default_reminders)
        else:
            self.is_use_default = False
            self.use_default_var.set(False)
            self.selected_minutes = set(preset_list)

        self._sync_check_vars()
        self._update_summary()

    def _sync_check_vars(self):
        for mins, var in self.check_vars.items():
            var.set(mins in self.selected_minutes and not self.is_use_default)

    def _on_check_changed(self):
        self.is_use_default = False
        self.use_default_var.set(False)
        self.selected_minutes = {mins for mins, var in self.check_vars.items() if var.get()}
        self._update_summary()

    def _on_toggle_use_default(self):
        self.is_use_default = self.use_default_var.get()
        if self.is_use_default:
            self.selected_minutes = set(self.default_reminders)
        self._sync_check_vars()
        self._update_summary()

    def _add_custom_stage(self):
        val_str = self.custom_mins_entry.get().strip()
        try:
            val = int(val_str)
            if val <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Lỗi", "Vui lòng nhập số phút nguyên dương hợp lệ!")
            return

        self.is_use_default = False
        self.use_default_var.set(False)
        self.selected_minutes.add(val)
        self.custom_mins_entry.delete(0, tk.END)
        self._sync_check_vars()
        self._update_summary()

    def _update_summary(self):
        if self.is_use_default:
            default_text = format_reminders_text(self.default_reminders)
            self.lbl_summary.config(text=f"📋 Sẽ nhắc theo cài đặt chung: {default_text}")
        elif not self.selected_minutes:
            self.lbl_summary.config(text="🚫 Không đặt mốc nhắc nhở nào cho công việc này.")
        else:
            sorted_list = sorted(list(self.selected_minutes), reverse=True)
            text = format_reminders_text(sorted_list)
            self.lbl_summary.config(text=f"⏰ Sẽ nhắc nhở: {text}")

    def _on_confirm(self):
        if callable(self.on_apply):
            if self.is_use_default:
                self.on_apply(None)
            else:
                sorted_list = sorted(list(self.selected_minutes), reverse=True)
                self.on_apply(sorted_list)
        self.win.destroy()

