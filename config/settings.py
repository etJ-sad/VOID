"""
Configuration Settings
Centralized configuration for VOID Framework
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "VOID Framework"
    app_version: str = "0.0.1 night alpha concept"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Test Execution
    max_parallel_tests: int = 8
    max_test_duration_hours: int = 48
    
    # AI/ML
    anomaly_contamination: float = 0.1
    confidence_threshold: float = 95.0
    score_threshold: float = 70.0
    
    # Directories
    testcases_dir: str = "testcases"
    reports_dir: str = "reports"
    logs_dir: str = "logs"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()

