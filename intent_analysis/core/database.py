import psycopg2
from psycopg2.extras import RealDictCursor
from core.logger import info, error

class Database:
    def __init__(self, db_config):
        self.host = db_config["host"]
        self.port = db_config["port"]
        self.database = db_config["database"]
        self.user = db_config["user"]
        self.password = db_config["password"]
        self.connection = None

    def connect(self):
        if self.connection is None or self.connection.closed != 0:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            info("Connected to Postgres")

    def close(self):
        if self.connection and self.connection.closed == 0:
            self.connection.close()
            info("Closed Postgres connection")

    def execute(self, query, params=None):
        """
        Execute INSERT/UPDATE/DELETE statements (no return).
        """
        self.connect()
        with self.connection.cursor() as cur:
            cur.execute(query, params)
            self.connection.commit()

    def fetchall(self, query, params=None):
        """
        Execute SELECT and return all rows as dictionaries.
        """
        self.connect()
        with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return rows

    def fetchone(self, query, params=None):
        """
        Execute SELECT and return a single row as dictionary.
        """
        self.connect()
        with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return row


def initialize_database(db: Database):
    """
    Creates the tables if they don't exist yet.
    For large-scale or production, you'd use migrations.
    """
    create_transcriptions_sql = """
    CREATE TABLE IF NOT EXISTS transcriptions (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255),
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        text TEXT NOT NULL,
        session_id INT DEFAULT NULL
    );
    """

    create_sessions_sql = """
    CREATE TABLE IF NOT EXISTS sessions (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255),
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP,
        active BOOLEAN DEFAULT TRUE,
        summary TEXT,
        session_creation_reasoning TEXT,
        session_destroy_reasoning TEXT
    );
    """

    try:
        db.execute(create_transcriptions_sql)
        db.execute(create_sessions_sql)
        info("Database tables ensured/created successfully.")
    except Exception as e:
        error(f"Error creating tables: {e}")
