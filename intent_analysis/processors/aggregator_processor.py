import json
from core.base_processor import BaseKafkaProcessor
from core.logger import info, debug, error
from core.database import Database

class AggregatorProcessor(BaseKafkaProcessor):
    def __init__(self, config):
        super().__init__(config)
        kafka_config = config["kafka"]
        db_config = config["db"]

        self.consumer_group_id = kafka_config["consumer_groups"]["aggregator"]
        self.input_topic = kafka_config["aggregations_request_topic"]
        self.init_consumer(self.input_topic)

        self.db = Database(db_config)

    def process_records(self):
        info(f"AggregatorProcessor: Listening on topic '{self.input_topic}'...")
        for message in self.consumer:
            if not self.running:
                break

            msg_str = message.value
            debug(f"AggregatorProcessor received: {msg_str}")

            try:
                data = json.loads(msg_str)
                session_id = data.get("session_id")
                user_id = data.get("user_id")

                # Step 1: Retrieve session timestamps
                session_sql = """
                    SELECT start_time, end_time FROM sessions
                    WHERE id = %s
                """
                session_row = self.db.fetchone(session_sql, (session_id,))
                if not session_row:
                    error(f"AggregatorProcessor: No session found with id {session_id}")
                    continue

                start_time = session_row["start_time"]
                end_time = session_row["end_time"]

                info(f"Start Time: {start_time} and end time is {end_time} for session {session_id}")


                # Step 2: Gather transcriptions for the session based on timestamps
                select_transcriptions_sql = """
                    SELECT text FROM transcriptions
                    WHERE timestamp BETWEEN %s AND %s AND user_id = %s
                    ORDER BY id
                """
                rows = self.db.fetchall(select_transcriptions_sql, (start_time, end_time, user_id))
                all_text = [r["text"] for r in rows]

                # Step 3: Aggregate the text
                aggregated_text = "\n".join(all_text)
                info(f"AggregatorProcessor: Aggregated {len(all_text)} transcriptions for session {session_id}")

                # Step 4: Store the aggregated text in the sessions table
                update_session_sql = """
                    UPDATE sessions
                    SET summary = %s
                    WHERE id = %s
                """
                self.db.execute(update_session_sql, (aggregated_text, session_id))
                info(f"AggregatorProcessor: Stored summary in session {session_id}")

            except Exception as e:
                error(f"AggregatorProcessor Error: {e}")

        self.shutdown()
