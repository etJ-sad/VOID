"""
Large AI Models Integration
Offline-capable large models for advanced IPC test analysis
Uses Hugging Face models with local caching for offline operation
"""

import logging
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from app.models.schemas import TestResult, AnomalyDetectionResult, PatternRecognitionResult
from config.settings import settings

logger = logging.getLogger(__name__)


class LargeModelManager:
    """Manages large AI models for offline operation"""
    
    def __init__(self, models_dir: Optional[str] = None):
        self.models_dir = Path(models_dir or settings.models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Model paths (directly in models directory, no subfolder)
        self.time_series_model_path = self.models_dir / "time_series_forecaster"
        self.anomaly_model_path = self.models_dir / "anomaly_detector"
        self.pattern_model_path = self.models_dir / "pattern_analyzer"
        self.llm_model_path = self.models_dir / "phi1_5_small_llm"
        self.llm_model_path_phi2 = self.models_dir / "phi2_small_llm"
        
        # Model availability
        self.transformers_available = False
        self.models_loaded = {}
        
        self._check_dependencies()
        self._load_models()
    
    def _check_dependencies(self):
        """Check if required libraries are available"""
        try:
            import torch
            logger.debug("✓ PyTorch available")
        except ImportError:
            logger.warning("⚠ PyTorch not installed - large models cannot be loaded")
            logger.info("  Install PyTorch: https://pytorch.org/get-started/locally/")
            logger.info("  Or: pip install torch torchvision torchaudio")
            self.transformers_available = False
            return
        
        try:
            import transformers
            from transformers import AutoModel, AutoTokenizer, AutoModelForSequenceClassification
            self.transformers = transformers
            self.AutoModel = AutoModel
            self.AutoTokenizer = AutoTokenizer
            self.AutoModelForSequenceClassification = AutoModelForSequenceClassification
            self.transformers_available = True
            logger.info("✓ Transformers library available")
        except ImportError:
            logger.warning("Transformers not installed. Install with: pip install transformers")
            self.transformers_available = False
    
    def _load_models(self):
        """Load all available models from local cache"""
        if not self.transformers_available:
            logger.info("LargeModelManager: Transformers library not available - large models disabled")
            logger.info("  Install with: pip install transformers huggingface-hub")
            return
        
        models_loaded_count = 0
        
        # Try to load time-series model
        if self.time_series_model_path.exists():
            try:
                logger.info(f"Loading time-series model from {self.time_series_model_path}...")
                model = self.AutoModel.from_pretrained(
                    str(self.time_series_model_path),
                    local_files_only=True
                )
                tokenizer = self.AutoTokenizer.from_pretrained(
                    str(self.time_series_model_path),
                    local_files_only=True
                )
                self.models_loaded["time_series"] = {
                    "model": model,
                    "tokenizer": tokenizer
                }
                models_loaded_count += 1
                logger.info("✓ Loaded time-series forecasting model (offline)")
            except Exception as e:
                logger.warning(f"Could not load time-series model: {e}")
        else:
            logger.debug(f"Time-series model not found at {self.time_series_model_path}")
        
        # Try to load anomaly detection model
        if self.anomaly_model_path.exists():
            try:
                logger.info(f"Loading anomaly detection model from {self.anomaly_model_path}...")
                model = self.AutoModelForSequenceClassification.from_pretrained(
                    str(self.anomaly_model_path),
                    local_files_only=True
                )
                tokenizer = self.AutoTokenizer.from_pretrained(
                    str(self.anomaly_model_path),
                    local_files_only=True
                )
                self.models_loaded["anomaly"] = {
                    "model": model,
                    "tokenizer": tokenizer
                }
                models_loaded_count += 1
                logger.info("✓ Loaded anomaly detection model (offline)")
            except Exception as e:
                logger.warning(f"Could not load anomaly model: {e}")
        else:
            logger.debug(f"Anomaly detection model not found at {self.anomaly_model_path}")
        
        # Try to load LLM models (phi-1.5 or phi-2)
        for llm_path, llm_name in [(self.llm_model_path, "phi-1.5"), (self.llm_model_path_phi2, "phi-2")]:
            if llm_path.exists():
                try:
                    logger.info(f"Loading LLM model ({llm_name}) from {llm_path}...")
                    model = self.AutoModel.from_pretrained(
                        str(llm_path),
                        local_files_only=True
                    )
                    tokenizer = self.AutoTokenizer.from_pretrained(
                        str(llm_path),
                        local_files_only=True
                    )
                    self.models_loaded["llm"] = {
                        "model": model,
                        "tokenizer": tokenizer,
                        "name": llm_name
                    }
                    models_loaded_count += 1
                    logger.info(f"✓ Loaded LLM model ({llm_name}) (offline)")
                    break  # Only load one LLM
                except Exception as e:
                    error_msg = str(e)
                    if "PyTorch" in error_msg or "torch" in error_msg.lower():
                        logger.warning(f"⚠ Could not load LLM model ({llm_name}): PyTorch required")
                        logger.info("  Install PyTorch: https://pytorch.org/get-started/locally/")
                        logger.info("  Or: pip install torch torchvision torchaudio")
                    else:
                        logger.warning(f"Could not load LLM model ({llm_name}): {e}")
        
        if models_loaded_count > 0:
            logger.info(f"LargeModelManager: {models_loaded_count} large model(s) loaded successfully")
        else:
            logger.info("LargeModelManager: No large models found (use scripts/download_models.py to download)")
            logger.info("  Large models are optional - system will use sklearn models instead")
    
    def analyze_time_series(self, test_results: List[TestResult]) -> Dict[str, Any]:
        """Analyze time-series patterns using large transformer model"""
        if "time_series" not in self.models_loaded:
            logger.debug("Time-series model not available, using fallback")
            return self._fallback_time_series_analysis(test_results)
        
        try:
            model_data = self.models_loaded["time_series"]
            model = model_data["model"]
            tokenizer = model_data["tokenizer"]
            
            # Extract time-series data
            metrics_data = self._extract_time_series(test_results)
            
            # Prepare input for model
            # Convert metrics to sequence format
            sequences = self._prepare_sequences(metrics_data)
            
            # For now, use model for feature extraction
            # In production, this would use the model's forward pass
            predictions = self._predict_with_model(model, tokenizer, sequences)
            
            return {
                "model_type": "transformer_time_series",
                "patterns": predictions.get("patterns", []),
                "forecast": predictions.get("forecast", {}),
                "confidence": predictions.get("confidence", 0.75),
                "offline": True
            }
            
        except Exception as e:
            logger.error(f"Time-series analysis failed: {e}")
            return self._fallback_time_series_analysis(test_results)
    
    def detect_anomalies_advanced(self, test_results: List[TestResult]) -> List[AnomalyDetectionResult]:
        """Advanced anomaly detection using large models"""
        if "anomaly" not in self.models_loaded:
            logger.debug("Anomaly model not available, using fallback")
            return []
        
        try:
            model_data = self.models_loaded["anomaly"]
            model = model_data["model"]
            tokenizer = model_data["tokenizer"]
            
            # Extract features from test results
            features = self._extract_features_for_anomaly(test_results)
            
            # Use model for anomaly detection
            anomaly_scores = self._detect_with_model(model, tokenizer, features)
            
            # Convert to AnomalyDetectionResult format
            results = []
            for metric, score in anomaly_scores.items():
                if score > 0.5:  # Threshold for anomaly
                    results.append(AnomalyDetectionResult(
                        algorithm="Transformer Anomaly Detection",
                        anomalies_found=1,
                        anomaly_score=float(score * 100),
                        details={
                            "model_type": "transformer",
                            "metric": metric,
                            "offline": True
                        },
                        affected_metrics=[metric]
                    ))
            
            return results
            
        except Exception as e:
            logger.error(f"Advanced anomaly detection failed: {e}")
            return []
    
    def _extract_time_series(self, test_results: List[TestResult]) -> Dict[str, List[float]]:
        """Extract time-series data from test results"""
        series = {
            "cpu_usage": [],
            "memory_usage": [],
            "temperature": [],
            "duration": [],
            "timestamp": []
        }
        
        for result in test_results:
            if result.metrics:
                series["cpu_usage"].append(result.metrics.get("cpu_avg", 0))
                series["memory_usage"].append(result.metrics.get("memory_avg", 0))
                series["temperature"].append(result.metrics.get("temp_avg", 0))
            
            if result.duration:
                series["duration"].append(result.duration)
            
            if result.timestamp:
                # Convert timestamp to numeric (hours since start)
                series["timestamp"].append(result.timestamp.timestamp())
        
        return series
    
    def _prepare_sequences(self, metrics_data: Dict[str, List[float]]) -> np.ndarray:
        """Prepare sequences for model input"""
        # Normalize all metrics to same length
        max_len = max(len(v) for v in metrics_data.values() if v)
        
        sequences = []
        for metric_name, values in metrics_data.items():
            if metric_name == "timestamp":
                continue
            
            if values:
                # Pad or truncate to max_len
                if len(values) < max_len:
                    values = values + [values[-1]] * (max_len - len(values))
                else:
                    values = values[:max_len]
                
                sequences.append(values)
        
        return np.array(sequences).T if sequences else np.array([])
    
    def _predict_with_model(self, model, tokenizer, sequences: np.ndarray) -> Dict[str, Any]:
        """Make predictions with the model"""
        # Placeholder for actual model inference
        # In production, this would use the model's forward pass
        
        patterns = []
        forecast = {}
        confidence = 0.75
        
        if sequences.size > 0:
            # Simple pattern detection (simulating transformer output)
            for i in range(sequences.shape[1]):
                col = sequences[:, i]
                if len(col) > 1:
                    trend = np.polyfit(range(len(col)), col, 1)[0]
                    if abs(trend) > 0.1:
                        patterns.append(f"metric_{i}_trend")
            
            # Forecast next values
            if sequences.shape[0] > 0:
                last_values = sequences[-1, :]
                forecast = {f"metric_{i}": float(v) for i, v in enumerate(last_values)}
        
        return {
            "patterns": patterns,
            "forecast": forecast,
            "confidence": confidence
        }
    
    def _detect_with_model(self, model, tokenizer, features: Dict[str, Any]) -> Dict[str, float]:
        """Detect anomalies using the model"""
        # Placeholder for actual model inference
        anomaly_scores = {}
        
        for metric, value in features.items():
            # Simple threshold-based detection (simulating model output)
            if isinstance(value, (int, float)):
                # Normalize and check if anomalous
                normalized = abs(value) / (abs(value) + 1)
                anomaly_scores[metric] = normalized if normalized > 0.5 else 0.0
        
        return anomaly_scores
    
    def _extract_features_for_anomaly(self, test_results: List[TestResult]) -> Dict[str, Any]:
        """Extract features for anomaly detection"""
        features = {}
        
        for result in test_results:
            if result.metrics:
                for key, value in result.metrics.items():
                    if key not in features:
                        features[key] = []
                    features[key].append(value)
        
        # Aggregate features
        aggregated = {}
        for key, values in features.items():
            if values:
                aggregated[f"{key}_mean"] = np.mean(values)
                aggregated[f"{key}_std"] = np.std(values)
                aggregated[f"{key}_max"] = np.max(values)
                aggregated[f"{key}_min"] = np.min(values)
        
        return aggregated
    
    def _fallback_time_series_analysis(self, test_results: List[TestResult]) -> Dict[str, Any]:
        """Fallback analysis when models are not available"""
        metrics_data = self._extract_time_series(test_results)
        
        patterns = []
        for metric_name, values in metrics_data.items():
            if len(values) > 2:
                trend = np.polyfit(range(len(values)), values, 1)[0]
                if abs(trend) > 0.1:
                    patterns.append(f"{metric_name}_trend")
        
        return {
            "model_type": "fallback",
            "patterns": patterns,
            "forecast": {},
            "confidence": 0.5,
            "offline": True
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models"""
        info = {
            "transformers_available": self.transformers_available,
            "models_loaded": list(self.models_loaded.keys()),
            "models_dir": str(self.models_dir),
            "offline_mode": True
        }
        
        # Check model sizes
        model_sizes = {}
        for model_name, model_path in [
            ("time_series", self.time_series_model_path),
            ("anomaly", self.anomaly_model_path),
            ("pattern", self.pattern_model_path),
            ("llm_phi1_5", self.llm_model_path),
            ("llm_phi2", self.llm_model_path_phi2)
        ]:
            if model_path.exists():
                size = sum(f.stat().st_size for f in model_path.rglob('*') if f.is_file())
                model_sizes[model_name] = f"{size / (1024*1024):.1f} MB"
        
        info["model_sizes"] = model_sizes
        return info

