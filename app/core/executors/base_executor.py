"""
Base Test Executor
Common functionality for all test executors
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Callable, Optional
from abc import ABC, abstractmethod
from app.models.schemas import TestCase, TestResult, TestStatus

logger = logging.getLogger(__name__)


class BaseTestExecutor(ABC):
    """Base class for all test executors"""
    
    def __init__(self):
        self.category = self.__class__.__name__.replace('Executor', '').upper()
        self.test_progress_callback: Optional[Callable] = None
    
    async def execute(self, test_case: TestCase, progress_callback: Optional[Callable] = None) -> TestResult:
        """Execute a test case and return result"""
        logger.info(f"Executing {self.category} test: {test_case.name}")
        
        # Store progress callback for use during test execution
        self.test_progress_callback = progress_callback
        
        result = TestResult(
            test_id=test_case.id,
            test_name=test_case.name,
            status=TestStatus.RUNNING,
            start_time=datetime.now()
        )
        
        try:
            # Route to appropriate test type handler
            metrics = await self._route_test(test_case)
            result.metrics = metrics
            result.status = self._evaluate_result(test_case, metrics)
        except asyncio.CancelledError:
            # Test was cancelled - re-raise to allow proper cancellation handling
            logger.info(f"Test {test_case.name} was cancelled")
            result.status = TestStatus.CANCELLED
            raise
        except Exception as e:
            logger.error(f"Test {test_case.name} failed with error: {e}")
            result.status = TestStatus.ERROR
            result.errors.append(str(e))
        
        result.end_time = datetime.now()
        result.duration = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    async def _route_test(self, test_case: TestCase) -> Dict[str, Any]:
        """Route test to appropriate handler based on test type"""
        test_type = test_case.test_type.lower()
        
        if test_type == "stress":
            return await self.run_stress_test(test_case)
        elif test_type == "pattern":
            return await self.run_pattern_test(test_case)
        elif test_type == "benchmark":
            return await self.run_benchmark_test(test_case)
        elif test_type == "diagnostic":
            return await self.run_diagnostic_test(test_case)
        else:
            return await self.run_generic_test(test_case)
    
    # Abstract methods - must be implemented by subclasses
    @abstractmethod
    async def run_stress_test(self, test_case: TestCase) -> Dict[str, Any]:
        """Run stress test"""
        pass
    
    @abstractmethod
    async def run_pattern_test(self, test_case: TestCase) -> Dict[str, Any]:
        """Run pattern test"""
        pass
    
    @abstractmethod
    async def run_benchmark_test(self, test_case: TestCase) -> Dict[str, Any]:
        """Run benchmark test"""
        pass
    
    @abstractmethod
    async def run_diagnostic_test(self, test_case: TestCase) -> Dict[str, Any]:
        """Run diagnostic test"""
        pass
    
    async def run_generic_test(self, test_case: TestCase) -> Dict[str, Any]:
        """Run generic test (default implementation)"""
        # Use duration_estimate from YAML (in seconds), fallback to parameters.duration
        duration = test_case.duration_estimate if hasattr(test_case, 'duration_estimate') and test_case.duration_estimate else test_case.parameters.get("duration", 5)
        await self._safe_sleep(duration)
        return {"completed": True, "duration": duration}
    
    def _get_test_duration(self, test_case: TestCase) -> float:
        """Get test duration from duration_estimate (preferred) or parameters.duration"""
        # Prefer duration_estimate from YAML (actual test duration)
        if hasattr(test_case, 'duration_estimate') and test_case.duration_estimate:
            return float(test_case.duration_estimate)
        # Fallback to parameters.duration if duration_estimate not set
        return float(test_case.parameters.get("duration", 300))  # Default 5 minutes
    
    def _report_progress(self, elapsed_seconds: float, total_seconds: float, metrics: Dict[str, Any] = None):
        """Report test progress during execution"""
        if self.test_progress_callback:
            try:
                progress_data = {
                    "elapsed_seconds": elapsed_seconds,
                    "total_seconds": total_seconds,
                    "progress_percent": (elapsed_seconds / total_seconds * 100) if total_seconds > 0 else 0,
                    "metrics": metrics or {}
                }
                self.test_progress_callback(progress_data)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
    
    async def _safe_sleep(self, delay: float):
        """Sleep with cancellation support - raises CancelledError if cancelled"""
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            # Re-raise to allow proper cancellation handling upstream
            raise
    
    async def _sleep_with_progress(self, total_duration: float, progress_callback: Callable = None, interval: float = 1.0):
        """Sleep for duration but yield control periodically to allow progress updates"""
        elapsed = 0.0
        while elapsed < total_duration:
            sleep_time = min(interval, total_duration - elapsed)
            await self._safe_sleep(sleep_time)
            elapsed += sleep_time
            if progress_callback:
                try:
                    progress_callback(elapsed / total_duration * 100 if total_duration > 0 else 0)
                except Exception:
                    pass  # Ignore callback errors
    
    def _get_yield_interval(self, duration: float) -> float:
        """Get appropriate yield interval based on test duration to prevent Event Loop blocking"""
        # For very long tests (30+ minutes), yield more frequently
        if duration >= 1800:  # 30 minutes
            return 0.1  # Yield every 100ms
        elif duration >= 600:  # 10 minutes
            return 0.05  # Yield every 50ms
        elif duration >= 300:  # 5 minutes
            return 0.01  # Yield every 10ms
        else:
            return 0.01  # Default: yield every 10ms
    
    def _should_yield(self, iteration: int, duration: float) -> bool:
        """Determine if we should yield control to event loop based on iteration and duration"""
        # For very long tests, yield more frequently
        if duration >= 1800:  # 30 minutes
            return iteration % 10 == 0  # Every 10 iterations
        elif duration >= 600:  # 10 minutes
            return iteration % 50 == 0  # Every 50 iterations
        elif duration >= 300:  # 5 minutes
            return iteration % 100 == 0  # Every 100 iterations
        else:
            return iteration % 100 == 0  # Default: every 100 iterations
    
    def _evaluate_result(self, test_case: TestCase, metrics: Dict[str, Any]) -> TestStatus:
        """Evaluate if test passed based on metrics and thresholds"""
        if not metrics:
            return TestStatus.FAILED
        
        thresholds = test_case.thresholds
        if not thresholds:
            return TestStatus.PASSED
        
        # Category-specific threshold checking
        return self._check_thresholds(test_case, metrics, thresholds)
    
    def _check_thresholds(self, test_case: TestCase, metrics: Dict[str, Any], thresholds: Dict[str, Any]) -> TestStatus:
        """Check thresholds - override in subclasses for category-specific checks"""
        # Common threshold checks
        if "temp_max_celsius" in thresholds and "temp_max" in metrics:
            if metrics["temp_max"] > thresholds["temp_max_celsius"]:
                return TestStatus.FAILED
        
        return TestStatus.PASSED
    
    def _collect_common_metrics(self) -> Dict[str, Any]:
        """Collect common metrics (CPU, memory, temperature)"""
        import psutil
        
        metrics = {}
        
        # CPU
        metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        
        # Memory
        mem = psutil.virtual_memory()
        metrics["memory_percent"] = mem.percent
        
        # Temperature
        if hasattr(psutil, 'sensors_temperatures'):
            temps = psutil.sensors_temperatures()
            if temps:
                for sensor_name, entries in temps.items():
                    if entries:
                        metrics["temperature"] = entries[0].current
                        break
        
        return metrics

