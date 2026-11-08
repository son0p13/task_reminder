import json
import os
from datetime import datetime


class TaskManager:
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
                "deadline": today,
                "completed": False,
            },
            {
                "id": 2,
                "title": "Ôn tập kiến thức danh sách, từ điển và đọc ghi file",
                "priority": "Trung bình",
                "deadline": today,
                "completed": True,
            },
            {
                "id": 3,
                "title": "Chuẩn bị slide thuyết trình cuối kỳ",
                "priority": "Cao",
                "deadline": today,
                "completed": False,
            },
        ]

    def _get_next_id(self):
        if not self.tasks:
            return 1
        return max(task["id"] for task in self.tasks) + 1

    def add_task(self, title, priority, deadline):
        new_task = {
            "id": self._get_next_id(),
            "title": title.strip(),
            "priority": priority,
            "deadline": deadline.strip(),
            "completed": False,
        }
        self.tasks.append(new_task)
        self.save_tasks()
        return new_task

    def update_task(self, task_id, new_title, new_priority, new_deadline):
        for task in self.tasks:
            if task["id"] == task_id:
                task["title"] = new_title.strip()
                task["priority"] = new_priority
                task["deadline"] = new_deadline.strip()
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

        def parse_deadline(task):
            try:
                return datetime.strptime(task["deadline"], "%d/%m/%Y")
            except (ValueError, KeyError):
                return datetime.max

        if sort_col == "id":
            key_func = lambda t: t["id"]
        elif sort_col == "title":
            key_func = lambda t: t["title"].lower()
        elif sort_col == "priority":
            key_func = lambda t: priority_rank.get(t["priority"], 0)
        elif sort_col == "deadline":
            key_func = parse_deadline
        elif sort_col == "status":
            key_func = lambda t: t["completed"]
        else:
            key_func = lambda t: t["id"]

        return sorted(task_list, key=key_func, reverse=descending)

    def filter_tasks(self, status_filter="Tất cả", keyword=""):
        keyword = keyword.strip().lower()
        result = []

        for task in self.tasks:
            if status_filter == "Chưa xong" and task["completed"]:
                continue
            if status_filter == "Đã xong" and not task["completed"]:
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
