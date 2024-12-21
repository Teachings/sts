from termcolor import colored

def info(message: str):
    print(colored(f"[INFO] {message}", "green"))

def warning(message: str):
    print(colored(f"[WARNING] {message}", "yellow"))

def error(message: str):
    print(colored(f"[ERROR] {message}", "red"))

def debug(message: str):
    print(colored(f"[DEBUG] {message}", "blue"))
