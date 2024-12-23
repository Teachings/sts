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

            raw_str = message.value
            payload = json.loads(raw_str)
            user_id = payload.get("user", "UnknownUser")
            transcription = payload.get("text", "")
            timestamp = payload.get("timestamp", "")
            debug(f"PersistenceProcessor received: {transcription}")

            try:
                #query with timestamp
                insert_sql = """
                    INSERT INTO transcriptions (user_id, text, timestamp)
                    VALUES (%s, %s, %s)
                """
                self.db.execute(insert_sql, (user_id, transcription, timestamp))
                debug("PersistenceProcessor: Inserted into DB")
            except Exception as e:
                error(f"PersistenceProcessor Error: {e}")

        self.shutdown()
