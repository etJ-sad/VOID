"""
Pattern Recognition Module
Detects patterns, correlations, and trends in test data
"""

import numpy as np
import logging
from typing import List, Dict, Any
from scipy import stats
from app.models.schemas import TestResult, PatternRecognitionResult

logger = logging.getLogger(__name__)


class PatternRecognizer:
    """Recognizes patterns and trends in test data"""
    
    def analyze_patterns(self, test_results: List[TestResult]) -> PatternRecognitionResult:
        """Analyze patterns in test results"""
        logger.info(f"Analyzing patterns in {len(test_results)} test results")
        
        metrics_data = self._extract_time_series(test_results)
        
        patterns = []
        correlations = self._calculate_correlations(metrics_data)
        trends = self._detect_trends(metrics_data)
        confidence = self._calculate_confidence(correlations, trends)
        
        # Detect specific patterns
        if self._has_increasing_trend(trends):
            patterns.append("increasing_load")
        if self._has_decreasing_trend(trends):
            patterns.append("degrading_performance")
        if self._has_oscillation(metrics_data):
            patterns.append("oscillating_behavior")
        if self._has_stable_pattern(metrics_data):
            patterns.append("stable_operation")
        
        result = PatternRecognitionResult(
            patterns_detected=patterns,
            correlations=correlations,
            trends=trends,
            confidence=confidence
        )
        
        logger.info(f"Pattern analysis completed: {len(patterns)} patterns found")
        return result
    
    def _extract_time_series(self, test_results: List[TestResult]) -> Dict[str, List[float]]:
        """Extract time series data from test results"""
        series = {
            "cpu_usage": [],
            "memory_usage": [],
            "temperature": [],
            "duration": []
        }
        
        for result in test_results:
            if result.metrics:
                series["cpu_usage"].append(result.metrics.get("cpu_avg", 0))
                series["memory_usage"].append(result.metrics.get("memory_avg", 0))
                series["temperature"].append(result.metrics.get("temp_avg", 0))
            
            if result.duration:
                series["duration"].append(result.duration)
        
        return series
    
    def _calculate_correlations(self, metrics_data: Dict[str, List[float]]) -> Dict[str, float]:
        """Calculate correlations between metrics"""
        correlations = {}
        
        try:
            metrics_list = [(k, v) for k, v in metrics_data.items() if len(v) > 1]
            
            for i, (name1, values1) in enumerate(metrics_list):
                for name2, values2 in metrics_list[i+1:]:
                    if len(values1) == len(values2) and len(values1) > 1:
                        corr, _ = stats.pearsonr(values1, values2)
                        if not np.isnan(corr):
                            correlations[f"{name1}_vs_{name2}"] = round(float(corr), 3)
        except Exception as e:
            logger.error(f"Correlation calculation failed: {e}")
        
        return correlations
    
    def _detect_trends(self, metrics_data: Dict[str, List[float]]) -> Dict[str, str]:
        """Detect trends in metrics"""
        trends = {}
        
        for metric_name, values in metrics_data.items():
            if len(values) < 3:
                trends[metric_name] = "insufficient_data"
                continue
            
            # Linear regression to detect trend
            x = np.arange(len(values))
            y = np.array(values)
            
            try:
                slope, intercept, r_value, _, _ = stats.linregress(x, y)
                
                if abs(r_value) < 0.3:
                    trends[metric_name] = "stable"
                elif slope > 0:
                    trends[metric_name] = "increasing"
                else:
                    trends[metric_name] = "decreasing"
            except Exception as e:
                logger.debug(f"Trend detection failed for {metric_name}: {e}")
                trends[metric_name] = "unknown"
        
        return trends
    
    def _calculate_confidence(self, correlations: Dict[str, float], trends: Dict[str, str]) -> float:
        """Calculate overall confidence in pattern recognition"""
        confidence = 50.0  # Base confidence
        
        # More correlations found = higher confidence
        if correlations:
            strong_correlations = sum(1 for v in correlations.values() if abs(v) > 0.7)
            confidence += min(strong_correlations * 10, 30)
        
        # Clear trends = higher confidence
        clear_trends = sum(1 for v in trends.values() if v in ["increasing", "decreasing"])
        confidence += min(clear_trends * 5, 20)
        
        return min(confidence, 100.0)
    
    def _has_increasing_trend(self, trends: Dict[str, str]) -> bool:
        """Check if there are increasing trends"""
        return any(v == "increasing" for v in trends.values())
    
    def _has_decreasing_trend(self, trends: Dict[str, str]) -> bool:
        """Check if there are decreasing trends"""
        return any(v == "decreasing" for v in trends.values())
    
    def _has_oscillation(self, metrics_data: Dict[str, List[float]]) -> bool:
        """Detect oscillating patterns"""
        for values in metrics_data.values():
            if len(values) < 5:
                continue
            
            # Check for alternating increases/decreases
            diffs = np.diff(values)
            if len(diffs) < 2:
                continue
            
            sign_changes = np.sum(np.diff(np.sign(diffs)) != 0)
            if sign_changes > len(diffs) * 0.5:
                return True
        
        return False
    
    def _has_stable_pattern(self, metrics_data: Dict[str, List[float]]) -> bool:
        """Detect stable patterns (low variance)"""
        for values in metrics_data.values():
            if len(values) < 3:
                continue
            
            std = np.std(values)
            mean = np.mean(values)
            
            if mean > 0:
                cv = std / mean  # Coefficient of variation
                if cv < 0.1:  # Less than 10% variation
                    return True
        
        return False

