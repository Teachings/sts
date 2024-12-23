import json
import datetime
from core.base_processor import BaseKafkaProcessor
from core.logger import info, debug, error
from core.database import Database

SESSION_TIMEOUT_HOURS = 4

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
                # e.g. data = {
                #    "session_decision": "CREATE" | "DESTROY" | "NO_ACTION",
                #    "reasoning": "...",
                #    "user_id": "mukul"
                # }
                session_decision = data.get("session_decision")
                reasoning = data.get("reasoning")
                user_id = data.get("user_id")
                timestamp = data.get("timestamp")

                if session_decision == "NO_ACTION":
                    # Do nothing, just ignore
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
                    # If there's an active session, see if it's older than 4 hours
                    if active_session:
                        # Calculate how long it's been active
                        start_time = active_session["start_time"]
                        now = datetime.datetime.utcnow()
                        # Ensure your DB is storing times in UTC or convert accordingly
                        delta = now - start_time
                        hours_diff = delta.total_seconds() / 3600

                        if hours_diff < SESSION_TIMEOUT_HOURS:
                            # Already have an active session less than 4 hours old
                            debug(f"SessionProcessor: Session already active (id={active_session['id']}) < 4 hours. Skipping creation.")
                            continue
                        else:
                            # Auto-destroy the old session and create a new one
                            session_id = active_session["id"]
                            self.auto_close_session(session_id)

                    # Create new session
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
                    # If no active session, do nothing
                    if not active_session:
                        debug(f"SessionProcessor: No active session to destroy for user {user_id}, ignoring.")
                        continue

                    session_id = active_session["id"]
                    # Mark session as ended with manually set end_time
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
                    agg_msg = {"session_id": session_id, "user_id": user_id}
                    self.producer.send(self.aggregations_topic, agg_msg)
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
                session_destroy_reasoning = 'Timed out after 4 hours of inactivity'
            WHERE id = %s
        """, (session_id,))
        info(f"SessionProcessor: Auto-closed old session {session_id}")
