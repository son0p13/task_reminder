import os
import sys
import winreg
REG_KEY_PATH = 'Software\\Microsoft\\Windows\\CurrentVersion\\Run'
APP_NAME = 'TaskReminderApp'

class AutoStartManager:

    @staticmethod
    def get_startup_command():
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
            return f'"{exe_path}" --startup'
        base_dir = os.path.dirname(os.path.abspath(__file__))
        main_script = os.path.join(base_dir, 'main.py')
        py_dir = os.path.dirname(sys.executable)
        pythonw_path = os.path.join(py_dir, 'pythonw.exe')
        exec_to_use = pythonw_path if os.path.exists(pythonw_path) else sys.executable
        return f'"{exec_to_use}" "{main_script}" --startup'

    @staticmethod
    def is_autostart_enabled():
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, APP_NAME)
                return True
        except (FileNotFoundError, OSError):
            return False

    @staticmethod
    def set_autostart(enable=True):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
                if enable:
                    cmd = AutoStartManager.get_startup_command()
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
            return True
        except OSError:
            return False
