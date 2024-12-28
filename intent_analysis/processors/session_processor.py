import datetime
from core.base_avro_processor import BaseAvroProcessor
from core.logger import info, debug, error
from core.database import Database

class SessionProcessor(BaseAvroProcessor):
    def __init__(self, config):
        super().__init__(config)
        kafka_cfg = config["kafka"]
        db_cfg = config["db"]
        app_cfg = config["app"]

        self.voice_session_timeout_hours = app_cfg["voice_session_timeout_hours"]

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

                if session_decision == "NO_ACTION":
                    debug("SessionProcessor: NO_ACTION received, ignoring.")
                    continue

                # Check if user has an active session
                active_session = self.db.fetchone("""
                    SELECT id, start_time 
                    FROM sessions 
                    WHERE user_id = %s AND active = TRUE
                    ORDER BY id DESC
                    LIMIT 1
                """, (user_id,))

                if session_decision == "CREATE":
                    if active_session:
                        # Check if old session is older than voice_session_timeout_hours
                        start_time = active_session["start_time"]
                        now = datetime.datetime.now()
                        delta = now - start_time
                        hours_diff = delta.total_seconds() / 3600

                        if hours_diff < self.voice_session_timeout_hours:
                            debug(f"SessionProcessor: Session already active < {self.voice_session_timeout_hours} hours. Skipping creation.")
                            continue
                        else:
                            # Auto-close old session
                            self.auto_close_session(active_session["id"])

                    # Create a new session
                    self.db.execute("""
                        INSERT INTO sessions (user_id, session_creation_reasoning, start_time)
                        VALUES (%s, %s, %s)
                    """, (user_id, reasoning, timestamp))


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
                    if not active_session:
                        debug(f"No active session to destroy for user {user_id}, ignoring.")
                        continue

                    session_id = active_session["id"]
                    self.db.execute("""
                        UPDATE sessions
                        SET end_time = %s,
                            active = FALSE,
                            session_destroy_reasoning = %s
                        WHERE id = %s
                    """, (timestamp, reasoning, session_id))

                    info(f"SessionProcessor: Stopped session {session_id} for user {user_id}")

                    #debug to cehck session start and end time
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

    def auto_close_session(self, session_id: int):
        """
        Utility to end a session automatically due to timeout
        (in case user forgot to explicitly destroy it).
        """
        self.db.execute("""
            UPDATE sessions
            SET end_time = CURRENT_TIMESTAMP,
                active = FALSE,
                session_destroy_reasoning = 'Timed out.'
            WHERE id = %s
        """, (session_id,))
        info(f"SessionProcessor: Auto-closed old session {session_id}")
