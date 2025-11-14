"""
Test Session Manager
Manages complete test sessions from start to finish
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional, Callable, List
from app.models.schemas import TestSession, HardwareProfile, TestResult, CheckpointResult, DecisionStatus
from app.core.hardware_detection import HardwareDetector
from app.core.test_loader import TestCaseLoader
from app.core.test_generator import TestGenerator
from app.core.test_executor import TestExecutor
from app.ai.decision_engine import DecisionEngine
from app.reporting.json_reporter import JSONReporter
from app.reporting.html_reporter import HTMLReporter
from app.reporting.pdf_reporter import PDFReporter
from app.database.db_manager import DatabaseManager
from app.core.preset_loader import PresetLoader

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages complete test sessions with database persistence"""
    
    def __init__(self):
        self.sessions: Dict[str, TestSession] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}  # Track running test cycles
        self.db = DatabaseManager()
        self.hardware_detector = HardwareDetector()
        self.test_loader = TestCaseLoader()
        self.preset_loader = PresetLoader()
        self.test_generator = TestGenerator(self.test_loader)
        self.test_executor = TestExecutor(max_parallel=8)
        self.decision_engine = DecisionEngine()
        self.json_reporter = JSONReporter()
        self.html_reporter = HTMLReporter()
        self.pdf_reporter = PDFReporter()
        
        # Load sessions from database on startup
        self._load_sessions_from_db()
        
    def _load_sessions_from_db(self):
        """Load sessions from database on startup"""
        try:
            db_sessions = self.db.list_sessions(limit=100)
            for session_data in db_sessions:
                session = self.db.load_session(session_data['session_id'])
                if session:
                    self.sessions[session.session_id] = session
            logger.info(f"Loaded {len(self.sessions)} sessions from database")
        except Exception as e:
            logger.error(f"Error loading sessions from database: {e}")
    
    def create_session(self, ipc_id: Optional[str] = None) -> TestSession:
        """Create new test session"""
        session_id = str(uuid.uuid4())
        
        if not ipc_id:
            ipc_id = f"IPC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = TestSession(
            session_id=session_id,
            ipc_id=ipc_id,
            status="initializing",
            progress_percent=0.0
        )
        
        self.sessions[session_id] = session
        self.db.save_session(session)  # Save to database
        logger.info(f"Created session {session_id} for IPC {ipc_id}")
        
        return session
    
    async def run_complete_test_cycle(
        self, 
        session_id: str,
        progress_callback: Optional[Callable] = None,
        selected_test_ids: Optional[list[str]] = None
    ) -> TestSession:
        """Run complete 9-step test cycle"""
        session = self.sessions.get(session_id)
        if not session:
            # Try loading from database
            session = self.db.load_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            self.sessions[session_id] = session
        
        logger.info(f"Starting complete test cycle for session {session_id}")
        
        # Check if already running
        if session_id in self.running_tasks:
            logger.warning(f"Session {session_id} is already running")
            return session
        
        # Create task for this test cycle
        task = asyncio.create_task(self._run_test_cycle_internal(session_id, progress_callback, selected_test_ids))
        self.running_tasks[session_id] = task
        
        try:
            await task
        except asyncio.CancelledError:
            logger.info(f"Test cycle for session {session_id} was cancelled")
            session.status = "stopped"
            session.end_time = datetime.now()
            self.db.save_session(session)
            raise
        finally:
            if session_id in self.running_tasks:
                del self.running_tasks[session_id]
        
        return session
    
    async def _run_test_cycle_internal(
        self,
        session_id: str,
        progress_callback: Optional[Callable] = None,
        selected_test_ids: Optional[list[str]] = None
    ) -> TestSession:
        """Internal test cycle execution"""
        session = self.sessions[session_id]
        
        try:
            # Step 1: Hardware Detection (15 min simulated as 2 seconds)
            logger.info("Step 1/9: Hardware Detection")
            session.status = "detecting"
            session.progress_percent = 5.0
            self._save_and_notify(session, progress_callback)
            
            session.hardware_profile = self.hardware_detector.detect_all()
            await asyncio.sleep(2)  # Simulate detection time
            
            # Step 2: Test Selection (10 min simulated as 1 second)
            logger.info("Step 2/9: Test Selection")
            session.status = "planning"
            session.progress_percent = 10.0
            self._save_and_notify(session, progress_callback)
            
            # Generate test plan - but if selected_test_ids provided, load only those tests
            if selected_test_ids and len(selected_test_ids) > 0:
                # Load only the selected tests directly
                all_available_tests = self.test_loader.load_all()
                session.test_cases = [t for t in all_available_tests if t.id in selected_test_ids]
                logger.info(f"Running {len(session.test_cases)} selected tests (from {len(all_available_tests)} available)")
                logger.info(f"Selected test IDs: {selected_test_ids}")
                logger.info(f"Selected test names: {[t.name for t in session.test_cases]}")
                
                # Verify all requested tests were found
                found_ids = {t.id for t in session.test_cases}
                missing_ids = set(selected_test_ids) - found_ids
                if missing_ids:
                    logger.warning(f"Some requested test IDs were not found: {missing_ids}")
            else:
                # Generate full test plan based on hardware
                all_tests = self.test_generator.generate_test_plan(session.hardware_profile)
                session.test_cases = all_tests
                logger.info(f"Running all {len(session.test_cases)} tests (no selection provided)")
            
            await asyncio.sleep(1)
            
            # Step 3: Pre-flight Checks (5 min simulated as 1 second)
            logger.info("Step 3/9: Pre-flight Checks")
            session.progress_percent = 15.0
            self._save_and_notify(session, progress_callback)
            
            await self._preflight_checks(session)
            await asyncio.sleep(1)
            
            # Step 4: Test Execution (40 hours simulated as variable time)
            logger.info("Step 4/9: Test Execution")
            session.status = "testing"
            session.progress_percent = 20.0
            self._save_and_notify(session, progress_callback)
            
            # Define checkpoints (hours from start)
            checkpoint_hours = [6, 18, 36, 46]
            checkpoint_names = {
                6: "Initial Validation",
                18: "Mid-point Review",
                36: "Final Checks",
                46: "Pre-completion"
            }
            checkpoint_progress = {
                6: 30.0,   # 6h checkpoint at ~30% progress
                18: 50.0,  # 18h checkpoint at ~50% progress
                36: 80.0,  # 36h checkpoint at ~80% progress
                46: 95.0   # 46h checkpoint at ~95% progress
            }
            
            test_start_time = datetime.now()
            
            def test_progress(progress: float, result: TestResult):
                # Map test progress from 20% to 70%
                session.progress_percent = 20.0 + (progress * 0.5)
                
                # session.test_results is already managed by the executor via results_list parameter
                # We just update the session's overall progress here
                
                # Check for checkpoint evaluation
                elapsed_hours = (datetime.now() - test_start_time).total_seconds() / 3600
                for checkpoint_hour in checkpoint_hours:
                    # Check if we've passed this checkpoint and haven't evaluated it yet
                    checkpoint_id = f"{checkpoint_hour}h"
                    already_evaluated = any(cp.checkpoint_id == checkpoint_id for cp in session.checkpoints)
                    
                    if elapsed_hours >= checkpoint_hour and not already_evaluated:
                        logger.info(f"Evaluating checkpoint at {checkpoint_hour}h (elapsed: {elapsed_hours:.2f}h)")
                        checkpoint_result = self._evaluate_checkpoint(
                            session,
                            checkpoint_id,
                            checkpoint_names[checkpoint_hour],
                            elapsed_hours,
                            session.test_results
                        )
                        session.checkpoints.append(checkpoint_result)
                        session.progress_percent = checkpoint_progress[checkpoint_hour]
                        
                        # If checkpoint is NO-GO, we can optionally stop early
                        if checkpoint_result.decision == DecisionStatus.NO_GO:
                            logger.warning(f"Checkpoint {checkpoint_hour}h returned NO-GO - continuing but will flag in final decision")
                        
                        self._save_and_notify(session, progress_callback)
                
                self._save_and_notify(session, progress_callback)
            
            await self.test_executor.execute_test_plan(
                session.test_cases,
                progress_callback=test_progress,
                results_list=session.test_results
            )
            
            # Step 5: Data Aggregation (30 min simulated as 1 second)
            logger.info("Step 5/9: Data Aggregation")
            session.progress_percent = 75.0
            self._save_and_notify(session, progress_callback)
            await asyncio.sleep(1)
            
            # Step 6: AI/ML Analysis (3 hours simulated as 2 seconds)
            logger.info("Step 6/9: AI/ML Analysis")
            session.status = "analyzing"
            session.progress_percent = 80.0
            self._save_and_notify(session, progress_callback)
            
            session.ai_analysis, session.decision = self.decision_engine.analyze_and_decide(session.test_results)
            await asyncio.sleep(2)
            
            # Step 7: Decision Engine (15 min simulated as 1 second)
            logger.info("Step 7/9: Decision Engine")
            session.progress_percent = 85.0
            self._save_and_notify(session, progress_callback)
            await asyncio.sleep(1)
            
            # Step 8: Report Generation (1 hour simulated as 2 seconds)
            logger.info("Step 8/9: Report Generation")
            session.progress_percent = 90.0
            self._save_and_notify(session, progress_callback)
            
            # Generate and store reports
            json_report = self.json_reporter.generate(session)
            html_report = self.html_reporter.generate(session)
            session.reports.append(json_report)
            session.reports.append(html_report)
            
            try:
                pdf_report = self.pdf_reporter.generate(session)
                session.reports.append(pdf_report)
            except Exception as e:
                logger.warning(f"PDF generation failed: {e}")
            
            await asyncio.sleep(2)
            
            # Step 9: Distribution (30 min simulated as 1 second)
            logger.info("Step 9/9: Distribution")
            session.progress_percent = 95.0
            self._save_and_notify(session, progress_callback)
            await asyncio.sleep(1)
            
            # Complete
            session.status = "completed"
            session.end_time = datetime.now()
            session.total_duration = (session.end_time - session.start_time).total_seconds() / 3600
            session.progress_percent = 100.0
            self._save_and_notify(session, progress_callback)
            
            logger.info(f"Test cycle completed for session {session_id}")
            logger.info(f"Final decision: {session.decision.decision} with score {session.decision.score}")
            
        except asyncio.CancelledError:
            logger.info(f"Test cycle cancelled for session {session_id}")
            session.status = "stopped"
            session.end_time = datetime.now()
            self._save_and_notify(session, progress_callback)
            raise
        except Exception as e:
            logger.error(f"Test cycle failed: {e}", exc_info=True)
            session.status = "failed"
            session.end_time = datetime.now()
            self._save_and_notify(session, progress_callback)
            raise
        
        return session
    
    async def _preflight_checks(self, session: TestSession) -> bool:
        """Run pre-flight checks"""
        # Check if hardware was detected
        if not session.hardware_profile:
            raise RuntimeError("Hardware detection failed")
        
        # Check if tests were generated
        if not session.test_cases:
            raise RuntimeError("No test cases generated")
        
        logger.info("Pre-flight checks passed")
        return True
    
    def _save_and_notify(self, session: TestSession, callback: Optional[Callable]):
        """Save session to database and notify progress callback"""
        try:
            self.db.save_session(session)
        except Exception as e:
            logger.error(f"Error saving session to database: {e}")
        
        if callback:
            try:
                callback(session)
            except Exception as e:
                logger.error(f"Progress callback failed: {e}")
    
    def _notify_progress(self, callback: Optional[Callable], session: TestSession):
        """Notify progress callback"""
        if callback:
            try:
                callback(session)
            except Exception as e:
                logger.error(f"Progress callback failed: {e}")
    
    def _evaluate_checkpoint(
        self,
        session: TestSession,
        checkpoint_id: str,
        checkpoint_name: str,
        elapsed_hours: float,
        completed_tests: List[TestResult]
    ) -> CheckpointResult:
        """Evaluate checkpoint and make GO/NO-GO decision"""
        logger.info(f"Evaluating checkpoint {checkpoint_id}: {checkpoint_name}")
        
        # Count test results
        total_completed = len(completed_tests)
        passed = sum(1 for r in completed_tests if r.status.value == "passed")
        failed = sum(1 for r in completed_tests if r.status.value == "failed")
        
        # Calculate pass rate
        pass_rate = (passed / total_completed * 100) if total_completed > 0 else 0
        
        # Quick AI analysis on current results (simplified)
        from app.ai.decision_engine import DecisionEngine
        decision_engine = DecisionEngine()
        
        # Run quick analysis
        ai_analysis, decision = decision_engine.analyze_and_decide(completed_tests)
        
        # Determine checkpoint decision
        # More lenient at early checkpoints, stricter at later ones
        if checkpoint_id == "6h":
            # Early checkpoint - only fail on critical issues
            checkpoint_decision = DecisionStatus.NO_GO if (failed > 0 and pass_rate < 50) else DecisionStatus.GO
        elif checkpoint_id == "18h":
            # Mid-point - moderate threshold
            checkpoint_decision = DecisionStatus.NO_GO if (failed > 0 and pass_rate < 70) else DecisionStatus.GO
        elif checkpoint_id in ["36h", "46h"]:
            # Late checkpoints - use full decision engine result
            checkpoint_decision = decision.decision
        else:
            checkpoint_decision = DecisionStatus.GO
        
        # Build reasoning
        reasoning = [
            f"Checkpoint at {elapsed_hours:.1f} hours",
            f"Tests completed: {total_completed}/{len(session.test_cases)}",
            f"Pass rate: {pass_rate:.1f}% ({passed} passed, {failed} failed)"
        ]
        
        if decision.score < 70:
            reasoning.append(f"Score below threshold: {decision.score:.1f}/100")
        
        warnings = []
        if failed > 0:
            warnings.append(f"{failed} test(s) failed at checkpoint")
        if decision.confidence < 80:
            warnings.append(f"Low confidence: {decision.confidence:.1f}%")
        
        checkpoint_result = CheckpointResult(
            checkpoint_id=checkpoint_id,
            checkpoint_name=checkpoint_name,
            elapsed_hours=elapsed_hours,
            decision=checkpoint_decision,
            score=decision.score,
            confidence=decision.confidence,
            tests_completed=total_completed,
            tests_passed=passed,
            tests_failed=failed,
            reasoning=reasoning,
            warnings=warnings
        )
        
        logger.info(f"Checkpoint {checkpoint_id} decision: {checkpoint_decision} (Score: {decision.score:.1f})")
        return checkpoint_result
    
    def get_session(self, session_id: str) -> Optional[TestSession]:
        """Get session by ID (from memory or database)"""
        if session_id in self.sessions:
            return self.sessions[session_id]
        
        # Try loading from database
        session = self.db.load_session(session_id)
        if session:
            self.sessions[session_id] = session
        return session
    
    def list_sessions(self) -> list[TestSession]:
        """List all sessions (from memory and database)"""
        # Load from database if not in memory
        db_sessions = self.db.list_sessions(limit=1000)
        for session_data in db_sessions:
            if session_data['session_id'] not in self.sessions:
                session = self.db.load_session(session_data['session_id'])
                if session:
                    self.sessions[session.session_id] = session
        
        return list(self.sessions.values())
    
    async def stop_session(self, session_id: str) -> bool:
        """Stop a running test session"""
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return False
        
        # Check if session is already stopped or completed
        if session.status in ["stopped", "completed", "error"]:
            logger.info(f"Session {session_id} is already {session.status}")
            return True
        
        logger.info(f"Stopping session {session_id}")
        
        # Cancel the running task if it exists
        if session_id in self.running_tasks:
            task = self.running_tasks.get(session_id)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"Task for session {session_id} was cancelled")
                except Exception as e:
                    logger.warning(f"Error while cancelling task for session {session_id}: {e}")
            
            # Remove from running tasks
            del self.running_tasks[session_id]
        else:
            logger.info(f"Session {session_id} not in running_tasks, but marking as stopped")
        
        # Update session status regardless of whether it was in running_tasks
        session.status = "stopped"
        session.end_time = datetime.now()
        if session.start_time:
            session.total_duration = (session.end_time - session.start_time).total_seconds() / 3600
        self._save_and_notify(session, None)
        
        logger.info(f"Session {session_id} stopped")
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session from memory and database"""
        # Stop if running
        if session_id in self.running_tasks:
            logger.info(f"Stopping running session {session_id} before deletion")
            asyncio.create_task(self.stop_session(session_id))
        
        # Remove from memory
        if session_id in self.sessions:
            del self.sessions[session_id]
        
        # Delete from database
        deleted = self.db.delete_session(session_id)
        
        logger.info(f"Session {session_id} deleted")
        return deleted
    
    def get_session_status(self, session_id: str) -> dict:
        """Get session status summary"""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        return {
            "session_id": session.session_id,
            "ipc_id": session.ipc_id,
            "status": session.status,
            "progress_percent": session.progress_percent,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "total_tests": len(session.test_results),
            "tests_passed": sum(1 for r in session.test_results if r.status.value == "passed"),
            "decision": session.decision.decision.value if session.decision else "PENDING"
        }

