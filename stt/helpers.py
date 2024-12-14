from termcolor import colored
from datetime import datetime


def log(message, level="INFO", color="cyan"):
    """Log messages with timestamp and optional color."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    levels = {"INFO": "cyan", "WARNING": "yellow", "ERROR": "red", "SUCCESS": "green"}
    level_color = levels.get(level.upper(), color)
    print(colored(f"[{timestamp}] [{level}] {message}", level_color))
