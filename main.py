import calendar
import ctypes
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

from task_manager import TaskManager

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


class TodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Reminder - Quản Lý Công Việc")

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = max(860, int(screen_w * 0.62))
        win_h = max(620, int(screen_h * 0.72))
        pos_x = (screen_w - win_w) // 2
        pos_y = (screen_h - win_h) // 2
        self.root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        self.root.minsize(780, 520)
        self.root.configure(bg="#f4f6f9")

        self.manager = TaskManager()
        self.cal_win = None
        self.sort_col = "id"
        self.sort_desc = False
        self.col_titles = {
            "id": "ID",
            "title": "Tên công việc",
            "priority": "Mức ưu tiên",
            "deadline": "Deadline",
            "status": "Trạng thái",
        }

        self._setup_styles()
        self._create_widgets()
        self.refresh_table()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Treeview", font=("Segoe UI", 10), rowheight=30)
        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 10, "bold"),
            background="#e2e8f0",
            foreground="#1e293b",
        )
        style.map("Treeview.Heading", background=[("active", "#cbd5e1")])
        style.map("Treeview", background=[("selected", "#bfdbfe")], foreground=[("selected", "#0f172a")])

    def _create_widgets(self):
        header = tk.Label(
            self.root,
            text="📋 QUẢN LÝ CÔNG VIỆC (TASK REMINDER)",
            font=("Segoe UI", 15, "bold"),
            bg="#2563eb",
            fg="white",
            pady=10,
        )
        header.pack(fill=tk.X)

        input_frame = tk.LabelFrame(
            self.root,
            text=" Thông tin công việc ",
            font=("Segoe UI", 10, "bold"),
            bg="#f4f6f9",
            fg="#1e293b",
            padx=12,
            pady=10,
        )
        input_frame.pack(fill=tk.X, padx=15, pady=(12, 6))

        tk.Label(input_frame, text="Tên công việc:", font=("Segoe UI", 10), bg="#f4f6f9").grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.title_var = tk.StringVar()
        self.entry_title = tk.Entry(
            input_frame, textvariable=self.title_var, font=("Segoe UI", 10), width=48
        )
        self.entry_title.grid(row=0, column=1, columnspan=3, sticky="we", padx=8, pady=4)
        self.entry_title.bind("<Return>", lambda event: self.on_add_task())

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
            width=14,
        )
        self.combo_priority.grid(row=1, column=1, sticky="w", padx=8, pady=4)

        tk.Label(input_frame, text="Deadline (dd/mm/yyyy):", font=("Segoe UI", 10), bg="#f4f6f9").grid(
            row=1, column=2, sticky="e", pady=4
        )
        deadline_box = tk.Frame(input_frame, bg="#f4f6f9")
        deadline_box.grid(row=1, column=3, sticky="w", padx=8, pady=4)

        self.deadline_var = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        self.entry_deadline = tk.Entry(
            deadline_box, textvariable=self.deadline_var, font=("Segoe UI", 10), width=13
        )
        self.entry_deadline.pack(side=tk.LEFT)

        tk.Button(
            deadline_box,
            text="Chọn thời gian",
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg="#1e293b",
            padx=6,
            cursor="hand2",
            command=self.open_date_picker,
        ).pack(side=tk.LEFT, padx=(6, 0))

        input_frame.columnconfigure(1, weight=1)

        btn_input_box = tk.Frame(input_frame, bg="#f4f6f9")
        btn_input_box.grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 2))

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
        ).pack(side=tk.LEFT)

        filter_frame = tk.Frame(self.root, bg="#f4f6f9")
        filter_frame.pack(fill=tk.X, padx=15, pady=4)

        tk.Label(filter_frame, text="🔍 Tìm kiếm:", font=("Segoe UI", 10), bg="#f4f6f9").pack(
            side=tk.LEFT
        )
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_table())
        tk.Entry(filter_frame, textvariable=self.search_var, font=("Segoe UI", 10), width=26).pack(
            side=tk.LEFT, padx=(6, 18)
        )

        tk.Label(filter_frame, text="Lọc trạng thái:", font=("Segoe UI", 10), bg="#f4f6f9").pack(
            side=tk.LEFT
        )
        self.filter_var = tk.StringVar(value="Tất cả")
        combo_filter = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_var,
            values=["Tất cả", "Chưa xong", "Đã xong"],
            state="readonly",
            font=("Segoe UI", 10),
            width=13,
        )
        combo_filter.pack(side=tk.LEFT, padx=6)
        combo_filter.bind("<<ComboboxSelected>>", lambda event: self.refresh_table())

        bottom_frame = tk.Frame(self.root, bg="#f4f6f9", pady=10)
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
            text="Xóa các việc đã xong",
            font=("Segoe UI", 9, "bold"),
            bg="#f59e0b",
            fg="white",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.on_clear_completed,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            bottom_frame,
            text=" Xóa tất cả",
            font=("Segoe UI", 9, "bold"),
            bg="#7f1d1d",
            fg="white",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.on_clear_all,
        ).pack(side=tk.LEFT)

        self.lbl_stats = tk.Label(
            bottom_frame,
            text="",
            font=("Segoe UI", 10, "bold"),
            bg="#f4f6f9",
            fg="#1e293b",
        )
        self.lbl_stats.pack(side=tk.RIGHT)

        table_frame = tk.Frame(self.root, bg="#f4f6f9")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=4)

        columns = ("id", "title", "priority", "deadline", "status")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse", height=7
        )

        for col_name in columns:
            self.tree.heading(
                col_name,
                text=self.col_titles[col_name],
                command=lambda c=col_name: self.on_sort_column(c),
            )
        self._update_column_headers()

        self.tree.column("id", width=65, anchor="center")
        self.tree.column("title", width=350, anchor="w")
        self.tree.column("priority", width=115, anchor="center")
        self.tree.column("deadline", width=120, anchor="center")
        self.tree.column("status", width=130, anchor="center")

        self.tree.tag_configure("done", foreground="#64748b", background="#f8fafc")
        self.tree.tag_configure("high", foreground="#dc2626")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.context_menu = tk.Menu(self.root, tearoff=0, font=("Segoe UI", 9))
        self.context_menu.add_command(
            label="✔ Đánh dấu Xong / Chưa xong", command=self.on_toggle_task
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="🗑 Xóa công việc này", foreground="#dc2626", command=self.on_delete_task
        )

        self.tree.bind("<<TreeviewSelect>>", self.on_select_row)
        self.tree.bind("<Double-1>", lambda event: self.on_toggle_task())
        self.tree.bind("<Delete>", lambda event: self.on_delete_task())
        self.tree.bind("<Button-3>", self.on_right_click_row)

    def open_date_picker(self):
        if self.cal_win is not None and self.cal_win.winfo_exists():
            self.cal_win.lift()
            self.cal_win.focus_force()
            return

        today = datetime.now()
        try:
            init_dt = datetime.strptime(self.deadline_var.get().strip(), "%d/%m/%Y")
        except ValueError:
            init_dt = today

        state = {"year": init_dt.year, "month": init_dt.month}

        win = tk.Toplevel(self.root)
        win.title("Chọn Deadline")
        win.resizable(False, False)
        win.configure(bg="#ffffff", padx=10, pady=10)
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

        def pick_date(d, m, y):
            self.deadline_var.set(f"{d:02d}/{m:02d}/{y:04d}")
            win.destroy()

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
                        day == init_dt.day
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
                        command=lambda d=day: pick_date(d, state["month"], state["year"]),
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
            top_bar, text="◀", font=("Segoe UI", 9, "bold"), bg="#f1f5f9", relief=tk.FLAT,
            width=3, cursor="hand2", command=lambda: shift_month(-1),
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
            top_bar, text="▶", font=("Segoe UI", 9, "bold"), bg="#f1f5f9", relief=tk.FLAT,
            width=3, cursor="hand2", command=lambda: shift_month(1),
        ).pack(side=tk.LEFT)

        tk.Button(
            win,
            text=f"Hôm nay ({today.strftime('%d/%m/%Y')})",
            font=("Segoe UI", 9, "bold"),
            bg="#eff6ff",
            fg="#2563eb",
            relief=tk.FLAT,
            pady=4,
            cursor="hand2",
            command=lambda: pick_date(today.day, today.month, today.year),
        ).pack(fill=tk.X, pady=(8, 0))

        render_days()

    def _validate_inputs(self):
        title = self.title_var.get().strip()
        deadline = self.deadline_var.get().strip()

        if not title:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập tên công việc!")
            self.entry_title.focus_set()
            return False

        if deadline:
            try:
                datetime.strptime(deadline, "%d/%m/%Y")
            except ValueError:
                messagebox.showwarning(
                    "Sai định dạng ngày",
                    "Hạn chót cần nhập đúng định dạng ngày/tháng/năm (VD: 25/12/2026) hoặc để trống!",
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
        )
        self.refresh_table()
        messagebox.showinfo("Thành công", "Đã cập nhật thông tin công việc!")

    def on_toggle_task(self):
        task_id = self._get_selected_task_id()
        if task_id is None:
            messagebox.showinfo("Chưa chọn việc", "Hãy chọn một công việc để đánh dấu!")
            return

        self.manager.toggle_task(task_id)
        self.refresh_table()

    def on_delete_task(self):
        task_id = self._get_selected_task_id()
        if task_id is None:
            messagebox.showinfo("Chưa chọn việc", "Hãy chọn một công việc cần xóa!")
            return

        confirm = messagebox.askyesno("Xác nhận xóa", "Bạn có chắc muốn xóa công việc này không?")
        if confirm:
            self.manager.delete_task(task_id)
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
            self.clear_inputs()
            self.refresh_table()

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
        self.title_var.set(values[1])
        self.priority_var.set(values[2])
        self.deadline_var.set(values[3])

    def clear_inputs(self):
        self.title_var.set("")
        self.priority_var.set("Trung bình")
        self.deadline_var.set(datetime.now().strftime("%d/%m/%Y"))
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

        for task in sorted_tasks:
            status_text = "✅ Đã xong" if task["completed"] else "⏳ Chưa xong"
            row_tag = ""
            if task["completed"]:
                row_tag = "done"
            elif task["priority"] == "Cao":
                row_tag = "high"

            self.tree.insert(
                "",
                tk.END,
                values=(
                    task["id"],
                    task["title"],
                    task["priority"],
                    task["deadline"],
                    status_text,
                ),
                tags=(row_tag,) if row_tag else (),
            )

        total, done, pending = self.manager.get_statistics()
        self.lbl_stats.config(
            text=f"Tổng: {total}  |  Đã xong: {done}  |  Chưa xong: {pending}"
        )


if __name__ == "__main__":
    root_window = tk.Tk()
    app = TodoApp(root_window)
    root_window.mainloop()
