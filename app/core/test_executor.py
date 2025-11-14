"""
Test Execution Engine
Executes tests in parallel with progress tracking
Uses modular executors for each category
"""

import asyncio
import logging
from typing import List, Callable, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from app.models.schemas import TestCase, TestResult, TestStatus
from app.core.executors.executor_factory import ExecutorFactory

logger = logging.getLogger(__name__)


class TestExecutor:
    """Executes tests in parallel with monitoring using category-specific executors"""
    
    def __init__(self, max_parallel: int = 8):
        self.max_parallel = max_parallel
        self.executor = ThreadPoolExecutor(max_workers=max_parallel)
        self.results: List[TestResult] = []
        self.progress_callback: Callable = None
        
    async def execute_test_plan(
        self, 
        test_cases: List[TestCase],
        progress_callback: Callable = None,
        results_list: List[TestResult] = None
    ) -> List[TestResult]:
        """Execute all test cases with parallel execution"""
        logger.info(f"Starting test execution: {len(test_cases)} tests")
        self.progress_callback = progress_callback
        self.results = results_list if results_list is not None else []
        
        # Execute tests sequentially (can be parallelized later)
        for i, test_case in enumerate(test_cases):
            # Create initial result with RUNNING status
            from datetime import datetime
            initial_result = TestResult(
                test_id=test_case.id,
                test_name=test_case.name,
                status=TestStatus.RUNNING,
                start_time=datetime.now()
            )
            self.results.append(initial_result)
            
            # Report that test started
            progress = (i / len(test_cases)) * 100
            if self.progress_callback:
                self.progress_callback(progress, initial_result)
            
            logger.info(f"Starting test {i+1}/{len(test_cases)}: {test_case.name}")
            
            # Execute the test, passing the initial_result to update in real-time
            result = await self._execute_single_test(test_case, result_to_update=initial_result)
            
            # Update the result in the list
            self.results[i] = result
            
            # Report progress after completion
            progress = ((i + 1) / len(test_cases)) * 100
            if self.progress_callback:
                self.progress_callback(progress, result)
            
            logger.info(f"Progress: {progress:.1f}% - Test {test_case.name}: {result.status}")
        
        logger.info(f"Test execution completed: {len(self.results)} results")
        return self.results
    
    async def _execute_single_test(self, test_case: TestCase, result_to_update: TestResult = None) -> TestResult:
        """Execute a single test case using appropriate category executor"""
        logger.info(f"Executing test: {test_case.name} (Category: {test_case.category})")
        
        try:
            # Get appropriate executor for this test category
            executor = ExecutorFactory.get_executor(test_case)
            
            # Create progress callback that updates the result in real-time
            def test_progress_callback(progress_data: dict):
                """Update test result with progress information"""
                if result_to_update:
                    # Update elapsed time in the result
                    result_to_update.duration = progress_data.get("elapsed_seconds", 0)
                    # Store progress metrics
                    if "progress_percent" in progress_data:
                        if not result_to_update.metrics:
                            result_to_update.metrics = {}
                        result_to_update.metrics["_progress_percent"] = progress_data["progress_percent"]
                        result_to_update.metrics["_elapsed_seconds"] = progress_data.get("elapsed_seconds", 0)
                        result_to_update.metrics["_total_seconds"] = progress_data.get("total_seconds", 0)
                    # Call session-level progress callback if available
                    if self.progress_callback:
                        try:
                            self.progress_callback(progress_data.get("progress_percent", 0), result_to_update)
                        except Exception:
                            pass
            
            # Execute test using category-specific executor with progress callback
            result = await executor.execute(test_case, progress_callback=test_progress_callback)
            
            return result
        except asyncio.CancelledError:
            # Test execution was cancelled - create cancelled result
            logger.info(f"Test execution cancelled: {test_case.name}")
            from app.models.schemas import TestResult, TestStatus
            from datetime import datetime
            return TestResult(
                test_id=test_case.id,
                test_name=test_case.name,
                status=TestStatus.CANCELLED,
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration=0.0
            )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in self.results if r.status == TestStatus.ERROR)
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": (passed / total * 100) if total > 0 else 0
        }
