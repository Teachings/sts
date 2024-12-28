from core.base_avro_processor import BaseAvroProcessor
from core.logger import info, debug, error
from core.database import Database

class PersistenceProcessor(BaseAvroProcessor):
    def __init__(self, config):
        super().__init__(config)
        kafka_cfg = config["kafka"]
        db_cfg = config["db"]
        self.input_topic = kafka_cfg["transcriptions_topic"]
        group_id = kafka_cfg["consumer_groups"]["persistence"]
        self.db = Database(db_cfg)

        self.init_consumer(group_id=group_id, topics=[self.input_topic], offset_reset="latest")

    def process_records(self):
        info(f"PersistenceProcessor: Listening on {self.input_topic} (Avro)...")
        while self.running:
            try:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    error(f"PersistenceProcessor consumer error: {msg.error()}")
                    continue

                payload = msg.value()
                if not payload:
                    continue

                user_id = payload.get("user", "UnknownUser")
                transcription = payload.get("text", "")
                timestamp = payload.get("timestamp", "")
                debug(f"PersistenceProcessor received: {transcription}")

                insert_sql = """
                    INSERT INTO transcriptions (user_id, text, timestamp)
                    VALUES (%s, %s, %s)
                """
                self.db.execute(insert_sql, (user_id, transcription, timestamp))
                debug("PersistenceProcessor: Inserted into DB")

            except Exception as e:
                error(f"PersistenceProcessor Avro Error: {e}")

        self.shutdown()