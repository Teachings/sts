import yaml
import os

def load_config(config_path: str = "config/config.yml"):
    """
    Loads the YAML configuration from the given path.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at {config_path}")
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
    return config
