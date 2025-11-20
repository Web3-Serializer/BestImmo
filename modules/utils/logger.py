import colorama
from datetime import datetime

colorama.init()

class Logger:

    def __init__(self, name: str):
        self.module = name.upper()

    def _timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def info(self, message):
        print(f"    {colorama.Fore.CYAN}[INFO] - {self.module} - {self._timestamp()} - {message}{colorama.Style.RESET_ALL}")

    def warning(self, message):
        print(f"    {colorama.Fore.YELLOW}[WARNING] - {self.module} - {self._timestamp()} - {message}{colorama.Style.RESET_ALL}")

    def error(self, message):
        print(f"    {colorama.Fore.RED}[ERROR] - {self.module} - {self._timestamp()} - {message}{colorama.Style.RESET_ALL}")

    def success(self, message):
        print(f"    {colorama.Fore.GREEN}[SUCCESS] - {self.module} - {self._timestamp()} - {message}{colorama.Style.RESET_ALL}")
