import json
import os
DEFAULT_CONFIG = {'reminder_advance_minutes': 30, 'default_reminders': [1440, 60, 30], 'check_interval_seconds': 30, 'autostart': False, 'minimize_to_tray_on_close': True, 'play_sound': True, 'notify_overdue': True, 'notify_due_today': True, 'has_shown_tray_hint': False}

class ConfigManager:

    def __init__(self, filename='settings.json'):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.filepath = os.path.join(base_dir, filename)
        self.config = dict(DEFAULT_CONFIG)
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.filepath):
            self.save_config()
            return
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self.config.update(data)
        except (json.JSONDecodeError, OSError):
            self.save_config()

    def save_config(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except OSError:
            pass

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

    def update(self, new_data):
        self.config.update(new_data)
        self.save_config()
