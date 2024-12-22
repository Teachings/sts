import json
from datetime import datetime
from core.base_processor import BaseKafkaProcessor
from core.logger import info, debug, error
from core.database import Database

class PersistenceProcessor(BaseKafkaProcessor):
    def __init__(self, config):
        super().__init__(config)
        kafka_config = config["kafka"]
        db_config = config["db"]

        self.consumer_group_id = kafka_config["consumer_groups"]["persistence"]
        self.input_topic = kafka_config["transcriptions_topic"]
        self.init_consumer(self.input_topic)

        # DB
        self.db = Database(db_config)

    def process_records(self):
        info(f"PersistenceProcessor: Listening on topic '{self.input_topic}'...")
        for message in self.consumer:
            if not self.running:
                break

            transcription = message.value
            debug(f"PersistenceProcessor received: {transcription}")

            try:
                # For simplicity, assume user_id is embedded or we use some default
                # Example: "USER123: Hello, how are you?"
                # We'll parse user_id from the string or set a default
                parts = transcription.split(":", 1)
                if len(parts) == 2:
                    user_id, text = parts[0].strip(), parts[1].strip()
                else:
                    user_id, text = "UnknownUser", transcription

                insert_sql = """
                    INSERT INTO transcriptions (user_id, text) 
                    VALUES (%s, %s)
                """
                self.db.execute(insert_sql, (user_id, text))
                debug("PersistenceProcessor: Inserted into DB")
            except Exception as e:
                error(f"PersistenceProcessor Error: {e}")

        self.shutdown()
