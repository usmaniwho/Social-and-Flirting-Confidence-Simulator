import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List

class SessionStore:
    def __init__(self, db_path: str = "sessions.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    mode TEXT,
                    scenario TEXT,
                    personality TEXT,
                    objectives TEXT,
                    started_at TEXT
                )
            ''')
            # Check and add personality column to sessions if missing
            cursor = conn.execute("PRAGMA table_info(sessions)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'personality' not in columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN personality TEXT")

            conn.execute('''
                CREATE TABLE IF NOT EXISTS session_summaries (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    mode TEXT,
                    scenario TEXT,
                    personality TEXT,
                    frs_result TEXT,
                    feedback TEXT,
                    objectives_completed TEXT,
                    stars_earned INTEGER,
                    ended_at TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            ''')
            # Check and add personality column to session_summaries if missing
            cursor = conn.execute("PRAGMA table_info(session_summaries)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'personality' not in columns:
                conn.execute("ALTER TABLE session_summaries ADD COLUMN personality TEXT")

            conn.commit()

    def save_session(self, session_id: str, session_data: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO sessions
                (session_id, user_id, mode, scenario, personality, objectives, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                session_data['user_id'],
                session_data['mode'],
                session_data['scenario'],
                session_data.get('personality'),
                json.dumps(session_data['objectives']),
                session_data['started_at'].isoformat()
            ))
            conn.commit()

    def get_session(self, session_id: str) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT user_id, mode, scenario, personality, objectives, started_at
                FROM sessions WHERE session_id = ?
            ''', (session_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'user_id': row[0],
                    'mode': row[1],
                    'scenario': row[2],
                    'personality': row[3],
                    'objectives': json.loads(row[4]),
                    'started_at': datetime.fromisoformat(row[5])
                }
            return None

    def session_exists(self, session_id: str) -> bool:
        return self.get_session(session_id) is not None

    def save_session_summary(self, session_id: str, summary_data: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO session_summaries
                (session_id, user_id, mode, scenario, personality, frs_result, feedback, objectives_completed, stars_earned, ended_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                summary_data['user_id'],
                summary_data['mode'],
                summary_data['scenario'],
                summary_data.get('personality'),
                json.dumps(summary_data['frs_result']),
                json.dumps(summary_data.get('feedback', {})),
                json.dumps(summary_data.get('objectives_completed', [])),
                summary_data['stars_earned'],
                summary_data['ended_at'].isoformat()
            ))
            conn.commit()

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT user_id, mode, scenario, personality, frs_result, feedback, objectives_completed, stars_earned, ended_at
                FROM session_summaries WHERE session_id = ?
            ''', (session_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'user_id': row[0],
                    'mode': row[1],
                    'scenario': row[2],
                    'personality': row[3],
                    'frs_result': json.loads(row[4]),
                    'feedback': json.loads(row[5]) if row[5] else {},
                    'objectives_completed': json.loads(row[6]) if row[6] else [],
                    'stars_earned': row[7],
                    'ended_at': datetime.fromisoformat(row[8])
                }
            return None

# Global instance
session_store = SessionStore()
