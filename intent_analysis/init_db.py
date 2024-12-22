from core.config_loader import load_config
from core.database import Database, initialize_database

if __name__ == "__main__":
    config = load_config()
    db = Database(config["db"])
    initialize_database(db)
