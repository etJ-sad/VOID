"""
Decision Engine
Makes final GO/NO-GO decision based on all analysis
"""

import logging
from typing import List
from app.models.schemas import (
    TestResult, TestStatus, AIAnalysisResult, 
    DecisionResult, DecisionStatus, AnomalyDetectionResult,
    PatternRecognitionResult
)
from app.ai.anomaly_detection import AnomalyDetector
from app.ai.pattern_recognition import PatternRecognizer
from app.ai.large_models import LargeModelManager

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Makes final GO/NO-GO decision"""
    
    def __init__(self):
        self.anomaly_detector = AnomalyDetector()
        self.pattern_recognizer = PatternRecognizer()
        self.large_model_manager = LargeModelManager()
        self.confidence_threshold = 95.0
        self.score_threshold = 70.0
        
    def analyze_and_decide(self, test_results: List[TestResult]) -> tuple[AIAnalysisResult, DecisionResult]:
        """Run AI analysis and make decision"""
        logger.info("Starting AI analysis and decision making")
        
        # Run AI analysis
        ai_analysis = self._run_ai_analysis(test_results)
        
        # Make decision
        decision = self._make_decision(test_results, ai_analysis)
        
        logger.info(f"Decision: {decision.decision} (Score: {decision.score:.1f}, Confidence: {decision.confidence:.1f}%)")
        return ai_analysis, decision
    
    def _run_ai_analysis(self, test_results: List[TestResult]) -> AIAnalysisResult:
        """Run complete AI/ML analysis"""
        logger.info("Running AI/ML analysis")
        
        # Anomaly detection (traditional + large models)
        anomaly_results = self.anomaly_detector.detect_anomalies(test_results)
        
        # Advanced anomaly detection with large models
        try:
            large_anomaly_results = self.large_model_manager.detect_anomalies_advanced(test_results)
            if large_anomaly_results:
                anomaly_results.extend(large_anomaly_results)
                logger.info(f"Added {len(large_anomaly_results)} results from large models")
        except Exception as e:
            logger.debug(f"Large model anomaly detection not available: {e}")
        
        # Pattern recognition (traditional + large models)
        pattern_result = self.pattern_recognizer.analyze_patterns(test_results)
        
        # Advanced time-series analysis with large models
        try:
            large_ts_result = self.large_model_manager.analyze_time_series(test_results)
            if large_ts_result and large_ts_result.get("patterns"):
                # Merge patterns from large model
                pattern_result.patterns_detected.extend(large_ts_result["patterns"])
                # Increase confidence if large model was used
                if large_ts_result.get("confidence", 0) > pattern_result.confidence:
                    pattern_result.confidence = (pattern_result.confidence + large_ts_result["confidence"] * 100) / 2
                logger.info("Enhanced pattern recognition with large transformer model")
        except Exception as e:
            logger.debug(f"Large model time-series analysis not available: {e}")
        
        # Calculate overall anomaly score - weight algorithms differently
        if anomaly_results:
            # Weight algorithms: Isolation Forest and Z-Score are more reliable with small datasets
            weighted_scores = []
            for result in anomaly_results:
                if result.algorithm == "Isolation Forest":
                    weight = 0.4
                elif result.algorithm == "Statistical Z-Score":
                    weight = 0.4
                elif result.algorithm == "One-Class SVM":
                    weight = 0.2  # Less reliable with few samples
                else:
                    weight = 0.3
                
                # If algorithm has warning about insufficient data, reduce its weight
                if result.details and ("insufficient" in str(result.details).lower() or 
                                      "warning" in str(result.details).lower()):
                    weight *= 0.5
                
                weighted_scores.append(result.anomaly_score * weight)
            
            # Calculate weighted average - sum of weights should be 1.0 (0.4 + 0.4 + 0.2 = 1.0)
            # But we need to account for actual weights used (some may be reduced)
            total_weight = sum(0.4 if r.algorithm == "Isolation Forest" else 
                              0.4 if r.algorithm == "Statistical Z-Score" else 
                              0.2 if r.algorithm == "One-Class SVM" else 0.3
                              for r in anomaly_results)
            overall_anomaly_score = sum(weighted_scores) / total_weight if total_weight > 0 and weighted_scores else 0.0
        else:
            overall_anomaly_score = 0.0
        
        # Determine risk level
        risk_level = self._determine_risk_level(overall_anomaly_score, pattern_result)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(anomaly_results, pattern_result, test_results)
        
        return AIAnalysisResult(
            anomaly_detection=anomaly_results,
            pattern_recognition=pattern_result,
            overall_anomaly_score=overall_anomaly_score,
            risk_level=risk_level,
            recommendations=recommendations
        )
    
    def _make_decision(self, test_results: List[TestResult], ai_analysis: AIAnalysisResult) -> DecisionResult:
        """Make final GO/NO-GO decision"""
        logger.info("Making final decision")
        
        reasoning = []
        warnings = []
        critical_failures = []
        
        # Check for test failures
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r.status == TestStatus.PASSED)
        failed_tests = sum(1 for r in test_results if r.status == TestStatus.FAILED)
        error_tests = sum(1 for r in test_results if r.status == TestStatus.ERROR)
        
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Calculate base score - Test results are PRIMARY factor
        score = pass_rate
        
        # Check for critical failures FIRST (these override everything)
        for result in test_results:
            if result.status == TestStatus.FAILED and result.errors:
                critical_failures.append(f"{result.test_name}: {', '.join(result.errors[:2])}")
        
        # Adjust score based on AI analysis, but with reduced weight if tests passed
        # If all tests passed, AI anomalies are less critical
        if pass_rate == 100.0:
            # All tests passed - AI anomalies are secondary concerns
            anomaly_weight = 0.1  # Reduced weight
            if ai_analysis.overall_anomaly_score > 50:
                warnings.append(f"High anomaly score ({ai_analysis.overall_anomaly_score:.1f}) despite all tests passing - may indicate measurement variance")
            anomaly_penalty = ai_analysis.overall_anomaly_score * anomaly_weight
        else:
            # Some tests failed - AI analysis is more important
            anomaly_weight = 0.3
            anomaly_penalty = ai_analysis.overall_anomaly_score * anomaly_weight
        
        score -= anomaly_penalty
        
        # Risk level impact - but only if tests actually failed or anomaly score is very high
        if ai_analysis.risk_level == "CRITICAL":
            if failed_tests > 0 or ai_analysis.overall_anomaly_score > 70:
                score -= 20
                critical_failures.append("CRITICAL risk level detected by AI analysis")
            else:
                score -= 5  # Reduced penalty if tests passed
                warnings.append("CRITICAL risk level detected, but all tests passed")
        elif ai_analysis.risk_level == "HIGH":
            if failed_tests > 0 or ai_analysis.overall_anomaly_score > 50:
                score -= 10
                warnings.append("HIGH risk level detected")
            else:
                score -= 3  # Reduced penalty if tests passed
                warnings.append("HIGH risk level detected, but all tests passed")
        elif ai_analysis.risk_level == "MEDIUM":
            if failed_tests > 0:
                score -= 5
                warnings.append("MEDIUM risk level detected")
            else:
                score -= 1  # Minimal penalty if tests passed
        
        # Ensure score is in valid range
        score = max(0, min(100, score))
        
        # Build reasoning
        reasoning.append(f"Test pass rate: {pass_rate:.1f}% ({passed_tests}/{total_tests} tests passed)")
        
        # Only mention AI scores if they're significant or tests failed
        if failed_tests > 0 or ai_analysis.overall_anomaly_score > 30:
            reasoning.append(f"AI anomaly score: {ai_analysis.overall_anomaly_score:.1f}")
            reasoning.append(f"Risk level: {ai_analysis.risk_level}")
        elif ai_analysis.overall_anomaly_score > 0:
            reasoning.append(f"AI anomaly score: {ai_analysis.overall_anomaly_score:.1f} (low impact - all tests passed)")
        
        if failed_tests > 0:
            reasoning.append(f"Failed tests: {failed_tests}")
        if error_tests > 0:
            reasoning.append(f"Error tests: {error_tests}")
        
        # Pattern insights
        if ai_analysis.pattern_recognition.patterns_detected:
            patterns_str = ", ".join(ai_analysis.pattern_recognition.patterns_detected)
            reasoning.append(f"Patterns detected: {patterns_str}")
        
        # Calculate confidence
        confidence = self._calculate_confidence(test_results, ai_analysis)
        
        # Make final decision - prioritize test results
        if critical_failures:
            decision = DecisionStatus.NO_GO
            reasoning.append("Critical failures detected")
        elif failed_tests > 0:
            # If tests failed, NO-GO regardless of score
            decision = DecisionStatus.NO_GO
            reasoning.append(f"{failed_tests} test(s) failed")
        elif pass_rate == 100.0 and score >= 80:
            # All tests passed and score is good - GO (prioritize this over confidence)
            decision = DecisionStatus.GO
            reasoning.append("All tests passed and score meets threshold")
            if confidence < self.confidence_threshold and total_tests < 5:
                warnings.append(f"Low confidence ({confidence:.1f}%) due to limited test data ({total_tests} tests) - consider running more tests")
        elif score < self.score_threshold:
            decision = DecisionStatus.NO_GO
            reasoning.append(f"Score {score:.1f} below threshold {self.score_threshold}")
        elif score >= self.score_threshold and confidence >= self.confidence_threshold:
            decision = DecisionStatus.GO
            reasoning.append("All criteria met for GO decision")
        elif confidence < self.confidence_threshold and total_tests < 5 and pass_rate < 100.0:
            # Only use confidence threshold if we have very few tests AND some tests failed
            decision = DecisionStatus.NO_GO
            reasoning.append(f"Low confidence ({confidence:.1f}%) due to limited test data ({total_tests} tests)")
        else:
            # Default to GO if tests passed but score/confidence are borderline
            if pass_rate == 100.0:
                decision = DecisionStatus.GO
                reasoning.append("All tests passed - GO decision despite lower confidence")
            else:
                decision = DecisionStatus.NO_GO
                reasoning.append("Criteria not fully met")
        
        return DecisionResult(
            decision=decision,
            score=round(score, 2),
            confidence=round(confidence, 2),
            reasoning=reasoning,
            critical_failures=critical_failures,
            warnings=warnings
        )
    
    def _determine_risk_level(self, anomaly_score: float, pattern_result: PatternRecognitionResult) -> str:
        """Determine risk level based on analysis"""
        # Check patterns first - they can override anomaly score
        dangerous_patterns = {"degrading_performance", "oscillating_behavior"}
        detected = set(pattern_result.patterns_detected)
        
        # If dangerous patterns detected, elevate risk
        if detected & dangerous_patterns:
            if anomaly_score > 30:
                return "CRITICAL"
            elif anomaly_score > 15:
                return "HIGH"
            else:
                return "MEDIUM"
        
        # Otherwise use anomaly score
        if anomaly_score > 70:
            return "CRITICAL"
        elif anomaly_score > 50:
            return "HIGH"
        elif anomaly_score > 30:
            return "MEDIUM"
        elif anomaly_score > 15:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _calculate_confidence(self, test_results: List[TestResult], ai_analysis: AIAnalysisResult) -> float:
        """Calculate confidence in the decision"""
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r.status == TestStatus.PASSED)
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Start with base confidence based on test results
        if pass_rate == 100.0:
            confidence = 90.0  # High confidence if all tests passed
        elif pass_rate >= 80.0:
            confidence = 75.0
        elif pass_rate >= 50.0:
            confidence = 60.0
        else:
            confidence = 40.0
        
        # Adjust for number of tests (more tests = more confidence)
        if total_tests >= 10:
            confidence += 5  # Bonus for many tests
        elif total_tests >= 5:
            confidence += 0  # Normal confidence
        elif total_tests >= 3:
            confidence -= 10  # Slight reduction
        else:
            confidence -= 20  # Significant reduction for very few tests
        
        # Adjust for AI analysis - but less impact if tests passed
        if pass_rate == 100.0:
            # If all tests passed, AI anomalies are less concerning
            if ai_analysis.overall_anomaly_score > 50:
                confidence -= 15  # Still reduce if very high
            elif ai_analysis.overall_anomaly_score > 30:
                confidence -= 10
            else:
                confidence -= ai_analysis.overall_anomaly_score * 0.2  # Minimal impact
        else:
            # If tests failed, AI analysis is more important
            if ai_analysis.overall_anomaly_score > 20:
                confidence -= ai_analysis.overall_anomaly_score * 0.5
        
        # Use pattern recognition confidence as additional signal
        pattern_confidence = ai_analysis.pattern_recognition.confidence
        if total_tests >= 5:
            # More weight on patterns if we have enough data
            confidence = (confidence * 0.7 + pattern_confidence * 0.3)
        else:
            # Less weight on patterns if few tests
            confidence = (confidence * 0.9 + pattern_confidence * 0.1)
        
        return max(0, min(100, confidence))
    
    def _generate_recommendations(
        self, 
        anomaly_results: List[AnomalyDetectionResult],
        pattern_result: PatternRecognitionResult,
        test_results: List[TestResult]
    ) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # Check anomalies
        total_anomalies = sum(r.anomalies_found for r in anomaly_results)
        if total_anomalies > 10:
            recommendations.append(f"High number of anomalies detected ({total_anomalies}). Recommend detailed investigation.")
        
        # Check patterns
        if "degrading_performance" in pattern_result.patterns_detected:
            recommendations.append("Degrading performance pattern detected. Check for thermal issues or wear.")
        
        if "oscillating_behavior" in pattern_result.patterns_detected:
            recommendations.append("Oscillating behavior detected. May indicate control system instability.")
        
        # Check failed tests
        failed = [r for r in test_results if r.status == TestStatus.FAILED]
        if failed:
            categories = set(r.test_name.split()[0] for r in failed)
            recommendations.append(f"Failed tests in categories: {', '.join(categories)}")
        
        # Temperature warnings
        for result in test_results:
            if result.metrics and result.metrics.get("temp_max", 0) > 80:
                recommendations.append("High temperatures detected (>80°C). Check cooling system.")
                break
        
        if not recommendations:
            recommendations.append("No major issues detected. IPC appears to be functioning within normal parameters.")
        
        return recommendations

