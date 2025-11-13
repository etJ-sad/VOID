"""
Anomaly Detection Module
Multiple algorithms for detecting anomalies in test results
"""

import numpy as np
import logging
from typing import List, Dict, Any
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from app.models.schemas import TestResult, AnomalyDetectionResult

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detects anomalies using multiple algorithms"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        
    def detect_anomalies(self, test_results: List[TestResult]) -> List[AnomalyDetectionResult]:
        """Run all anomaly detection algorithms"""
        logger.info(f"Running anomaly detection on {len(test_results)} test results")
        
        results = []
        
        # Extract metrics from test results
        metrics_data = self._extract_metrics(test_results)
        
        if not metrics_data:
            logger.warning("No metrics data available for anomaly detection")
            return results
        
        # Run multiple algorithms
        results.append(self._isolation_forest(metrics_data))
        results.append(self._one_class_svm(metrics_data))
        results.append(self._statistical_zscore(metrics_data))
        
        logger.info(f"Anomaly detection completed: {len(results)} algorithms")
        return results
    
    def _extract_metrics(self, test_results: List[TestResult]) -> Dict[str, List[float]]:
        """Extract numerical metrics from test results"""
        metrics = {
            "cpu_avg": [],
            "cpu_max": [],
            "memory_avg": [],
            "temp_avg": [],
            "duration": []
        }
        
        for result in test_results:
            if result.metrics:
                metrics["cpu_avg"].append(result.metrics.get("cpu_avg", 0))
                metrics["cpu_max"].append(result.metrics.get("cpu_max", 0))
                metrics["memory_avg"].append(result.metrics.get("memory_avg", 0))
                metrics["temp_avg"].append(result.metrics.get("temp_avg", 0))
            
            if result.duration:
                metrics["duration"].append(result.duration)
        
        return metrics
    
    def _isolation_forest(self, metrics_data: Dict[str, List[float]]) -> AnomalyDetectionResult:
        """Isolation Forest anomaly detection"""
        logger.info("Running Isolation Forest")
        
        try:
            # Prepare data
            X = self._prepare_feature_matrix(metrics_data)
            
            if X.shape[0] < 2:
                return AnomalyDetectionResult(
                    algorithm="Isolation Forest",
                    anomalies_found=0,
                    anomaly_score=0.0,
                    details={"error": "Insufficient data"}
                )
            
            # Fit model
            clf = IsolationForest(contamination=0.1, random_state=42)
            predictions = clf.fit_predict(X)
            
            # Count anomalies (-1 = anomaly, 1 = normal)
            anomalies = np.sum(predictions == -1)
            anomaly_score = (anomalies / len(predictions)) * 100
            
            return AnomalyDetectionResult(
                algorithm="Isolation Forest",
                anomalies_found=int(anomalies),
                anomaly_score=float(anomaly_score),
                details={
                    "total_samples": len(predictions),
                    "contamination": 0.1
                },
                affected_metrics=list(metrics_data.keys())
            )
        except Exception as e:
            logger.error(f"Isolation Forest failed: {e}")
            return AnomalyDetectionResult(
                algorithm="Isolation Forest",
                anomalies_found=0,
                anomaly_score=0.0,
                details={"error": str(e)}
            )
    
    def _one_class_svm(self, metrics_data: Dict[str, List[float]]) -> AnomalyDetectionResult:
        """One-Class SVM anomaly detection"""
        logger.info("Running One-Class SVM")
        
        try:
            X = self._prepare_feature_matrix(metrics_data)
            
            # One-Class SVM needs at least 3 samples to be meaningful
            if X.shape[0] < 3:
                logger.warning(f"One-Class SVM: Insufficient data ({X.shape[0]} samples), returning low score")
                return AnomalyDetectionResult(
                    algorithm="One-Class SVM",
                    anomalies_found=0,
                    anomaly_score=0.0,
                    details={"warning": f"Insufficient data ({X.shape[0]} samples), minimum 3 required"}
                )
            
            # Adjust nu parameter based on sample size
            # With few samples, use higher nu to avoid over-detection
            nu = 0.2 if X.shape[0] < 5 else 0.1
            
            clf = OneClassSVM(nu=nu, kernel="rbf", gamma='auto')
            predictions = clf.fit_predict(X)
            
            anomalies = np.sum(predictions == -1)
            anomaly_score = (anomalies / len(predictions)) * 100
            
            # If we have very few samples and detect anomalies, reduce the score
            # because it's less reliable
            if X.shape[0] < 5 and anomalies > 0:
                anomaly_score = anomaly_score * 0.5  # Reduce by 50% for small sample sizes
                logger.warning(f"One-Class SVM: Reduced anomaly score due to small sample size")
            
            return AnomalyDetectionResult(
                algorithm="One-Class SVM",
                anomalies_found=int(anomalies),
                anomaly_score=float(anomaly_score),
                details={
                    "total_samples": len(predictions),
                    "nu": nu,
                    "kernel": "rbf",
                    "sample_size_adjusted": X.shape[0] < 5
                },
                affected_metrics=list(metrics_data.keys())
            )
        except Exception as e:
            logger.error(f"One-Class SVM failed: {e}")
            return AnomalyDetectionResult(
                algorithm="One-Class SVM",
                anomalies_found=0,
                anomaly_score=0.0,
                details={"error": str(e)}
            )
    
    def _statistical_zscore(self, metrics_data: Dict[str, List[float]]) -> AnomalyDetectionResult:
        """Statistical Z-Score anomaly detection"""
        logger.info("Running Statistical Z-Score")
        
        try:
            anomalies = 0
            affected = []
            threshold = 3.0  # Z-score threshold
            
            for metric_name, values in metrics_data.items():
                if not values or len(values) < 2:
                    continue
                
                mean = np.mean(values)
                std = np.std(values)
                
                if std == 0:
                    continue
                
                z_scores = np.abs((np.array(values) - mean) / std)
                metric_anomalies = np.sum(z_scores > threshold)
                
                if metric_anomalies > 0:
                    anomalies += metric_anomalies
                    affected.append(metric_name)
            
            total_samples = sum(len(v) for v in metrics_data.values())
            anomaly_score = (anomalies / total_samples * 100) if total_samples > 0 else 0
            
            return AnomalyDetectionResult(
                algorithm="Statistical Z-Score",
                anomalies_found=int(anomalies),
                anomaly_score=float(anomaly_score),
                details={
                    "threshold": threshold,
                    "total_samples": total_samples
                },
                affected_metrics=affected
            )
        except Exception as e:
            logger.error(f"Z-Score analysis failed: {e}")
            return AnomalyDetectionResult(
                algorithm="Statistical Z-Score",
                anomalies_found=0,
                anomaly_score=0.0,
                details={"error": str(e)}
            )
    
    def _prepare_feature_matrix(self, metrics_data: Dict[str, List[float]]) -> np.ndarray:
        """Prepare feature matrix for ML algorithms"""
        # Get maximum length
        max_len = max(len(v) for v in metrics_data.values() if v)
        
        # Pad all metrics to same length
        features = []
        for values in metrics_data.values():
            if values:
                padded = values + [0] * (max_len - len(values))
                features.append(padded)
        
        X = np.array(features).T
        
        # Standardize
        if X.shape[0] > 0:
            X = self.scaler.fit_transform(X)
        
        return X

