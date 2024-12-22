import json
from core.base_processor import BaseKafkaProcessor
from core.logger import info, debug, error
from core.database import Database

class SessionProcessor(BaseKafkaProcessor):
    def __init__(self, config):
        super().__init__(config)
        kafka_config = config["kafka"]
        db_config = config["db"]

        self.consumer_group_id = kafka_config["consumer_groups"]["session"]
        self.input_topic = kafka_config["sessions_management_topic"]
        self.aggregations_topic = kafka_config["aggregations_request_topic"]

        self.init_consumer(self.input_topic)
        self.init_producer()

        self.db = Database(db_config)

    def process_records(self):
        info(f"SessionProcessor: Listening on topic '{self.input_topic}'...")
        for message in self.consumer:
            if not self.running:
                break

            msg_str = message.value
            debug(f"SessionProcessor received: {msg_str}")

            try:
                data = json.loads(msg_str)
                command = data.get("command")  # e.g., "start_session", "stop_session"
                user_id = data.get("user_id")

                if command == "start_session":
                    # Create a new row in sessions
                    insert_sql = """
                        INSERT INTO sessions (user_id) VALUES (%s)
                        RETURNING id
                    """
                    result = self.db.fetchall(insert_sql, (user_id,))
                    new_session_id = result[0]["id"]
                    info(f"SessionProcessor: Started new session {new_session_id} for {user_id}")

                elif command == "stop_session":
                    session_id = data.get("session_id")
                    # Mark session as ended
                    update_sql = """
                        UPDATE sessions 
                        SET end_time = CURRENT_TIMESTAMP, active = FALSE
                        WHERE id = %s
                    """
                    self.db.execute(update_sql, (session_id,))
                    info(f"SessionProcessor: Stopped session {session_id}")

                    # Trigger aggregator
                    agg_msg = {"session_id": session_id, "user_id": user_id}
                    self.producer.send(self.aggregations_topic, agg_msg)
                    info(f"SessionProcessor: Aggregation request sent for session {session_id}")

            except Exception as e:
                error(f"SessionProcessor Error: {e}")

        self.shutdown()
