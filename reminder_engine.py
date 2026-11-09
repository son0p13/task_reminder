from datetime import datetime, timedelta
from multi_reminder_dialog import minutes_to_label, format_reminders_text


def parse_deadline_datetime(deadline_str):
    """Phân tích chuỗi deadline thành đối tượng datetime."""
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


def format_time_remaining(deadline_dt, completed=False):
    """Chuyển đổi thời gian còn lại thành chuỗi thân thiện với người dùng."""
    if completed:
        return "Đã xong"
    if not deadline_dt:
        return "Không có hạn"

    now = datetime.now()
    delta = deadline_dt - now
    total_seconds = int(delta.total_seconds())

    if total_seconds < 0:
        overdue_sec = abs(total_seconds)
        if overdue_sec < 60:
            return "Vừa quá hạn"
        elif overdue_sec < 3600:
            return f"Quá hạn {overdue_sec // 60}p"
        elif overdue_sec < 86400:
            h = overdue_sec // 3600
            m = (overdue_sec % 3600) // 60
            return f"Quá hạn {h}h {m}p" if m > 0 else f"Quá hạn {h} giờ"
        else:
            d = overdue_sec // 86400
            return f"Quá hạn {d} ngày"
    else:
        if total_seconds < 60:
            return "Dưới 1 phút"
        elif total_seconds < 3600:
            return f"Còn {total_seconds // 60} phút"
        elif total_seconds < 86400:
            h = total_seconds // 3600
            m = (total_seconds % 3600) // 60
            return f"Còn {h}h {m}p" if m > 0 else f"Còn {h} giờ"
        else:
            d = total_seconds // 86400
            rem_h = (total_seconds % 86400) // 3600
            return f"Còn {d} ngày {rem_h}h" if rem_h > 0 else f"Còn {d} ngày"


def get_task_reminders(task, default_reminders=None):
    """Lấy danh sách các mốc nhắc nhở (phút) của công việc."""
    if default_reminders is None:
        default_reminders = [1440, 60, 30]

    # Kiểm tra trường reminders (danh sách)
    if "reminders" in task and task["reminders"] is not None:
        return sorted([int(m) for m in task["reminders"] if int(m) > 0], reverse=True)

    # Kiểm tra trường reminder_minutes cũ (số nguyên)
    if task.get("reminder_minutes") is not None:
        val = int(task["reminder_minutes"])
        return [val] if val > 0 else []

    # Sử dụng cài đặt mặc định
    return sorted(list(default_reminders), reverse=True)


def get_task_status_info(task, default_reminders=None):
    """Xác định trạng thái chi tiết của công việc: đã xong, quá hạn, sắp đến hạn, hoặc đang chờ."""
    if task.get("completed"):
        return {
            "code": "COMPLETED",
            "text": "✅ Đã xong",
            "tag": "done",
            "time_str": "Đã hoàn thành",
            "seconds": 0,
        }

    deadline_dt = parse_deadline_datetime(task.get("deadline", ""))
    if not deadline_dt:
        return {
            "code": "PENDING",
            "text": "⏳ Chưa xong",
            "tag": "pending",
            "time_str": "Không có hạn",
            "seconds": float("inf"),
        }

    now = datetime.now()
    diff = (deadline_dt - now).total_seconds()
    time_str = format_time_remaining(deadline_dt, completed=False)

    reminders = get_task_reminders(task, default_reminders)
    max_advance = max(reminders) if reminders else 0

    if diff < 0:
        return {
            "code": "OVERDUE",
            "text": "🚨 Quá hạn",
            "tag": "overdue",
            "time_str": time_str,
            "seconds": diff,
        }
    elif diff <= (max_advance * 60) and max_advance > 0:
        return {
            "code": "DUE_SOON",
            "text": "⏰ Sắp đến hạn",
            "tag": "due_soon",
            "time_str": time_str,
            "seconds": diff,
        }
    else:
        return {
            "code": "PENDING",
            "text": "⏳ Chưa xong",
            "tag": "pending",
            "time_str": time_str,
            "seconds": diff,
        }


class ReminderEngine:
    """Động cơ theo dõi và phát thông báo nhắc nhở deadline nhiều mốc (Multi-stage Reminders)."""

    def __init__(self, task_manager, config_manager, notification_service):
        self.task_manager = task_manager
        self.config_manager = config_manager
        self.notification_service = notification_service

        # Bộ nhớ đệm lưu các thông báo đã gửi:
        # self.notified_thresholds: tập hợp các tuple (task_id, deadline_str, threshold_mins)
        # self.notified_overdue: tập hợp các tuple (task_id, deadline_str)
        self.notified_thresholds = set()
        self.notified_overdue = set()

    def reset_task_notification(self, task_id):
        """Xóa cache thông báo của một công việc khi công việc được sửa hoặc đổi trạng thái."""
        self.notified_thresholds = {item for item in self.notified_thresholds if item[0] != task_id}
        self.notified_overdue = {item for item in self.notified_overdue if item[0] != task_id}

    def clear_cache(self):
        """Xóa toàn bộ cache thông báo."""
        self.notified_thresholds.clear()
        self.notified_overdue.clear()

    def check_deadlines(self):
        """Quét toàn bộ danh sách công việc và gửi thông báo nếu đến các mốc hạn chót."""
        now = datetime.now()
        default_reminders = self.config_manager.get("default_reminders", [1440, 60, 30])
        sound_enabled = self.config_manager.get("play_sound", True)
        notify_overdue_enabled = self.config_manager.get("notify_overdue", True)

        alerts_sent = []

        for task in self.task_manager.tasks:
            if task.get("completed"):
                continue

            deadline_str = task.get("deadline", "")
            deadline_dt = parse_deadline_datetime(deadline_str)
            if not deadline_dt:
                continue

            task_key = (task["id"], deadline_str)

            # 1. Kiểm tra công việc đã quá hạn
            if now > deadline_dt:
                if notify_overdue_enabled and task_key not in self.notified_overdue:
                    self.notification_service.notify_overdue(task, sound_enabled=sound_enabled)
                    self.notified_overdue.add(task_key)
                    alerts_sent.append(("overdue", task, 0))

            # 2. Kiểm tra công việc sắp đến hạn theo từng mốc (3 ngày, 1 ngày, 1 tiếng,...)
            else:
                reminders = get_task_reminders(task, default_reminders)
                if not reminders:
                    continue

                remaining_seconds = (deadline_dt - now).total_seconds()
                remaining_minutes = max(1, int(remaining_seconds / 60))

                # Lấy danh sách các mốc đã bị vượt qua (thời gian còn lại <= mốc)
                triggered_thresholds = [m for m in reminders if remaining_minutes <= m]
                if not triggered_thresholds:
                    continue

                # Tìm mốc thấp nhất mà chưa được thông báo
                unnotified = [
                    m for m in triggered_thresholds if (task["id"], deadline_str, m) not in self.notified_thresholds
                ]

                if unnotified:
                    target_threshold = min(unnotified)
                    stage_label = minutes_to_label(target_threshold) + " trước"

                    self.notification_service.notify_due_soon(
                        task,
                        remaining_minutes=remaining_minutes,
                        stage_label=stage_label,
                        sound_enabled=sound_enabled,
                    )

                    # Đánh dấu mốc này và tất cả các mốc lớn hơn đã được xử lý (tránh spam)
                    for m in triggered_thresholds:
                        self.notified_thresholds.add((task["id"], deadline_str, m))

                    alerts_sent.append(("due_soon", task, target_threshold))

        return alerts_sent
