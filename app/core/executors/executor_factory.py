"""
Executor Factory
Creates appropriate executor based on test category
"""

import logging
from typing import Dict
from app.models.schemas import TestCase
from app.core.executors.base_executor import BaseTestExecutor
from app.core.executors.cpu_executor import CPUExecutor
from app.core.executors.ram_executor import RAMExecutor
from app.core.executors.gpu_executor import GPUExecutor
from app.core.executors.storage_executor import StorageExecutor
from app.core.executors.network_executor import NetworkExecutor
from app.core.executors.system_executor import SystemExecutor

logger = logging.getLogger(__name__)


class ExecutorFactory:
    """Factory for creating test executors"""
    
    # Cache executors to avoid recreating them
    _executors: Dict[str, BaseTestExecutor] = {}
    
    @classmethod
    def get_executor(cls, test_case: TestCase) -> BaseTestExecutor:
        """Get executor for a test case based on category"""
        category = test_case.category.upper()
        
        # Return cached executor if available
        if category in cls._executors:
            return cls._executors[category]
        
        # Create new executor
        executor = cls._create_executor(category)
        cls._executors[category] = executor
        
        return executor
    
    @classmethod
    def _create_executor(cls, category: str) -> BaseTestExecutor:
        """Create executor instance for category"""
        category_map = {
            "CPU": CPUExecutor,
            "RAM": RAMExecutor,
            "GPU": GPUExecutor,
            "STORAGE": StorageExecutor,
            "NETWORK": NetworkExecutor,
            "SYSTEM": SystemExecutor,
        }
        
        executor_class = category_map.get(category)
        if executor_class:
            return executor_class()
        else:
            logger.warning(f"Unknown category {category}, using SystemExecutor")
            return SystemExecutor()
    
    @classmethod
    def clear_cache(cls):
        """Clear executor cache (useful for testing)"""
        cls._executors.clear()

