import csv
import json
import os
from datetime import datetime


def parse_deadline_datetime(deadline_str):
    """Phân tích chuỗi deadline thành datetime (hỗ trợ cả ngày và giờ)."""
    deadline_str = (deadline_str or "").strip()
    if not deadline_str:
        return None

    formats = [
        ("%d/%m/%Y %H:%M:%S", False),
        ("%d/%m/%Y %H:%M", False),
        ("%d/%m/%Y", True),
        ("%Y-%m-%d %H:%M", False),
        ("%Y-%m-%d", True),
    ]

    for fmt, is_date_only in formats:
        try:
            dt = datetime.strptime(deadline_str, fmt)
            if is_date_only:
                dt = dt.replace(hour=23, minute=59, second=59)
            return dt
        except ValueError:
            continue

    return None


class TaskManager:
    """Lớp quản lý nghiệp vụ và lưu trữ dữ liệu công việc (Task)."""

    def __init__(self, filename="tasks.json"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.filepath = os.path.join(base_dir, filename)
        self.tasks = []
        self.load_tasks()

    def load_tasks(self):
        if not os.path.exists(self.filepath):
            self.tasks = self._create_sample_tasks()
            self.save_tasks()
            return

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                self.tasks = json.load(f)
        except (json.JSONDecodeError, OSError):
            self.tasks = []

    def save_tasks(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=4)

    def _create_sample_tasks(self):
        today = datetime.now().strftime("%d/%m/%Y")
        return [
            {
                "id": 1,
                "title": "Hoàn thành bài tập lớn môn Lập trình Python",
                "priority": "Cao",
                "deadline": f"{today} 23:59",
                "completed": False,
                "reminder_minutes": 30,
                "reminders": [1440, 60, 30, 15],  # 1 ngày, 1 tiếng, 30p, 15p
            },
            {
                "id": 2,
                "title": "Ôn tập kiến thức danh sách, từ điển và đọc ghi file",
                "priority": "Trung bình",
                "deadline": f"{today} 20:00",
                "completed": True,
                "reminder_minutes": None,
                "reminders": None,  # Dùng cài đặt chung
            },
            {
                "id": 3,
                "title": "Chuẩn bị slide thuyết trình cuối kỳ",
                "priority": "Cao",
                "deadline": f"{today} 22:00",
                "completed": False,
                "reminder_minutes": 60,
                "reminders": [4320, 1440, 120, 30],  # 3 ngày, 1 ngày, 2 tiếng, 30p
            },
        ]

    def _get_next_id(self):
        if not self.tasks:
            return 1
        return max(task["id"] for task in self.tasks) + 1

    def find_task_by_id(self, task_id):
        for task in self.tasks:
            if task["id"] == task_id:
                return task
        return None

    def add_task(self, title, priority, deadline, reminder_minutes=None, reminders=None):
        if reminders is not None:
            clean_reminders = sorted([int(m) for m in reminders if int(m) > 0], reverse=True)
            single_min = clean_reminders[0] if clean_reminders else 0
        elif reminder_minutes is not None:
            clean_reminders = [reminder_minutes] if reminder_minutes > 0 else []
            single_min = reminder_minutes
        else:
            clean_reminders = None
            single_min = None

        new_task = {
            "id": self._get_next_id(),
            "title": title.strip(),
            "priority": priority,
            "deadline": deadline.strip(),
            "completed": False,
            "reminder_minutes": single_min,
            "reminders": clean_reminders,
        }
        self.tasks.append(new_task)
        self.save_tasks()
        return new_task

    def update_task(
        self,
        task_id,
        new_title,
        new_priority,
        new_deadline,
        new_reminder_minutes=None,
        new_reminders=None,
    ):
        for task in self.tasks:
            if task["id"] == task_id:
                task["title"] = new_title.strip()
                task["priority"] = new_priority
                task["deadline"] = new_deadline.strip()

                if new_reminders is not None:
                    task["reminders"] = sorted([int(m) for m in new_reminders if int(m) > 0], reverse=True)
                    task["reminder_minutes"] = task["reminders"][0] if task["reminders"] else 0
                elif new_reminder_minutes is not None:
                    task["reminder_minutes"] = new_reminder_minutes
                    task["reminders"] = [new_reminder_minutes] if new_reminder_minutes > 0 else []
                else:
                    task["reminders"] = None
                    task["reminder_minutes"] = None

                self.save_tasks()
                return True
        return False

    def toggle_task(self, task_id):
        for task in self.tasks:
            if task["id"] == task_id:
                task["completed"] = not task["completed"]
                self.save_tasks()
                return True
        return False

    def delete_task(self, task_id):
        for i, task in enumerate(self.tasks):
            if task["id"] == task_id:
                del self.tasks[i]
                self.save_tasks()
                return True
        return False

    def clear_completed(self):
        before_count = len(self.tasks)
        self.tasks = [t for t in self.tasks if not t["completed"]]
        removed = before_count - len(self.tasks)
        if removed > 0:
            self.save_tasks()
        return removed

    def clear_all(self):
        removed = len(self.tasks)
        if removed > 0:
            self.tasks = []
            self.save_tasks()
        return removed

    def sort_tasks(self, task_list, sort_col="id", descending=False):
        priority_rank = {"Thấp": 1, "Trung bình": 2, "Cao": 3}

        def parse_dl(task):
            dt = parse_deadline_datetime(task.get("deadline", ""))
            return dt if dt is not None else datetime.max

        def get_time_left(task):
            if task.get("completed"):
                return float("inf")
            dt = parse_deadline_datetime(task.get("deadline", ""))
            if not dt:
                return float("inf") - 1
            return (dt - datetime.now()).total_seconds()

        def get_status_rank(task):
            if task.get("completed"):
                return 4
            dt = parse_deadline_datetime(task.get("deadline", ""))
            if not dt:
                return 3
            diff = (dt - datetime.now()).total_seconds()
            if diff < 0:
                return 1
            elif diff <= 86400:  # Trong vòng 1 ngày
                return 2
            return 3

        if sort_col == "id":
            key_func = lambda t: t["id"]
        elif sort_col == "title":
            key_func = lambda t: t["title"].lower()
        elif sort_col == "priority":
            key_func = lambda t: priority_rank.get(t["priority"], 0)
        elif sort_col == "deadline":
            key_func = parse_dl
        elif sort_col == "time_left":
            key_func = get_time_left
        elif sort_col == "status":
            key_func = get_status_rank
        else:
            key_func = lambda t: t["id"]

        return sorted(task_list, key=key_func, reverse=descending)

    def filter_tasks(self, status_filter="Tất cả", keyword=""):
        keyword = keyword.strip().lower()
        result = []
        now = datetime.now()

        for task in self.tasks:
            if status_filter == "Chưa xong" and task["completed"]:
                continue
            if status_filter == "Đã xong" and not task["completed"]:
                continue
            if status_filter == "Quá hạn":
                if task["completed"]:
                    continue
                dt = parse_deadline_datetime(task.get("deadline", ""))
                if not dt or dt >= now:
                    continue
            if status_filter == "Sắp đến hạn":
                if task["completed"]:
                    continue
                dt = parse_deadline_datetime(task.get("deadline", ""))
                if not dt:
                    continue
                diff = (dt - now).total_seconds()
                if diff < 0 or diff > 259200:  # Trong vòng 3 ngày
                    continue

            if keyword and keyword not in task["title"].lower():
                continue
            result.append(task)

        return result

    def get_statistics(self):
        total = len(self.tasks)
        done = sum(1 for t in self.tasks if t["completed"])
        pending = total - done
        return total, done, pending

    def get_detailed_statistics(self, default_reminders=None):
        if default_reminders is None:
            default_reminders = [1440, 60, 30]

        total = len(self.tasks)
        done = 0
        pending = 0
        overdue = 0
        due_soon = 0
        now = datetime.now()

        for task in self.tasks:
            if task.get("completed"):
                done += 1
            else:
                pending += 1
                dt = parse_deadline_datetime(task.get("deadline", ""))
                if dt:
                    diff = (dt - now).total_seconds()
                    if "reminders" in task and task["reminders"] is not None:
                        rems = [int(m) for m in task["reminders"] if int(m) > 0]
                    elif task.get("reminder_minutes") is not None:
                        val = int(task["reminder_minutes"])
                        rems = [val] if val > 0 else []
                    else:
                        rems = list(default_reminders)

                    max_adv = max(rems) if rems else 0
                    if diff < 0:
                        overdue += 1
                    elif diff <= (max_adv * 60) and max_adv > 0:
                        due_soon += 1

        return {
            "total": total,
            "done": done,
            "pending": pending,
            "overdue": overdue,
            "due_soon": due_soon,
        }

    def export_to_csv(self, filepath):
        """Xuất danh sách công việc ra định dạng CSV (hỗ trợ hiển thị tiếng Việt chuẩn trong Excel)."""
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Tên công việc", "Mức ưu tiên", "Hạn chót", "Trạng thái", "Các mốc nhắc nhở"])
            for task in self.tasks:
                status = "Đã xong" if task["completed"] else "Chưa xong"
                if "reminders" in task and task["reminders"] is not None:
                    rems_str = ", ".join(f"{m}p" for m in task["reminders"])
                elif task.get("reminder_minutes") is not None:
                    rems_str = f"{task['reminder_minutes']}p"
                else:
                    rems_str = "Cài đặt chung"

                writer.writerow([
                    task["id"],
                    task["title"],
                    task["priority"],
                    task["deadline"],
                    status,
                    rems_str,
                ])
        return True
