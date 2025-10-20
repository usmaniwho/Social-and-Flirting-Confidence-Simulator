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
            cursor = conn.execute("PRAGMA table_info(session_summaries)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'personality' not in columns:
                conn.execute("ALTER TABLE session_summaries ADD COLUMN personality TEXT")

            # 🔹 ADDED: table for storing live transcript and emotional data
            conn.execute('''
                CREATE TABLE IF NOT EXISTS session_stream (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp TEXT,
                    speaker TEXT,           -- 'user' or 'ai'
                    text_chunk TEXT,
                    emotion_state TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            ''')

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

    # 🔹 ADDED: append transcript and emotional data during session
    def add_stream_chunk(self, session_id: str, speaker: str, text_chunk: str, emotion_state: str = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO session_stream (session_id, timestamp, speaker, text_chunk, emotion_state)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, datetime.utcnow().isoformat(), speaker, text_chunk, emotion_state))
            conn.commit()

    # 🔹 ADDED: fetch complete transcript for a session
    def get_full_transcript(self, session_id: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT timestamp, speaker, text_chunk, emotion_state
                FROM session_stream WHERE session_id = ?
                ORDER BY timestamp ASC
            ''', (session_id,))
            return [
                {
                    'timestamp': row[0],
                    'speaker': row[1],
                    'text': row[2],
                    'emotion_state': row[3]
                }
                for row in cursor.fetchall()
            ]

    # 🔹 ADDED: summarize emotional trend for the session
    def summarize_emotions(self, session_id: str) -> Dict[str, float]:
        transcript = self.get_full_transcript(session_id)
        counts = {}
        for entry in transcript:
            if entry['emotion_state']:
                counts[entry['emotion_state']] = counts.get(entry['emotion_state'], 0) + 1
        total = sum(counts.values()) or 1
        return {k: round(v / total, 2) for k, v in counts.items()}


# Global instance
session_store = SessionStore()
