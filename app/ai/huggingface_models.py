"""
Hugging Face Model Integration
Optional integration with Hugging Face models for advanced analysis
Supports offline mode with locally cached models
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.models.schemas import TestResult
from config.settings import settings

logger = logging.getLogger(__name__)


class HuggingFaceModelManager:
    """Manages Hugging Face models for advanced AI analysis"""
    
    def __init__(self, models_dir: Optional[str] = None):
        self.models_dir = Path(models_dir or settings.models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.models_available = False
        self._check_availability()
    
    def _check_availability(self):
        """Check if Hugging Face libraries are available"""
        try:
            import transformers
            from transformers import AutoModel, AutoTokenizer
            self.transformers = transformers
            self.AutoModel = AutoModel
            self.AutoTokenizer = AutoTokenizer
            self.models_available = True
            logger.info("Hugging Face transformers library available")
        except ImportError:
            logger.info("Hugging Face transformers not installed. Install with: pip install transformers")
            self.models_available = False
    
    def load_time_series_model(self, model_name: str = "timeseries-forecasting/autoformer"):
        """Load a time-series forecasting model from Hugging Face"""
        if not self.models_available:
            logger.warning("Hugging Face models not available")
            return None
        
        try:
            model_path = self.models_dir / model_name.replace("/", "_")
            
            # Try to load from local cache first
            if model_path.exists():
                logger.info(f"Loading model from local cache: {model_path}")
                model = self.AutoModel.from_pretrained(str(model_path), local_files_only=True)
                tokenizer = self.AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
                return {"model": model, "tokenizer": tokenizer}
            
            # Otherwise, download (requires internet)
            logger.warning(f"Model {model_name} not found locally. Download requires internet connection.")
            logger.info("To use offline: Download model first with internet, then use offline mode")
            return None
            
        except Exception as e:
            logger.error(f"Failed to load Hugging Face model: {e}")
            return None
    
    def analyze_with_transformer(self, test_results: List[TestResult], model_name: Optional[str] = None) -> Dict[str, Any]:
        """Analyze test results using a transformer model"""
        if not self.models_available:
            return {
                "available": False,
                "message": "Hugging Face models not installed. Install with: pip install transformers"
            }
        
        # For now, return a placeholder
        # In production, this would use a fine-tuned model for IPC test analysis
        return {
            "available": True,
            "model_type": "transformer",
            "patterns": [],
            "confidence": 0.0,
            "message": "Transformer model analysis - to be implemented with fine-tuned model"
        }
    
    def download_model_offline(self, model_name: str, save_path: Optional[str] = None):
        """Download a model for offline use (requires internet initially)"""
        if not self.models_available:
            logger.error("Hugging Face transformers not installed")
            return False
        
        try:
            from huggingface_hub import snapshot_download
            
            target_path = Path(save_path) if save_path else self.models_dir / model_name.replace("/", "_")
            target_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Downloading model {model_name} to {target_path}...")
            snapshot_download(
                repo_id=model_name,
                local_dir=str(target_path),
                local_dir_use_symlinks=False
            )
            
            logger.info(f"Model downloaded successfully to {target_path}")
            return True
            
        except ImportError:
            logger.error("huggingface_hub not installed. Install with: pip install huggingface-hub")
            return False
        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            return False

