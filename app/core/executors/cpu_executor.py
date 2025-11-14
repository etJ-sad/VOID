"""
CPU Test Executor
Handles all CPU-related test execution
"""

import asyncio
import logging
import time
import psutil
import numpy as np
from typing import Dict, Any
from app.models.schemas import TestCase, TestStatus
from app.core.executors.base_executor import BaseTestExecutor

logger = logging.getLogger(__name__)


class CPUExecutor(BaseTestExecutor):
    """Executes CPU tests"""
    
    async def run_stress_test(self, test_case: TestCase) -> Dict[str, Any]:
        """Run CPU stress test"""
        logger.info(f"Running CPU stress test: {test_case.name}")
        
        metrics = {
            "cpu_samples": [],
            "memory_samples": [],
            "temperature_samples": []
        }
        
        duration = self._get_test_duration(test_case)
        algorithm = test_case.parameters.get("algorithm", "default")
        intensity = test_case.parameters.get("intensity", "medium")
        matrix_size = test_case.parameters.get("matrix_size", 1000)
        iterations_per_second = test_case.parameters.get("iterations_per_second", 2)
        collect_temperature = test_case.parameters.get("collect_temperature", True)
        collect_memory = test_case.parameters.get("collect_memory", True)
        
        # Detect test type from ID/name
        test_id_lower = test_case.id.lower()
        test_name_lower = test_case.name.lower()
        
        # Memory intensive stress test
        if "memory_intensive" in test_id_lower or "memory_intensive" in test_name_lower:
            memory_size_gb = test_case.parameters.get("memory_size_gb", 2)
            access_pattern = test_case.parameters.get("access_pattern", "random")
            cache_pressure = test_case.parameters.get("cache_pressure", "high")
            monitor_temperature = test_case.parameters.get("monitor_temperature", True)
            collect_memory_stats = test_case.parameters.get("collect_memory_stats", True)
            
            memory_size_bytes = int(memory_size_gb * 1024 * 1024 * 1024)
            iterations_per_second = 5
            interval = 1.0 / iterations_per_second
            iterations = int(duration / interval)
            
            for i in range(iterations):
                # Memory-intensive operations
                if access_pattern == "random":
                    data = np.random.rand(min(memory_size_bytes // 8, 10000000))
                    _ = data.sum()
                elif access_pattern == "sequential":
                    data = np.random.rand(min(memory_size_bytes // 8, 10000000))
                    _ = np.cumsum(data)[-1]
                else:
                    data = np.random.rand(min(memory_size_bytes // 8, 10000000))
                    _ = data.mean()
                
                # Collect metrics
                metrics["cpu_samples"].append(psutil.cpu_percent(interval=0.1))
                if collect_memory_stats:
                    mem = psutil.virtual_memory()
                    metrics["memory_samples"].append(mem.percent)
                if monitor_temperature and hasattr(psutil, 'sensors_temperatures'):
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for sensor_name, entries in temps.items():
                            if entries:
                                metrics["temperature_samples"].append(entries[0].current)
                                break
                
                await self._safe_sleep(interval)
            
            # Calculate cache miss rate (simulated)
            metrics["cache_miss_rate"] = 0.3 if cache_pressure == "high" else 0.15
            metrics["memory_access_pattern"] = access_pattern
            
        # Cache stress test
        elif "cache" in test_id_lower and "stress" in test_id_lower:
            cache_levels = test_case.parameters.get("cache_levels", ["L1", "L2", "L3"])
            access_patterns = test_case.parameters.get("access_patterns", ["sequential", "random", "strided"])
            data_size_mb = test_case.parameters.get("data_size_mb", 100)
            monitor_cache_misses = test_case.parameters.get("monitor_cache_misses", True)
            collect_temperature = test_case.parameters.get("collect_temperature", True)
            
            data_size_bytes = int(data_size_mb * 1024 * 1024)
            iterations_per_second = 3
            interval = 1.0 / iterations_per_second
            iterations = int(duration / interval)
            
            cache_results = {}
            for level in cache_levels:
                cache_results[level] = {"hits": 0, "misses": 0}
            
            for i in range(iterations):
                # Simulate cache access patterns
                data = np.random.rand(min(data_size_bytes // 8, 1000000))
                
                for pattern in access_patterns:
                    if pattern == "sequential":
                        _ = data.sum()
                    elif pattern == "random":
                        indices = np.random.randint(0, len(data), min(10000, len(data)))
                        _ = data[indices].sum()
                    elif pattern == "strided":
                        _ = data[::16].sum()
                
                # Simulate cache statistics
                for level in cache_levels:
                    cache_results[level]["hits"] += np.random.randint(80, 100)
                    cache_results[level]["misses"] += np.random.randint(0, 20)
                
                metrics["cpu_samples"].append(psutil.cpu_percent(interval=0.1))
                if collect_temperature and hasattr(psutil, 'sensors_temperatures'):
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for sensor_name, entries in temps.items():
                            if entries:
                                metrics["temperature_samples"].append(entries[0].current)
                                break
                
                await self._safe_sleep(interval)
            
            # Calculate cache miss rates
            for level in cache_levels:
                total = cache_results[level]["hits"] + cache_results[level]["misses"]
                cache_results[level]["miss_rate"] = cache_results[level]["misses"] / total if total > 0 else 0
                cache_results[level]["hit_rate"] = cache_results[level]["hits"] / total if total > 0 else 0
            
            metrics["cache_results"] = cache_results
            metrics["cache_miss_rate"] = sum(r["miss_rate"] for r in cache_results.values()) / len(cache_results)
        
        # Floating point stress test
        elif "floating_point" in test_id_lower and "stress" in test_id_lower:
            precision = test_case.parameters.get("precision", "double")
            operations_list = test_case.parameters.get("operations", ["add", "multiply", "divide", "sqrt", "sin", "cos"])
            use_simd = test_case.parameters.get("use_simd", True)
            monitor_fpu_usage = test_case.parameters.get("monitor_fpu_usage", True)
            iterations_per_second = test_case.parameters.get("iterations_per_second", 5)
            
            interval = 1.0 / iterations_per_second
            iterations = int(duration / interval)
            
            fpu_operations = 0
            
            for i in range(iterations):
                result = 0.0
                for op in operations_list:
                    if op == "add":
                        result += i * 3.14159
                    elif op == "multiply":
                        result *= 2.71828
                    elif op == "divide":
                        result /= 1.41421
                    elif op == "sqrt":
                        import math
                        result = math.sqrt(abs(result) + 1)
                    elif op == "sin":
                        import math
                        result = math.sin(result)
                    elif op == "cos":
                        import math
                        result = math.cos(result)
                    fpu_operations += 1
                
                metrics["cpu_samples"].append(psutil.cpu_percent(interval=0.1))
                if hasattr(psutil, 'sensors_temperatures'):
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for sensor_name, entries in temps.items():
                            if entries:
                                metrics["temperature_samples"].append(entries[0].current)
                                break
                
                await self._safe_sleep(interval)
            
            metrics["fpu_operations"] = fpu_operations
            metrics["fpu_utilization"] = 0.95 if use_simd else 0.75
            metrics["precision"] = precision
            metrics["operations_per_second"] = fpu_operations / duration if duration > 0 else 0
        
        # Default stress test logic
        else:
            interval = 1.0 / iterations_per_second
            iterations = int(duration / interval)
            
            for i in range(iterations):
                # CPU stress algorithms
                if algorithm == "matrix_multiplication":
                    _ = np.random.rand(matrix_size, matrix_size) @ np.random.rand(matrix_size, matrix_size)
                elif algorithm == "prime_calculation":
                    primes = []
                    limit = 10000 if intensity == "high" else 5000
                    for num in range(2, limit):
                        if all(num % i != 0 for i in range(2, int(num**0.5) + 1)):
                            primes.append(num)
                elif algorithm == "floating_point":
                    result = 0.0
                    ops = 100000 if intensity == "high" else 50000
                    for j in range(ops):
                        result += j * 3.14159
                elif algorithm == "cryptographic":
                    import hashlib
                    data = b"test_data" * 1000
                    for _ in range(100):
                        _ = hashlib.sha256(data).hexdigest()
                else:
                    _ = np.random.rand(matrix_size, matrix_size) @ np.random.rand(matrix_size, matrix_size)
            
            # Collect metrics
            metrics["cpu_samples"].append(psutil.cpu_percent(interval=0.1))
            
            if collect_memory:
                mem = psutil.virtual_memory()
                metrics["memory_samples"].append(mem.percent)
            
            if collect_temperature:
                if hasattr(psutil, 'sensors_temperatures'):
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for sensor_name, entries in temps.items():
                            if entries:
                                metrics["temperature_samples"].append(entries[0].current)
                                break
            
            await self._safe_sleep(interval)
        
        # Calculate statistics
        if metrics["cpu_samples"]:
            metrics["cpu_avg"] = sum(metrics["cpu_samples"]) / len(metrics["cpu_samples"])
            metrics["cpu_max"] = max(metrics["cpu_samples"])
        if metrics["memory_samples"]:
            metrics["memory_avg"] = sum(metrics["memory_samples"]) / len(metrics["memory_samples"])
        if metrics["temperature_samples"]:
            metrics["temp_avg"] = sum(metrics["temperature_samples"]) / len(metrics["temperature_samples"])
            metrics["temp_max"] = max(metrics["temperature_samples"])
            if test_case.parameters.get("monitor_throttling", False):
                metrics["throttling_events"] = sum(1 for t in metrics["temperature_samples"] if t > 90)
        
        return metrics
    
    async def run_pattern_test(self, test_case: TestCase) -> Dict[str, Any]:
        """Run CPU pattern test"""
        logger.info(f"Running CPU pattern test: {test_case.name}")
        
        duration = self._get_test_duration(test_case)
        pattern_type = test_case.parameters.get("pattern_type", "instruction_mix")
        instruction_types = test_case.parameters.get("instruction_types", ["arithmetic", "logical"])
        mix_ratio = test_case.parameters.get("mix_ratio", [0.5, 0.5])
        branch_count = test_case.parameters.get("branch_count", 1000000)
        
        metrics = {
            "operations_per_second": 0,
            "instructions_executed": 0,
            "pattern_detected": pattern_type
        }
        
        start_time = time.time()
        operations = 0
        
        # Detect test type from ID/name
        test_id_lower = test_case.id.lower()
        test_name_lower = test_case.name.lower()
        
        # Cache locality pattern test
        if "cache_locality" in test_id_lower or "cache_locality" in test_name_lower:
            locality_types = test_case.parameters.get("locality_types", ["spatial", "temporal", "mixed"])
            data_size_mb = test_case.parameters.get("data_size_mb", 50)
            stride_sizes = test_case.parameters.get("stride_sizes", [1, 4, 16, 64, 256])
            measure_cache_hits = test_case.parameters.get("measure_cache_hits", True)
            
            data_size_bytes = int(data_size_mb * 1024 * 1024)
            data = np.random.rand(min(data_size_bytes // 8, 10000000))
            cache_hits = 0
            cache_misses = 0
            
            for locality in locality_types:
                for stride in stride_sizes:
                    if locality == "spatial":
                        # Sequential access pattern
                        for i in range(0, len(data), stride):
                            _ = data[i]
                            cache_hits += 1
                    elif locality == "temporal":
                        # Repeated access to same locations
                        indices = list(range(0, min(1000, len(data)), stride))
                        for _ in range(100):
                            for idx in indices:
                                _ = data[idx]
                                cache_hits += 1
                    elif locality == "mixed":
                        # Mix of spatial and temporal
                        for i in range(0, len(data), stride * 2):
                            _ = data[i]
                            cache_hits += 1
                        cache_misses += len(data) // (stride * 2)
                    
                    await self._safe_sleep(0.01)
            
            total_accesses = cache_hits + cache_misses
            cache_hit_rate = cache_hits / total_accesses if total_accesses > 0 else 0
            
            metrics["cache_hit_rate"] = cache_hit_rate
            metrics["spatial_locality_hit_rate"] = 0.9  # Simulated
            metrics["temporal_locality_hit_rate"] = 0.85  # Simulated
            metrics["locality_types_tested"] = locality_types
            metrics["stride_sizes_tested"] = stride_sizes
        
        # Instruction pipeline pattern test
        elif "instruction_pipeline" in test_id_lower or "instruction_pipeline" in test_name_lower:
            instruction_mix = test_case.parameters.get("instruction_mix", ["arithmetic", "memory", "control", "floating_point"])
            dependency_levels = test_case.parameters.get("dependency_levels", ["none", "low", "medium", "high"])
            pipeline_depth = test_case.parameters.get("pipeline_depth", "auto")
            measure_stalls = test_case.parameters.get("measure_stalls", True)
            
            instructions_executed = 0
            pipeline_stalls = 0
            
            for dep_level in dependency_levels:
                stall_probability = {"none": 0.0, "low": 0.05, "medium": 0.15, "high": 0.3}.get(dep_level, 0.1)
                
                while time.time() - start_time < (duration / len(dependency_levels)):
                    # Execute instruction mix
                    for inst_type in instruction_mix:
                        if inst_type == "arithmetic":
                            result = 0
                            for i in range(100):
                                result += i * 2
                        elif inst_type == "memory":
                            data = [i for i in range(100)]
                            _ = sum(data)
                        elif inst_type == "control":
                            for i in range(10):
                                if i % 2 == 0:
                                    _ = i * 2
                        elif inst_type == "floating_point":
                            result = 0.0
                            for i in range(100):
                                result += i * 3.14159
                        
                        instructions_executed += 1
                        
                        # Simulate pipeline stalls based on dependency level
                        if np.random.random() < stall_probability:
                            pipeline_stalls += 1
                            await self._safe_sleep(0.001)
                    
                    await self._safe_sleep(0.001)
            
            elapsed = time.time() - start_time
            pipeline_efficiency = 1.0 - (pipeline_stalls / instructions_executed) if instructions_executed > 0 else 1.0
            instructions_per_cycle = instructions_executed / (elapsed * 1000) if elapsed > 0 else 0
            
            metrics["pipeline_efficiency"] = pipeline_efficiency
            metrics["instructions_per_cycle"] = instructions_per_cycle
            metrics["pipeline_stall_rate"] = pipeline_stalls / instructions_executed if instructions_executed > 0 else 0
            metrics["instructions_executed"] = instructions_executed
            metrics["pipeline_stalls"] = pipeline_stalls
        
        elif pattern_type == "instruction_mix" or "instruction_types" in test_case.parameters:
            # Instruction mix pattern
            iteration = 0
            while time.time() - start_time < duration:
                iteration += 1
                # Arithmetic operations
                if "arithmetic" in instruction_types:
                    result = 0
                    for i in range(1000):
                        result += i * 2 - i / 2
                    operations += 1
                
                # Logical operations
                if "logical" in instruction_types:
                    result = True
                    for i in range(1000):
                        result = result and (i > 0) or (i < 1000)
                    operations += 1
                
                # Memory operations
                if "memory" in instruction_types:
                    data = [i for i in range(1000)]
                    _ = sum(data)
                    operations += 1
                
                # Branch operations
                if "branch" in instruction_types:
                    for i in range(100):
                        if i % 2 == 0:
                            _ = i * 2
                        else:
                            _ = i * 3
                    operations += 1
                
                await self._safe_sleep(0.001)
            
            elapsed = time.time() - start_time
            metrics["operations_per_second"] = operations / elapsed if elapsed > 0 else 0
            metrics["instructions_executed"] = operations * 1000
        
        elif pattern_type == "branch_prediction" or "branch_count" in test_case.parameters:
            # Branch prediction pattern
            predictable_branches = 0
            unpredictable_branches = 0
            
            for i in range(branch_count):
                # Predictable pattern (alternating)
                if i % 2 == 0:
                    predictable_branches += 1
                else:
                    predictable_branches += 1
                
                # Unpredictable pattern (random-like)
                if (i * 7 + 13) % 3 == 0:
                    unpredictable_branches += 1
                else:
                    unpredictable_branches += 1
                
                if i % 10000 == 0:
                    await self._safe_sleep(0.001)
            
            elapsed = time.time() - start_time
            total_branches = predictable_branches + unpredictable_branches
            prediction_rate = predictable_branches / total_branches if total_branches > 0 else 0
            
            metrics["branch_prediction_rate"] = prediction_rate
            metrics["predictable_branches"] = predictable_branches
            metrics["unpredictable_branches"] = unpredictable_branches
            metrics["branches_per_second"] = total_branches / elapsed if elapsed > 0 else 0
        
        else:
            # Generic pattern test
            iteration = 0
            while time.time() - start_time < duration:
                iteration += 1
                _ = sum(range(10000))
                operations += 1
                await self._safe_sleep(0.001)
            
            elapsed = time.time() - start_time
            metrics["operations_per_second"] = operations / elapsed if elapsed > 0 else 0
        
        return metrics
    
    async def run_benchmark_test(self, test_case: TestCase) -> Dict[str, Any]:
        """Run CPU benchmark test"""
        logger.info(f"Running CPU benchmark test: {test_case.name}")
        
        duration = self._get_test_duration(test_case)
        algorithm = test_case.parameters.get("algorithm", "default")
        workload = test_case.parameters.get("workload", "default")
        algorithms = test_case.parameters.get("algorithms", [])  # Support plural form
        
        # Determine test type from ID or name if not in parameters
        test_id_lower = test_case.id.lower()
        test_name_lower = test_case.name.lower()
        
        # Auto-detect test type from ID/name or parameters
        if algorithm == "default" and not algorithms:
            if "cryptographic" in test_id_lower or "cryptographic" in test_name_lower:
                algorithm = "cryptographic"
            elif "crypto" in test_id_lower or "crypto" in test_name_lower:
                algorithm = "cryptographic"
            elif "integer" in test_id_lower or "integer_ops" in test_id_lower:
                algorithm = "integer_operations"
            elif "compression" in test_id_lower:
                algorithm = "compression"
            elif "sorting" in test_id_lower:
                algorithm = "sorting"
        
        # Use algorithms list if provided, otherwise use algorithm
        if algorithms and not algorithm == "cryptographic":
            algorithm = "cryptographic"  # If algorithms list is provided, it's cryptographic
        
        metrics = {"score": 0, "operations_per_second": 0}
        start_time = time.time()
        
        # Integer operations benchmark
        if algorithm == "integer_operations" or "integer_ops" in test_id_lower:
            operation_types = test_case.parameters.get("operation_types", ["add", "multiply", "divide", "modulo"])
            data_size = test_case.parameters.get("data_size", 1000000)
            iterations = test_case.parameters.get("iterations", 1000)
            
            operations = 0
            op_results = {}
            
            for op_type in operation_types:
                op_count = 0
                op_start = time.time()
                
                while time.time() - op_start < (duration / len(operation_types)):
                    if op_type == "add":
                        result = 0
                        for i in range(data_size // 1000):
                            result += i
                    elif op_type == "multiply":
                        result = 1
                        for i in range(1, data_size // 10000):
                            result *= i % 1000
                    elif op_type == "divide":
                        result = data_size
                        for i in range(1, data_size // 10000):
                            result /= max(i % 1000, 1)
                    elif op_type == "modulo":
                        result = 0
                        for i in range(data_size // 1000):
                            result += i % 1000
                    
                    op_count += 1
                    operations += 1
                    # Yield control to event loop every 10 operations (for long-running tests)
                    if op_count % 10 == 0:
                        await self._safe_sleep(0.01)
                
                op_elapsed = time.time() - op_start
                op_results[op_type] = {
                    "operations_per_second": op_count / op_elapsed if op_elapsed > 0 else 0
                }
            
            elapsed = time.time() - start_time
            metrics["operations_per_second"] = operations / elapsed if elapsed > 0 else 0
            metrics["operation_results"] = op_results
            metrics["score"] = int(metrics["operations_per_second"] / 100)
        
        # Compression benchmark
        elif algorithm == "compression" or "compression" in test_id_lower:
            compression_algorithms = test_case.parameters.get("algorithms", ["gzip", "lz4", "zlib"])
            data_size_mb = test_case.parameters.get("data_size_mb", 50)
            compression_level = test_case.parameters.get("compression_level", 6)
            
            import gzip
            import zlib
            
            test_data = b"x" * (data_size_mb * 1024 * 1024)
            algo_results = {}
            
            for algo_name in compression_algorithms:
                algo_ops = 0
                algo_start = time.time()
                
                while time.time() - algo_start < (duration / len(compression_algorithms)):
                    if algo_name.lower() == "gzip":
                        _ = gzip.compress(test_data[:1024*1024], compresslevel=compression_level)
                    elif algo_name.lower() == "zlib":
                        _ = zlib.compress(test_data[:1024*1024], level=compression_level)
                    elif algo_name.lower() == "lz4":
                        # Simulate LZ4 (using zlib as placeholder)
                        _ = zlib.compress(test_data[:1024*1024], level=1)
                    
                    algo_ops += 1
                    if algo_ops % 10 == 0:
                        await self._safe_sleep(0.01)
                
                algo_elapsed = time.time() - algo_start
                compressed_size = len(gzip.compress(test_data[:1024*1024], compresslevel=compression_level))
                compression_ratio = compressed_size / (1024 * 1024) if compressed_size > 0 else 0
                
                algo_results[algo_name.lower()] = {
                    "operations_per_second": algo_ops / algo_elapsed if algo_elapsed > 0 else 0,
                    "compression_speed_mbps": (algo_ops * data_size_mb) / algo_elapsed if algo_elapsed > 0 else 0,
                    "compression_ratio": compression_ratio
                }
            
            elapsed = time.time() - start_time
            total_speed = sum(r["compression_speed_mbps"] for r in algo_results.values())
            metrics["compression_speed_mbps"] = total_speed
            metrics["algorithm_results"] = algo_results
            metrics["gzip_speed_mbps"] = algo_results.get("gzip", {}).get("compression_speed_mbps", 0)
            metrics["lz4_speed_mbps"] = algo_results.get("lz4", {}).get("compression_speed_mbps", 0)
            metrics["score"] = int(total_speed / 10)
        
        # Sorting benchmark
        elif algorithm == "sorting" or "sorting" in test_id_lower:
            sort_algorithms = test_case.parameters.get("algorithms", ["quicksort", "mergesort", "heapsort", "radix"])
            array_sizes = test_case.parameters.get("array_sizes", [10000, 100000, 1000000])
            data_type = test_case.parameters.get("data_type", "integer")
            
            algo_results = {}
            
            for algo_name in sort_algorithms:
                algo_ops = 0
                algo_start = time.time()
                
                while time.time() - algo_start < (duration / len(sort_algorithms)):
                    for size in array_sizes:
                        if data_type == "integer":
                            arr = np.random.randint(0, size, size)
                        else:
                            arr = np.random.rand(size)
                        
                        if algo_name.lower() == "quicksort":
                            arr_sorted = np.sort(arr, kind='quicksort')
                        elif algo_name.lower() == "mergesort":
                            arr_sorted = np.sort(arr, kind='mergesort')
                        elif algo_name.lower() == "heapsort":
                            arr_sorted = np.sort(arr, kind='heapsort')
                        elif algo_name.lower() == "radix":
                            arr_sorted = np.sort(arr)  # Radix sort simulation
                        else:
                            arr_sorted = np.sort(arr)
                        
                        algo_ops += 1
                        if algo_ops % 10 == 0:
                            await self._safe_sleep(0.01)
                
                algo_elapsed = time.time() - algo_start
                algo_results[algo_name.lower()] = {
                    "operations_per_second": algo_ops / algo_elapsed if algo_elapsed > 0 else 0
                }
            
            elapsed = time.time() - start_time
            total_ops = sum(r["operations_per_second"] for r in algo_results.values())
            metrics["operations_per_second"] = total_ops
            metrics["algorithm_results"] = algo_results
            metrics["quicksort_ops_per_sec"] = algo_results.get("quicksort", {}).get("operations_per_second", 0)
            metrics["score"] = int(total_ops / 10)
        
        elif algorithm == "cryptographic" or algorithms:
            import hashlib
            import secrets
            
            # Get algorithms list or use default
            algo_list = algorithms if algorithms else ["SHA256"]  # Default to SHA256 if not specified
            key_size = test_case.parameters.get("key_size", 2048)
            data_size_mb = test_case.parameters.get("data_size_mb", 10)  # Smaller default for crypto
            
            operations = 0
            test_data = b"x" * (data_size_mb * 1024 * 1024)
            algo_results = {}
            
            # Test each algorithm
            for algo_name in algo_list:
                algo_ops = 0
                algo_start = time.time()
                
                while time.time() - algo_start < (duration / len(algo_list)):
                    if algo_name.upper() == "SHA256":
                        _ = hashlib.sha256(test_data).hexdigest()
                    elif algo_name.upper() == "AES":
                        # Simulate AES (using hashlib as placeholder)
                        _ = hashlib.sha256(test_data).hexdigest()  # Simplified
                    elif algo_name.upper() == "RSA":
                        # Simulate RSA (very simplified)
                        _ = hashlib.sha256(test_data).hexdigest()  # Simplified
                    else:
                        # Default to SHA256
                        _ = hashlib.sha256(test_data).hexdigest()
                    
                    algo_ops += 1
                    operations += 1
                    if algo_ops % 100 == 0:
                        await self._safe_sleep(0.001)
                
                algo_elapsed = time.time() - algo_start
                algo_results[algo_name.lower()] = {
                    "operations_per_second": algo_ops / algo_elapsed if algo_elapsed > 0 else 0,
                    "throughput_mbps": (algo_ops * data_size_mb) / algo_elapsed if algo_elapsed > 0 else 0
                }
            
            elapsed = time.time() - start_time
            metrics["operations_per_second"] = operations / elapsed if elapsed > 0 else 0
            metrics["algorithms_tested"] = algo_list
            metrics["algorithm_results"] = algo_results
            metrics["key_size"] = key_size
            
            # Calculate overall throughput
            total_throughput = sum(r["throughput_mbps"] for r in algo_results.values())
            metrics["throughput_mb_s"] = total_throughput
            metrics["aes_throughput_mbps"] = algo_results.get("aes", {}).get("throughput_mbps", 0)
            metrics["sha256_throughput_mbps"] = algo_results.get("sha256", {}).get("throughput_mbps", 0)
            
            metrics["score"] = int(metrics["operations_per_second"] / 100)
        
        elif workload == "matrix_multiplication":
            matrix_size = test_case.parameters.get("matrix_size", 1000)
            threads = test_case.parameters.get("threads", 1)
            operations = 0
            
            # Multi-threaded matrix multiplication simulation
            if threads > 1:
                # Simulate multi-threaded workload
                import concurrent.futures
                def matrix_multiply_task():
                    return np.random.rand(matrix_size, matrix_size) @ np.random.rand(matrix_size, matrix_size)
                
                iteration = 0
                while time.time() - start_time < duration:
                    iteration += 1
                    # Run multiple threads concurrently
                    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
                        futures = [executor.submit(matrix_multiply_task) for _ in range(threads)]
                        concurrent.futures.wait(futures)
                        operations += threads
                    if iteration % 10 == 0:
                        await self._safe_sleep(0.01)
            else:
                # Single-threaded
                iteration = 0
                while time.time() - start_time < duration:
                    iteration += 1
                    _ = np.random.rand(matrix_size, matrix_size) @ np.random.rand(matrix_size, matrix_size)
                    operations += 1
                    if operations % 10 == 0:
                        await self._safe_sleep(0.01)
            
            elapsed = time.time() - start_time
            metrics["operations_per_second"] = operations / elapsed
            metrics["threads_used"] = threads
            metrics["score"] = int(metrics["operations_per_second"] * 10)
        
        else:
            # Default CPU benchmark
            operations = 0
            iteration = 0
            while time.time() - start_time < duration:
                iteration += 1
                _ = sum(range(10000))
                operations += 1
                if operations % 1000 == 0:
                    await self._safe_sleep(0.001)
            
            elapsed = time.time() - start_time
            metrics["operations_per_second"] = operations / elapsed
            metrics["score"] = int(metrics["operations_per_second"] / 1000)
        
        return metrics
    
    async def run_diagnostic_test(self, test_case: TestCase) -> Dict[str, Any]:
        """Run CPU diagnostic test"""
        logger.info(f"Running CPU diagnostic test: {test_case.name}")
        
        duration = self._get_test_duration(test_case)
        test_name = test_case.name.lower()
        test_id_lower = test_case.id.lower()
        test_name_lower = test_case.name.lower()
        
        # Run for full duration (as defined in YAML duration_estimate)
        # For diagnostic tests, simulate work during the duration instead of just sleeping
        logger.info(f"Running diagnostic test for {duration} seconds (duration_estimate: {test_case.duration_estimate if hasattr(test_case, 'duration_estimate') else 'N/A'})")
        start_time = time.time()
        iteration = 0
        
        # Use adaptive yield interval based on duration
        yield_interval = self._get_yield_interval(duration)
        
        while time.time() - start_time < duration:
            iteration += 1
            elapsed = time.time() - start_time
            
            # Simulate diagnostic work (collecting metrics, checking hardware, etc.)
            # Small CPU work to simulate actual diagnostic operations
            _ = sum(range(100))
            
            # Report progress every 2 seconds
            if iteration % 20 == 0:
                self._report_progress(elapsed, duration, {"iteration": iteration})
            
            # Always yield control to Event Loop periodically (especially important for long tests)
            # For 5-minute tests, yield every 10 iterations (very frequently)
            if duration >= 300:
                if iteration % 10 == 0:
                    await self._safe_sleep(0.1)  # Yield every 10 iterations for long tests
            elif duration >= 60:
                if iteration % 50 == 0:
                    await self._safe_sleep(0.05)  # Yield every 50 iterations for medium tests
            else:
                if iteration % 100 == 0:
                    await self._safe_sleep(0.01)  # Yield every 100 iterations for short tests
            
            # Log progress for long tests
            if duration >= 300 and iteration % 1000 == 0:
                progress = (elapsed / duration) * 100
                logger.info(f"Diagnostic test progress: {progress:.1f}% ({elapsed:.1f}s / {duration}s)")
        
        metrics = {
            "completed": True,
            "score": 100
        }
        
        # Collect basic CPU info
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        cpu_freq = psutil.cpu_freq()
        
        metrics["cpu_count_logical"] = cpu_count_logical
        metrics["cpu_count_physical"] = cpu_count_physical
        metrics["cpu_freq_mhz"] = cpu_freq.current if cpu_freq else None
        metrics["cpu_freq_max_mhz"] = cpu_freq.max if cpu_freq else None
        
        if "cache" in test_name or "cache_test" in test_case.id:
            # Cache performance test
            import platform
            data_sizes = test_case.parameters.get("data_sizes", [1024, 4096, 16384, 65536])  # KB
            cache_results = {}
            
            for size_kb in data_sizes:
                size_bytes = size_kb * 1024
                data = np.random.rand(size_bytes // 8)
                
                # Measure access time
                start = time.time()
                _ = data.sum()
                access_time = (time.time() - start) * 1000  # ms
                
                cache_results[f"{size_kb}KB"] = {
                    "access_time_ms": access_time,
                    "throughput_mb_s": (size_kb / 1024) / (access_time / 1000) if access_time > 0 else 0
                }
            
            metrics["cache_results"] = cache_results
            metrics["cache_hit_rate"] = 0.85  # Simulated
            metrics["l1_cache_size_kb"] = 32  # Simulated
            metrics["l2_cache_size_kb"] = 256  # Simulated
        
        if "info" in test_name or "cpu_info" in test_case.id:
            # Detailed CPU info
            import platform
            metrics["cpu_model"] = platform.processor() or "Unknown"
            metrics["architecture"] = platform.machine()
            metrics["platform"] = platform.platform()
            
            if test_case.parameters.get("check_features", False):
                # Simulated CPU features
                metrics["features"] = {
                    "sse": True,
                    "sse2": True,
                    "avx": True,
                    "avx2": False  # Simulated
                }
        
        # Performance counters diagnostic
        if "performance_counters" in test_id_lower or "performance_counters" in test_name_lower:
            counters = test_case.parameters.get("counters", ["instructions", "cycles", "cache_misses", "branch_mispredictions", "tlb_misses"])
            sampling_rate = test_case.parameters.get("sampling_rate", 10)
            collect_all_metrics = test_case.parameters.get("collect_all_metrics", True)
            
            counter_data = {}
            samples = 0
            
            for counter in counters:
                counter_data[counter] = []
            
            # Simulate counter collection
            for i in range(int(duration * sampling_rate)):
                for counter in counters:
                    if counter == "instructions":
                        counter_data[counter].append(np.random.randint(1000000, 5000000))
                    elif counter == "cycles":
                        counter_data[counter].append(np.random.randint(800000, 4000000))
                    elif counter == "cache_misses":
                        counter_data[counter].append(np.random.randint(1000, 50000))
                    elif counter == "branch_mispredictions":
                        counter_data[counter].append(np.random.randint(100, 5000))
                    elif counter == "tlb_misses":
                        counter_data[counter].append(np.random.randint(10, 500))
                    else:
                        counter_data[counter].append(np.random.randint(1000, 10000))
                
                samples += 1
                if i % sampling_rate == 0:
                    await self._safe_sleep(1.0 / sampling_rate)
            
            # Calculate statistics
            for counter in counters:
                if counter_data[counter]:
                    metrics[f"{counter}_total"] = sum(counter_data[counter])
                    metrics[f"{counter}_avg"] = sum(counter_data[counter]) / len(counter_data[counter])
                    metrics[f"{counter}_max"] = max(counter_data[counter])
                    metrics[f"{counter}_min"] = min(counter_data[counter])
            
            # Calculate IPC (Instructions Per Cycle)
            if "instructions" in counters and "cycles" in counters:
                total_instructions = sum(counter_data["instructions"])
                total_cycles = sum(counter_data["cycles"])
                metrics["instructions_per_cycle"] = total_instructions / total_cycles if total_cycles > 0 else 0
            
            metrics["counters_collected"] = len(counters)
            metrics["samples"] = samples
        
        # Microarchitecture diagnostic
        if "microarchitecture" in test_id_lower or "microarchitecture" in test_name_lower:
            analyze_pipeline = test_case.parameters.get("analyze_pipeline", True)
            analyze_cache = test_case.parameters.get("analyze_cache", True)
            analyze_execution_units = test_case.parameters.get("analyze_execution_units", True)
            detect_features = test_case.parameters.get("detect_features", True)
            collect_topology = test_case.parameters.get("collect_topology", True)
            
            import platform
            
            if analyze_pipeline:
                metrics["pipeline"] = {
                    "depth": 14,  # Simulated
                    "stages": ["fetch", "decode", "rename", "dispatch", "execute", "retire"],
                    "width": 4,  # Instructions per cycle
                    "out_of_order": True
                }
            
            if analyze_cache:
                metrics["cache"] = {
                    "l1_data_size_kb": 32,
                    "l1_instruction_size_kb": 32,
                    "l2_size_kb": 256,
                    "l3_size_mb": 8,
                    "cache_line_size_bytes": 64,
                    "associativity": {"l1": 8, "l2": 8, "l3": 16}
                }
            
            if analyze_execution_units:
                metrics["execution_units"] = {
                    "integer_alu": 4,
                    "floating_point_alu": 2,
                    "load_store_units": 2,
                    "branch_units": 1,
                    "simd_units": 2
                }
            
            if detect_features:
                metrics["features"] = {
                    "sse": True,
                    "sse2": True,
                    "sse3": True,
                    "ssse3": True,
                    "sse4_1": True,
                    "sse4_2": True,
                    "avx": True,
                    "avx2": False,
                    "avx512": False,
                    "fma": True
                }
            
            if collect_topology:
                metrics["topology"] = {
                    "cores": psutil.cpu_count(logical=False),
                    "threads": psutil.cpu_count(logical=True),
                    "sockets": 1,
                    "numa_nodes": 1
                }
            
            metrics["cpu_model"] = platform.processor() or "Unknown"
            metrics["architecture"] = platform.machine()
            metrics["cache_levels"] = 3
            metrics["execution_units_count"] = 11  # Sum of execution units
        
        return metrics
    
    def _check_thresholds(self, test_case: TestCase, metrics: Dict[str, Any], thresholds: Dict[str, Any]) -> TestStatus:
        """Check CPU-specific thresholds"""
        if "cpu_max_percent" in thresholds and "cpu_max" in metrics:
            if metrics["cpu_max"] > thresholds["cpu_max_percent"]:
                return TestStatus.FAILED
        
        if "temp_max_celsius" in thresholds and "temp_max" in metrics:
            if metrics["temp_max"] > thresholds["temp_max_celsius"]:
                return TestStatus.FAILED
        
        return TestStatus.PASSED

