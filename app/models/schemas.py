"""
Pydantic models for VOID Framework
Data schemas for hardware, tests, results, and reports
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field


class TestStatus(str, Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    CANCELLED = "cancelled"


class DecisionStatus(str, Enum):
    """Final GO/NO-GO decision"""
    GO = "GO"
    NO_GO = "NO_GO"
    PENDING = "PENDING"


class HardwareComponent(BaseModel):
    """Individual hardware component"""
    component_type: str = Field(..., description="Type of hardware (CPU, RAM, GPU, etc.)")
    name: str = Field(..., description="Component name/model")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    detected_at: datetime = Field(default_factory=datetime.now)


class HardwareProfile(BaseModel):
    """Complete hardware profile of IPC"""
    ipc_id: str = Field(..., description="Unique IPC identifier")
    ipc_model: str = Field(default="Unknown", description="IPC model name")
    cpu: Optional[HardwareComponent] = None
    ram: List[HardwareComponent] = Field(default_factory=list)
    gpu: List[HardwareComponent] = Field(default_factory=list)
    storage: List[HardwareComponent] = Field(default_factory=list)
    network: List[HardwareComponent] = Field(default_factory=list)
    sensors: List[HardwareComponent] = Field(default_factory=list)
    other: List[HardwareComponent] = Field(default_factory=list)
    detection_timestamp: datetime = Field(default_factory=datetime.now)


class TestCase(BaseModel):
    """Test case definition from YAML"""
    id: str = Field(..., description="Unique test identifier")
    name: str = Field(..., description="Human-readable test name")
    category: str = Field(..., description="Test category (CPU, RAM, GPU, etc.)")
    description: str = Field(..., description="Test description")
    duration_estimate: int = Field(..., description="Estimated duration in seconds")
    priority: int = Field(default=5, description="Priority 1-10, higher = more important")
    preconditions: List[str] = Field(default_factory=list)
    test_type: str = Field(..., description="Type of test (stress, pattern, benchmark, etc.)")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    baseline: Optional[Dict[str, Any]] = None
    thresholds: Dict[str, Any] = Field(default_factory=dict)


class TestResult(BaseModel):
    """Result of a single test execution"""
    test_id: str
    test_name: str
    status: TestStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None  # seconds
    metrics: Dict[str, Any] = Field(default_factory=dict)
    logs: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class AnomalyDetectionResult(BaseModel):
    """Result from anomaly detection algorithms"""
    algorithm: str = Field(..., description="Algorithm name")
    anomalies_found: int = Field(..., description="Number of anomalies detected")
    anomaly_score: float = Field(..., description="Score 0-100, higher = more anomalous")
    details: Dict[str, Any] = Field(default_factory=dict)
    affected_metrics: List[str] = Field(default_factory=list)


class PatternRecognitionResult(BaseModel):
    """Result from pattern recognition analysis"""
    patterns_detected: List[str] = Field(default_factory=list)
    correlations: Dict[str, float] = Field(default_factory=dict)
    trends: Dict[str, str] = Field(default_factory=dict)
    confidence: float = Field(..., description="Confidence level 0-100")


class AIAnalysisResult(BaseModel):
    """Complete AI/ML analysis result"""
    anomaly_detection: List[AnomalyDetectionResult] = Field(default_factory=list)
    pattern_recognition: PatternRecognitionResult
    overall_anomaly_score: float = Field(..., description="Combined anomaly score 0-100")
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    recommendations: List[str] = Field(default_factory=list)


class DecisionResult(BaseModel):
    """Final GO/NO-GO decision"""
    decision: DecisionStatus
    score: float = Field(..., description="Overall score 0-100")
    confidence: float = Field(..., description="Confidence in decision 0-100")
    reasoning: List[str] = Field(default_factory=list)
    critical_failures: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class Report(BaseModel):
    """Report metadata"""
    report_id: str
    session_id: str
    format: Literal["json", "html", "pdf"]
    generated_at: datetime = Field(default_factory=datetime.now)
    file_path: Optional[str] = None
    size_bytes: Optional[int] = None


class TestSession(BaseModel):
    """Complete test session"""
    session_id: str = Field(..., description="Unique session identifier")
    ipc_id: str
    hardware_profile: Optional[HardwareProfile] = None
    test_cases: List[TestCase] = Field(default_factory=list)
    test_results: List[TestResult] = Field(default_factory=list)
    ai_analysis: Optional[AIAnalysisResult] = None
    decision: Optional[DecisionResult] = None
    reports: List[Report] = Field(default_factory=list, description="Generated reports")
    status: Literal["initializing", "detecting", "planning", "testing", "analyzing", "completed", "failed"]
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_duration: Optional[float] = None  # hours
    progress_percent: float = Field(default=0.0, ge=0, le=100)


class SystemStatus(BaseModel):
    """Overall system status"""
    active_sessions: int
    total_sessions_completed: int
    system_health: Literal["healthy", "degraded", "critical"]
    last_update: datetime = Field(default_factory=datetime.now)

