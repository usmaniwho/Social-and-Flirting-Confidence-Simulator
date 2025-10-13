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
                    objectives TEXT,
                    started_at TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS session_summaries (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    mode TEXT,
                    scenario TEXT,
                    frs_result TEXT,
                    feedback TEXT,
                    objectives_completed TEXT,
                    stars_earned INTEGER,
                    ended_at TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            ''')
            conn.commit()

    def save_session(self, session_id: str, session_data: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO sessions
                (session_id, user_id, mode, scenario, objectives, started_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                session_data['user_id'],
                session_data['mode'],
                session_data['scenario'],
                json.dumps(session_data['objectives']),
                session_data['started_at'].isoformat()
            ))
            conn.commit()

    def get_session(self, session_id: str) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT user_id, mode, scenario, objectives, started_at
                FROM sessions WHERE session_id = ?
            ''', (session_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'user_id': row[0],
                    'mode': row[1],
                    'scenario': row[2],
                    'objectives': json.loads(row[3]),
                    'started_at': datetime.fromisoformat(row[4])
                }
            return None

    def session_exists(self, session_id: str) -> bool:
        return self.get_session(session_id) is not None

    def save_session_summary(self, session_id: str, summary_data: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO session_summaries
                (session_id, user_id, mode, scenario, frs_result, feedback, objectives_completed, stars_earned, ended_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                summary_data['user_id'],
                summary_data['mode'],
                summary_data['scenario'],
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
                SELECT user_id, mode, scenario, frs_result, feedback, objectives_completed, stars_earned, ended_at
                FROM session_summaries WHERE session_id = ?
            ''', (session_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'user_id': row[0],
                    'mode': row[1],
                    'scenario': row[2],
                    'frs_result': json.loads(row[3]),
                    'feedback': json.loads(row[4]) if row[4] else {},
                    'objectives_completed': json.loads(row[5]) if row[5] else [],
                    'stars_earned': row[6],
                    'ended_at': datetime.fromisoformat(row[7])
                }
            return None

# Global instance
session_store = SessionStore()
