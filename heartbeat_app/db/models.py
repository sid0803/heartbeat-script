import sqlite3
import os

# Project root is two levels up from this file
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DatabaseManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            self.db_path = os.path.join(PROJECT_ROOT, "data", "heartbeat.db")
        else:
            self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # User table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                password_hash TEXT,
                preferences TEXT
            )
        ''')
        
        # Connector configs (multi-tenant)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connector_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                connector_type TEXT,
                config_json TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # Multi-tenant digests
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS digests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                content TEXT,
                source_type TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()
        conn.close()

    def save_digest(self, user_id: int, content: str, source_type: str = "periodic"):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO digests (user_id, content, source_type) VALUES (?, ?, ?)', (user_id, content, source_type))
        conn.commit()
        conn.close()

    def get_connector_config(self, user_id: int, connector_type: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT config_json, is_active FROM connector_configs WHERE user_id = ? AND connector_type = ?',
            (user_id, connector_type)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        import json
        return {"config": json.loads(row[0]), "is_active": bool(row[1])}

    def upsert_connector_config(self, user_id: int, connector_type: str, config: dict, is_active: int = 1):
        import json
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM connector_configs WHERE user_id = ? AND connector_type = ?',
            (user_id, connector_type)
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                'UPDATE connector_configs SET config_json = ?, is_active = ? WHERE id = ?',
                (json.dumps(config), is_active, row[0])
            )
        else:
            cursor.execute(
                'INSERT INTO connector_configs (user_id, connector_type, config_json, is_active) VALUES (?, ?, ?, ?)',
                (user_id, connector_type, json.dumps(config), is_active)
            )
        conn.commit()
        conn.close()

    def get_last_24h_digests(self, user_id: int) -> list:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM digests WHERE user_id = ? AND timestamp > datetime('now', '-1 day')", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def seed_mock_connectors(self, user_id: int):
        import json
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Add mock founder-facing connector configs
        mocks = [
            ("slack", {"channel_ids": ["C12345", "C67890"], "token": "xoxb-mock-token"}),
            ("notion", {"database_id": "mock-db-id", "token": "secret_mock_notion"}),
            ("git", {"repo_path": "."})
        ]
        
        for c_type, config in mocks:
            cursor.execute('''
                INSERT INTO connector_configs (user_id, connector_type, config_json, is_active)
                VALUES (?, ?, ?, 1)
            ''', (user_id, c_type, json.dumps(config)))
            
        conn.commit()
        conn.close()
