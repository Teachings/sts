import datetime
import time
from core.base_avro_processor import BaseAvroProcessor
from core.logger import info, debug, error
from core.database import Database

class SessionProcessor(BaseAvroProcessor):
    def __init__(self, config):
        super().__init__(config)
        kafka_cfg = config["kafka"]
        db_cfg = config["db"]
        app_cfg = config["app"]

        self.session_timeout_seconds = app_cfg["session_timeout_seconds"]  # Use seconds for easier calculations.

        self.input_topic = kafka_cfg["sessions_management_topic"]
        self.aggregations_topic = kafka_cfg["aggregations_request_topic"]

        group_id = kafka_cfg["consumer_groups"]["session"]
        self.db = Database(db_cfg)

        # Avro consumer for session mgmt
        self.init_consumer(group_id=group_id, topics=[self.input_topic], offset_reset="latest")

        # Avro producer for aggregator requests
        self.init_producer(
            producer_name="aggregator_producer",
            avro_schema_file="schemas/aggregator_value.avsc"
        )

        # Start the background thread for timeout checks
        self.start_timeout_check_thread()

    def process_records(self):
        info(f"SessionProcessor: Listening on topic '{self.input_topic}' (Avro)...")
        while self.running:
            try:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    error(f"SessionProcessor consumer error: {msg.error()}")
                    continue

                data = msg.value()
                if not data:
                    continue

                session_decision = data.get("session_decision")
                reasoning = data.get("reasoning")
                user_id = data.get("user_id")
                timestamp = data.get("timestamp")

                if session_decision == "CREATE":
                    self.db.execute("""
                        INSERT INTO sessions (user_id, start_time, session_creation_reasoning)
                        VALUES (%s, %s, %s)
                    """, (user_id, timestamp, reasoning))

                    # Fetch the newly created session ID
                    new_session = self.db.fetchone("""
                        SELECT id
                        FROM sessions
                        WHERE user_id = %s
                        ORDER BY id DESC
                        LIMIT 1
                    """, (user_id,))
                    new_session_id = new_session["id"]

                    info(f"SessionProcessor: Created new session {new_session_id} for {user_id}")

                elif session_decision == "DESTROY":
                    active_session = self.db.fetchone("""
                        SELECT id, start_time 
                        FROM sessions 
                        WHERE user_id = %s AND active = TRUE
                        ORDER BY id DESC
                        LIMIT 1
                    """, (user_id,))

                    if active_session:
                        session_id = active_session["id"]

                        # Fetch the timestamp of the last transcription for this session
                        last_transcription_time = self.db.fetchone("""
                            SELECT timestamp
                            FROM transcriptions
                            WHERE session_id = %s
                            ORDER BY timestamp DESC
                            LIMIT 1
                        """, (session_id,))

                        if last_transcription_time:
                            end_time = last_transcription_time["timestamp"]
                        else:
                            # If no transcriptions (unlikely), use the current time
                            end_time = datetime.datetime.now()

                        self.db.execute("""
                            UPDATE sessions
                            SET end_time = %s,
                                active = FALSE,
                                session_destroy_reasoning = %s
                            WHERE id = %s
                        """, (end_time, reasoning, session_id))

                        info(f"SessionProcessor: Stopped session {session_id} for user {user_id} with end_time {end_time}")

                        # Trigger aggregator
                        agg_msg = {
                            "session_id": session_id,
                            "user_id": user_id
                        }
                        self.produce_message(
                            producer_name="aggregator_producer",
                            topic_name=self.aggregations_topic,
                            value_dict=agg_msg
                        )
                        info(f"SessionProcessor: Aggregation request sent for session {session_id}")

            except Exception as e:
                error(f"SessionProcessor Error: {e}")

        self.shutdown()

    def auto_close_session(self, session_id: int, user_id: str):
        """
        Utility to end a session automatically due to timeout.
        """

        # Fetch the timestamp of the last transcription for this session
        last_transcription_time = self.db.fetchone("""
            SELECT timestamp
            FROM transcriptions
            WHERE session_id = %s
            ORDER BY timestamp DESC
            LIMIT 1
        """, (session_id,))

        if last_transcription_time:
            end_time = last_transcription_time["timestamp"]
        else:
            # If no transcriptions (unlikely), use the current time
            end_time = datetime.datetime.now()
        
        self.db.execute("""
            UPDATE sessions
            SET end_time = %s,
                active = FALSE,
                session_destroy_reasoning = 'Timed out.'
            WHERE id = %s
        """, (end_time, session_id))
        info(f"SessionProcessor: Auto-closed old session {session_id} with end_time {end_time}")

        # Trigger aggregator
        agg_msg = {
            "session_id": session_id,
            "user_id": user_id
        }
        self.produce_message(
            producer_name="aggregator_producer",
            topic_name=self.aggregations_topic,
            value_dict=agg_msg
        )
        info(f"SessionProcessor: Aggregation request sent for session {session_id}")

    def start_timeout_check_thread(self):
        """Starts a background thread to periodically check for timed-out sessions."""
        import threading
        timeout_check_thread = threading.Thread(target=self.run_timeout_checks)
        timeout_check_thread.daemon = True  # Allow the program to exit even if this thread is running
        timeout_check_thread.start()

    def run_timeout_checks(self):
        """Periodically checks for sessions that have exceeded the timeout and closes them."""
        while self.running:
            try:
                active_sessions = self.db.fetchall("""
                    SELECT id, user_id
                    FROM sessions
                    WHERE active = TRUE
                """)

                for session in active_sessions:
                    session_id = session["id"]
                    user_id = session["user_id"]

                    # Get the last activity timestamp (either last transcription or session start time)
                    last_activity_time = self.db.fetchone("""
                        SELECT COALESCE(
                            (SELECT timestamp FROM transcriptions WHERE session_id = %s ORDER BY timestamp DESC LIMIT 1),
                            (SELECT start_time FROM sessions WHERE id = %s)
                        ) AS last_activity
                    """, (session_id, session_id))

                    if last_activity_time and last_activity_time["last_activity"]:
                        time_since_last_activity = (datetime.datetime.now() - last_activity_time["last_activity"]).total_seconds()

                        if time_since_last_activity > self.session_timeout_seconds:
                            self.auto_close_session(session_id, user_id)
            except Exception as e:
                error(f"SessionProcessor Timeout Check Error: {e}")

            time.sleep(self.session_timeout_seconds)  # Check every `session_timeout_seconds`