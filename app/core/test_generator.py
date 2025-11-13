"""
Test Generation Layer
Generates test plan based on detected hardware
"""

import logging
from typing import List, Dict
from app.models.schemas import HardwareProfile, TestCase
from app.core.test_loader import TestCaseLoader

logger = logging.getLogger(__name__)


class TestGenerator:
    """Generates optimal test plan based on hardware"""
    
    def __init__(self, test_loader: TestCaseLoader):
        self.test_loader = test_loader
        self.max_duration_hours = 48
        
    def generate_test_plan(self, hardware_profile: HardwareProfile) -> List[TestCase]:
        """Generate test plan based on detected hardware"""
        logger.info(f"Generating test plan for IPC: {hardware_profile.ipc_id}")
        
        selected_tests = []
        
        # Load all available tests
        all_tests = self.test_loader.load_all()
        
        # Select tests based on hardware presence
        hardware_map = {
            "CPU": hardware_profile.cpu is not None,
            "RAM": len(hardware_profile.ram) > 0,
            "GPU": len(hardware_profile.gpu) > 0,
            "Storage": len(hardware_profile.storage) > 0,
            "Network": len(hardware_profile.network) > 0,
        }
        
        for test in all_tests:
            category = test.category.upper()
            
            # Check if hardware is present for this test
            if category in hardware_map and hardware_map[category]:
                selected_tests.append(test)
                logger.info(f"Selected test: {test.name} (Category: {test.category})")
            elif category not in hardware_map:
                # Generic tests that don't require specific hardware
                selected_tests.append(test)
        
        # Sort by priority (higher priority first)
        selected_tests.sort(key=lambda t: t.priority, reverse=True)
        
        # Optimize for 48-hour window
        optimized_tests = self._optimize_for_duration(selected_tests)
        
        logger.info(f"Generated test plan with {len(optimized_tests)} tests")
        total_duration = sum(t.duration_estimate for t in optimized_tests) / 3600
        logger.info(f"Estimated total duration: {total_duration:.2f} hours")
        
        return optimized_tests
    
    def _optimize_for_duration(self, tests: List[TestCase]) -> List[TestCase]:
        """Optimize test selection to fit within 48-hour window"""
        max_seconds = self.max_duration_hours * 3600
        
        selected = []
        total_duration = 0
        
        for test in tests:
            if total_duration + test.duration_estimate <= max_seconds:
                selected.append(test)
                total_duration += test.duration_estimate
            else:
                logger.warning(f"Skipping test {test.name} - would exceed 48h window")
        
        return selected
    
    def estimate_completion_time(self, tests: List[TestCase]) -> float:
        """Estimate completion time in hours"""
        total_seconds = sum(test.duration_estimate for test in tests)
        return total_seconds / 3600

