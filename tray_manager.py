import os
from PIL import Image, ImageDraw
import pystray

def create_default_icon_image():
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([4, 4, size - 4, size - 4], radius=14, fill='#2563eb')
    draw.line([(18, 34), (28, 44), (46, 22)], fill='white', width=6, joint='curve')
    draw.ellipse([44, 8, 56, 20], fill='#ef4444', outline='white', width=2)
    return img

class TrayManager:

    def __init__(self, on_open=None, on_check_now=None, on_settings=None, on_toggle_startup=None, on_exit=None, is_startup_enabled=None):
        self.on_open = on_open
        self.on_check_now = on_check_now
        self.on_settings = on_settings
        self.on_toggle_startup = on_toggle_startup
        self.on_exit = on_exit
        self.is_startup_enabled = is_startup_enabled
        self.icon = None
        self._is_running = False

    def _get_icon_image(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        png_path = os.path.join(base_dir, 'app_icon.png')
        if os.path.exists(png_path):
            try:
                return Image.open(png_path)
            except Exception:
                pass
        return create_default_icon_image()

    def _create_menu(self):

        def _check_startup(item):
            if callable(self.is_startup_enabled):
                return self.is_startup_enabled()
            return False
        menu_items = [pystray.MenuItem('📋 Mở Task Reminder', lambda icon, item: self._safe_call(self.on_open), default=True), pystray.MenuItem('🔔 Kiểm tra deadline ngay', lambda icon, item: self._safe_call(self.on_check_now)), pystray.MenuItem('⚙️ Cài đặt hệ thống', lambda icon, item: self._safe_call(self.on_settings)), pystray.Menu.SEPARATOR, pystray.MenuItem('🚀 Tự khởi động cùng Windows', lambda icon, item: self._safe_call(self.on_toggle_startup), checked=_check_startup), pystray.Menu.SEPARATOR, pystray.MenuItem('❌ Thoát hoàn toàn', lambda icon, item: self._safe_call(self.on_exit))]
        return pystray.Menu(*menu_items)

    def _safe_call(self, callback):
        if callable(callback):
            try:
                callback()
            except Exception as e:
                print(f'[TrayManager Error] {e}')

    def start(self):
        if self._is_running and self.icon is not None:
            return
        image = self._get_icon_image()
        menu = self._create_menu()
        self.icon = pystray.Icon('TaskReminder', image, 'Task Reminder - Quản lý công việc', menu=menu)
        self.icon.run_detached()
        self._is_running = True

    def stop(self):
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                pass
            self.icon = None
            self._is_running = False

    def update_tooltip(self, pending_count=0, overdue_count=0):
        if self.icon is not None:
            parts = ['Task Reminder']
            if overdue_count > 0:
                parts.append(f'🚨 {overdue_count} quá hạn')
            if pending_count > 0:
                parts.append(f'⏳ {pending_count} việc cần làm')
            elif overdue_count == 0:
                parts.append('✨ Đã xong hết việc!')
            tooltip = ' | '.join(parts)
            try:
                self.icon.title = tooltip[:128]
            except Exception:
                pass
