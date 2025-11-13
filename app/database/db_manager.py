"""
Database Manager
SQLite database for session persistence
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.models.schemas import TestSession, TestResult, HardwareProfile, AIAnalysisResult, DecisionResult, Report

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database for session persistence"""
    
    def __init__(self, db_path: str = "void_sessions.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                ipc_id TEXT NOT NULL,
                status TEXT NOT NULL,
                progress_percent REAL DEFAULT 0.0,
                start_time TEXT NOT NULL,
                end_time TEXT,
                total_duration REAL,
                hardware_profile TEXT,
                test_cases TEXT,
                test_results TEXT,
                ai_analysis TEXT,
                decision TEXT,
                reports TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Test results table (for easier querying)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                test_id TEXT NOT NULL,
                test_name TEXT NOT NULL,
                status TEXT NOT NULL,
                metrics TEXT,
                errors TEXT,
                duration REAL,
                start_time TEXT,
                end_time TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_ipc_id ON sessions(ipc_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_test_results_session ON test_results(session_id)')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized: {self.db_path}")
    
    def save_session(self, session: TestSession):
        """Save or update session in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Serialize complex objects
            hardware_profile_json = json.dumps(session.hardware_profile.model_dump(), default=str) if session.hardware_profile else None
            test_cases_json = json.dumps([tc.model_dump() for tc in session.test_cases], default=str) if session.test_cases else None
            test_results_json = json.dumps([tr.model_dump() for tr in session.test_results], default=str) if session.test_results else None
            ai_analysis_json = json.dumps(session.ai_analysis.model_dump(), default=str) if session.ai_analysis else None
            decision_json = json.dumps(session.decision.model_dump(), default=str) if session.decision else None
            reports_json = json.dumps([r.model_dump() for r in session.reports], default=str) if session.reports else None
            
            # Check if session exists
            cursor.execute('SELECT session_id FROM sessions WHERE session_id = ?', (session.session_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing session
                cursor.execute('''
                    UPDATE sessions SET
                        ipc_id = ?,
                        status = ?,
                        progress_percent = ?,
                        end_time = ?,
                        total_duration = ?,
                        hardware_profile = ?,
                        test_cases = ?,
                        test_results = ?,
                        ai_analysis = ?,
                        decision = ?,
                        reports = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                ''', (
                    session.ipc_id,
                    session.status,
                    session.progress_percent,
                    session.end_time.isoformat() if session.end_time else None,
                    session.total_duration,
                    hardware_profile_json,
                    test_cases_json,
                    test_results_json,
                    ai_analysis_json,
                    decision_json,
                    reports_json,
                    session.session_id
                ))
            else:
                # Insert new session
                cursor.execute('''
                    INSERT INTO sessions (
                        session_id, ipc_id, status, progress_percent,
                        start_time, end_time, total_duration,
                        hardware_profile, test_cases, test_results,
                        ai_analysis, decision, reports
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session.session_id,
                    session.ipc_id,
                    session.status,
                    session.progress_percent,
                    session.start_time.isoformat(),
                    session.end_time.isoformat() if session.end_time else None,
                    session.total_duration,
                    hardware_profile_json,
                    test_cases_json,
                    test_results_json,
                    ai_analysis_json,
                    decision_json,
                    reports_json
                ))
            
            # Update test_results table
            if session.test_results:
                cursor.execute('DELETE FROM test_results WHERE session_id = ?', (session.session_id,))
                for result in session.test_results:
                    cursor.execute('''
                        INSERT INTO test_results (
                            session_id, test_id, test_name, status,
                            metrics, errors, duration, start_time, end_time
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        session.session_id,
                        result.test_id,
                        result.test_name,
                        result.status.value,
                        json.dumps(result.metrics, default=str) if result.metrics else None,
                        json.dumps(result.errors, default=str) if result.errors else None,
                        result.duration,
                        result.start_time.isoformat() if result.start_time else None,
                        result.end_time.isoformat() if result.end_time else None
                    ))
            
            conn.commit()
            logger.debug(f"Session {session.session_id} saved to database")
        except Exception as e:
            logger.error(f"Error saving session to database: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def load_session(self, session_id: str) -> Optional[TestSession]:
        """Load session from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Deserialize session
            session_dict = dict(row)
            
            # Parse JSON fields
            from app.models.schemas import TestCase
            
            hardware_profile = None
            if session_dict['hardware_profile']:
                hardware_data = json.loads(session_dict['hardware_profile'])
                hardware_profile = HardwareProfile(**hardware_data)
            
            test_cases = []
            if session_dict['test_cases']:
                test_cases_data = json.loads(session_dict['test_cases'])
                test_cases = [TestCase(**tc) for tc in test_cases_data]
            
            test_results = []
            if session_dict['test_results']:
                test_results_data = json.loads(session_dict['test_results'])
                test_results = [TestResult(**tr) for tr in test_results_data]
            
            ai_analysis = None
            if session_dict['ai_analysis']:
                ai_data = json.loads(session_dict['ai_analysis'])
                ai_analysis = AIAnalysisResult(**ai_data)
            
            decision = None
            if session_dict['decision']:
                decision_data = json.loads(session_dict['decision'])
                decision = DecisionResult(**decision_data)
            
            reports = []
            if session_dict['reports']:
                reports_data = json.loads(session_dict['reports'])
                reports = [Report(**r) for r in reports_data]
            
            session = TestSession(
                session_id=session_dict['session_id'],
                ipc_id=session_dict['ipc_id'],
                status=session_dict['status'],
                progress_percent=session_dict['progress_percent'],
                start_time=datetime.fromisoformat(session_dict['start_time']),
                end_time=datetime.fromisoformat(session_dict['end_time']) if session_dict['end_time'] else None,
                total_duration=session_dict['total_duration'],
                hardware_profile=hardware_profile,
                test_cases=test_cases,
                test_results=test_results,
                ai_analysis=ai_analysis,
                decision=decision,
                reports=reports
            )
            
            return session
        except Exception as e:
            logger.error(f"Error loading session from database: {e}")
            return None
        finally:
            conn.close()
    
    def list_sessions(self, limit: Optional[int] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all sessions with optional filtering"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            query = 'SELECT session_id, ipc_id, status, progress_percent, start_time, end_time FROM sessions'
            params = []
            
            if status:
                query += ' WHERE status = ?'
                params.append(status)
            
            query += ' ORDER BY start_time DESC'
            
            if limit:
                query += ' LIMIT ?'
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []
        finally:
            conn.close()
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
            conn.commit()
            deleted = cursor.rowcount > 0
            logger.info(f"Session {session_id} deleted from database")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def update_session_status(self, session_id: str, status: str, progress_percent: Optional[float] = None):
        """Update session status quickly"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if progress_percent is not None:
                cursor.execute('''
                    UPDATE sessions SET status = ?, progress_percent = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                ''', (status, progress_percent, session_id))
            else:
                cursor.execute('''
                    UPDATE sessions SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                ''', (status, session_id))
            conn.commit()
        except Exception as e:
            logger.error(f"Error updating session status: {e}")
            conn.rollback()
        finally:
            conn.close()

