"""
Anomaly Detection Module
Multiple algorithms for detecting anomalies in test results
"""

import numpy as np
import logging
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from app.models.schemas import TestResult, AnomalyDetectionResult
from config.settings import settings

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detects anomalies using multiple algorithms"""
    
    def __init__(self, models_dir: Optional[str] = None):
        self.scaler = StandardScaler()
        self.models_dir = Path(models_dir or settings.models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Model file paths
        self.isolation_forest_path = self.models_dir / "isolation_forest.pkl"
        self.one_class_svm_path = self.models_dir / "one_class_svm.pkl"
        self.scaler_path = self.models_dir / "scaler.pkl"
        
        # Try to load existing models
        self.isolation_forest_model = None
        self.one_class_svm_model = None
        self._load_models()
        
    def detect_anomalies(self, test_results: List[TestResult]) -> List[AnomalyDetectionResult]:
        """Run all anomaly detection algorithms"""
        logger.info(f"Running anomaly detection on {len(test_results)} test results")
        
        results = []
        
        # Extract metrics from test results
        metrics_data = self._extract_metrics(test_results)
        
        if not metrics_data:
            logger.warning("No metrics data available for anomaly detection")
            return results
        
        # Run multiple algorithms (4 methods as per documentation)
        results.append(self._isolation_forest(metrics_data))  # Method 1: Pattern-based
        results.append(self._one_class_svm(metrics_data))     # Method 2: Baseline comparison
        results.append(self._statistical_zscore(metrics_data)) # Method 4: Simple math
        
        # Try Autoencoder if available (Method 3: Unusual combinations)
        try:
            from app.ai.advanced_pattern_recognition import AdvancedPatternRecognizer
            advanced = AdvancedPatternRecognizer()
            autoencoder_result = advanced.analyze_with_autoencoder(metrics_data)
            
            if autoencoder_result and autoencoder_result.get("anomalies"):
                # Convert autoencoder results to AnomalyDetectionResult format
                total_anomalies = len(autoencoder_result["anomalies"])
                avg_error = np.mean(list(autoencoder_result.get("reconstruction_errors", {}).values())) if autoencoder_result.get("reconstruction_errors") else 0.0
                
                results.append(AnomalyDetectionResult(
                    algorithm="Autoencoder Networks",
                    anomalies_found=total_anomalies,
                    anomaly_score=float(avg_error * 100) if avg_error > 0 else 0.0,
                    details={
                        "model_type": autoencoder_result.get("model_type", "simulated"),
                        "reconstruction_errors": autoencoder_result.get("reconstruction_errors", {})
                    },
                    affected_metrics=autoencoder_result.get("anomalies", [])
                ))
        except Exception as e:
            logger.debug(f"Autoencoder not available: {e}")
        
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
    
    def _load_models(self):
        """Load pre-trained models if available"""
        models_loaded = []
        
        try:
            if self.isolation_forest_path.exists():
                with open(self.isolation_forest_path, 'rb') as f:
                    self.isolation_forest_model = pickle.load(f)
                models_loaded.append("Isolation Forest")
                logger.info("✓ Loaded Isolation Forest model from disk")
            else:
                logger.debug("Isolation Forest model not found (will train on first use)")
        except Exception as e:
            logger.warning(f"Could not load Isolation Forest model: {e}")
        
        try:
            if self.one_class_svm_path.exists():
                with open(self.one_class_svm_path, 'rb') as f:
                    self.one_class_svm_model = pickle.load(f)
                models_loaded.append("One-Class SVM")
                logger.info("✓ Loaded One-Class SVM model from disk")
            else:
                logger.debug("One-Class SVM model not found (will train on first use)")
        except Exception as e:
            logger.warning(f"Could not load One-Class SVM model: {e}")
        
        try:
            if self.scaler_path.exists():
                with open(self.scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                models_loaded.append("StandardScaler")
                logger.info("✓ Loaded StandardScaler from disk")
            else:
                logger.debug("StandardScaler not found (will train on first use)")
        except Exception as e:
            logger.debug(f"Could not load StandardScaler: {e}")
        
        if models_loaded:
            logger.info(f"AnomalyDetector: {len(models_loaded)} model(s) loaded: {', '.join(models_loaded)}")
        else:
            logger.info("AnomalyDetector: No pre-trained models found (will train on first use)")
    
    def _save_models(self, isolation_forest_model, one_class_svm_model, scaler):
        """Save trained models to disk"""
        try:
            with open(self.isolation_forest_path, 'wb') as f:
                pickle.dump(isolation_forest_model, f)
            logger.info(f"Saved Isolation Forest model to {self.isolation_forest_path}")
        except Exception as e:
            logger.error(f"Could not save Isolation Forest model: {e}")
        
        try:
            with open(self.one_class_svm_path, 'wb') as f:
                pickle.dump(one_class_svm_model, f)
            logger.info(f"Saved One-Class SVM model to {self.one_class_svm_path}")
        except Exception as e:
            logger.error(f"Could not save One-Class SVM model: {e}")
        
        try:
            with open(self.scaler_path, 'wb') as f:
                pickle.dump(scaler, f)
            logger.info(f"Saved StandardScaler to {self.scaler_path}")
        except Exception as e:
            logger.error(f"Could not save StandardScaler: {e}")
    
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
            
            # Use existing model or train new one
            if self.isolation_forest_model is not None:
                logger.info("Using pre-trained Isolation Forest model")
                predictions = self.isolation_forest_model.predict(X)
                clf = self.isolation_forest_model
            else:
                # Fit new model
                clf = IsolationForest(contamination=0.1, random_state=42)
                predictions = clf.fit_predict(X)
                self.isolation_forest_model = clf
                # Save model
                try:
                    with open(self.isolation_forest_path, 'wb') as f:
                        pickle.dump(clf, f)
                    logger.info(f"Saved new Isolation Forest model to {self.isolation_forest_path}")
                except Exception as e:
                    logger.warning(f"Could not save Isolation Forest model: {e}")
            
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
            
            # Use existing model or train new one
            if self.one_class_svm_model is not None:
                logger.info("Using pre-trained One-Class SVM model")
                predictions = self.one_class_svm_model.predict(X)
                clf = self.one_class_svm_model
            else:
                # Fit new model
                clf = OneClassSVM(nu=nu, kernel="rbf", gamma='auto')
                predictions = clf.fit_predict(X)
                self.one_class_svm_model = clf
                # Save model
                try:
                    with open(self.one_class_svm_path, 'wb') as f:
                        pickle.dump(clf, f)
                    logger.info(f"Saved new One-Class SVM model to {self.one_class_svm_path}")
                except Exception as e:
                    logger.warning(f"Could not save One-Class SVM model: {e}")
            
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
        
        # Standardize - use existing scaler or fit new one
        if X.shape[0] > 0:
            if hasattr(self.scaler, 'mean_') and self.scaler.mean_ is not None:
                # Scaler already fitted, just transform
                X = self.scaler.transform(X)
            else:
                # Fit new scaler
                X = self.scaler.fit_transform(X)
                # Save scaler
                try:
                    with open(self.scaler_path, 'wb') as f:
                        pickle.dump(self.scaler, f)
                    logger.info(f"Saved new StandardScaler to {self.scaler_path}")
                except Exception as e:
                    logger.warning(f"Could not save StandardScaler: {e}")
        
        return X

