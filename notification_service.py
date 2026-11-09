import os
import winsound
from winotify import Notification, audio


class NotificationService:
    """Dịch vụ gửi thông báo Windows Toast khi sắp đến hạn hoặc quá hạn."""

    def __init__(self, app_id="Task Reminder"):
        self.app_id = app_id
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.icon_path = os.path.join(base_dir, "app_icon.png")
        if not os.path.exists(self.icon_path):
            self.icon_path = None

    def _play_fallback_sound(self, high_priority=False):
        """Phát âm thanh cảnh báo Windows khi cần thiết."""
        try:
            if high_priority:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            else:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

    def send_toast(self, title, message, sound_enabled=True, high_priority=False):
        """Gửi Windows Toast notification native."""
        try:
            toast = Notification(
                app_id=self.app_id,
                title=title,
                msg=message,
                icon=self.icon_path if self.icon_path and os.path.exists(self.icon_path) else "",
                duration="short" if not high_priority else "long",
            )

            if sound_enabled:
                if high_priority:
                    toast.set_audio(audio.Reminder, loop=False)
                else:
                    toast.set_audio(audio.Default, loop=False)
            else:
                toast.set_audio(audio.Silent, loop=False)

            toast.show()
            return True
        except Exception:
            if sound_enabled:
                self._play_fallback_sound(high_priority)
            return False

    def notify_due_soon(self, task, remaining_minutes, stage_label=None, sound_enabled=True):
        """Thông báo công việc sắp đến hạn tại một mốc cụ thể (3 ngày, 1 ngày, 1 tiếng,...)."""
        task_title = task.get("title", "Công việc")
        if stage_label:
            title = f"⏰ [{stage_label}] Sắp đến hạn: {task_title}"
        else:
            title = f"⏰ Sắp đến hạn: {task_title}"

        if remaining_minutes <= 1:
            time_str = "dưới 1 phút"
        elif remaining_minutes < 60:
            time_str = f"{remaining_minutes} phút"
        elif remaining_minutes < 1440:
            h = remaining_minutes // 60
            m = remaining_minutes % 60
            time_str = f"{h} giờ {m} phút" if m > 0 else f"{h} giờ"
        else:
            d = remaining_minutes // 1440
            h = (remaining_minutes % 1440) // 60
            time_str = f"{d} ngày {h} giờ" if h > 0 else f"{d} ngày"

        priority = task.get("priority", "Trung bình")
        deadline = task.get("deadline", "")
        msg = f"Còn khoảng {time_str} nữa là đến hạn ({deadline})!\nMức ưu tiên: {priority}"

        is_high = priority == "Cao"
        return self.send_toast(title, msg, sound_enabled=sound_enabled, high_priority=is_high)

    def notify_overdue(self, task, sound_enabled=True):
        """Thông báo công việc đã quá hạn."""
        title = f"🚨 Quá hạn: {task.get('title', 'Công việc')}"
        priority = task.get("priority", "Trung bình")
        deadline = task.get("deadline", "")
        msg = f"Công việc đã quá hạn deadline ({deadline})!\nMức ưu tiên: {priority}. Hãy kiểm tra và hoàn thành ngay."

        return self.send_toast(title, msg, sound_enabled=sound_enabled, high_priority=True)

    def notify_info(self, title, message, sound_enabled=False):
        """Thông báo thông tin chung (chạy nền, khởi động, v.v.)."""
        return self.send_toast(title, message, sound_enabled=sound_enabled, high_priority=False)
