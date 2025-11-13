"""
JSON Reporter
Generates machine-readable JSON reports
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from app.models.schemas import TestSession, Report

logger = logging.getLogger(__name__)


class JSONReporter:
    """Generates JSON reports"""
    
    def __init__(self, output_dir: str = "reports/json"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate(self, session: TestSession) -> Report:
        """Generate JSON report"""
        logger.info(f"Generating JSON report for session {session.session_id}")
        
        # Build report data
        report_data = self._build_report_data(session)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"void_report_{session.ipc_id}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        # Write JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        # Create report metadata - use relative path from reports directory
        relative_path = filepath.relative_to(Path("reports"))
        report = Report(
            report_id=f"json_{session.session_id}",
            session_id=session.session_id,
            format="json",
            file_path=str(relative_path),
            size_bytes=filepath.stat().st_size
        )
        
        logger.info(f"JSON report generated: {filepath}")
        return report
    
    def _build_report_data(self, session: TestSession) -> Dict[str, Any]:
        """Build complete report data structure"""
        data = {
            "metadata": {
                "version": "1.0.0",
                "framework": "VOID - Validation Of Industrial Devices",
                "generated_at": datetime.now().isoformat(),
                "session_id": session.session_id
            },
            "ipc_info": {
                "ipc_id": session.ipc_id,
                "ipc_model": session.hardware_profile.ipc_model if session.hardware_profile else "Unknown",
                "detection_timestamp": session.hardware_profile.detection_timestamp.isoformat() if session.hardware_profile else None
            },
            "hardware_profile": self._serialize_hardware(session.hardware_profile) if session.hardware_profile else None,
            "test_execution": {
                "status": session.status,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "total_duration_hours": session.total_duration,
                "progress_percent": session.progress_percent,
                "total_tests": len(session.test_results),
                "tests_passed": sum(1 for r in session.test_results if r.status.value == "passed"),
                "tests_failed": sum(1 for r in session.test_results if r.status.value == "failed"),
                "tests_error": sum(1 for r in session.test_results if r.status.value == "error")
            },
            "test_results": [self._serialize_test_result(r) for r in session.test_results],
            "ai_analysis": self._serialize_ai_analysis(session.ai_analysis) if session.ai_analysis else None,
            "decision": self._serialize_decision(session.decision) if session.decision else None,
            "summary": {
                "final_score": session.decision.score if session.decision else 0,
                "decision": session.decision.decision.value if session.decision else "PENDING",
                "confidence": session.decision.confidence if session.decision else 0,
                "risk_level": session.ai_analysis.risk_level if session.ai_analysis else "UNKNOWN"
            }
        }
        
        return data
    
    def _serialize_hardware(self, hardware) -> Dict[str, Any]:
        """Serialize hardware profile"""
        return {
            "cpu": hardware.cpu.dict() if hardware.cpu else None,
            "ram": [r.dict() for r in hardware.ram],
            "gpu": [g.dict() for g in hardware.gpu],
            "storage": [s.dict() for s in hardware.storage],
            "network": [n.dict() for n in hardware.network],
            "sensors": [s.dict() for s in hardware.sensors]
        }
    
    def _serialize_test_result(self, result) -> Dict[str, Any]:
        """Serialize test result"""
        return {
            "test_id": result.test_id,
            "test_name": result.test_name,
            "status": result.status.value,
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat() if result.end_time else None,
            "duration_seconds": result.duration,
            "metrics": result.metrics,
            "errors": result.errors
        }
    
    def _serialize_ai_analysis(self, analysis) -> Dict[str, Any]:
        """Serialize AI analysis"""
        return {
            "anomaly_detection": [a.dict() for a in analysis.anomaly_detection],
            "pattern_recognition": analysis.pattern_recognition.dict(),
            "overall_anomaly_score": analysis.overall_anomaly_score,
            "risk_level": analysis.risk_level,
            "recommendations": analysis.recommendations
        }
    
    def _serialize_decision(self, decision) -> Dict[str, Any]:
        """Serialize decision"""
        return {
            "decision": decision.decision.value,
            "score": decision.score,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
            "critical_failures": decision.critical_failures,
            "warnings": decision.warnings,
            "timestamp": decision.timestamp.isoformat()
        }

