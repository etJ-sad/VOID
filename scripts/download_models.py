"""
Download Large AI Models for Offline Use
Downloads Hugging Face models and saves them locally for offline operation
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

import logging
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_model(model_name: str, local_path: Path, model_type: str = "AutoModel"):
    """Download a Hugging Face model for offline use"""
    try:
        from huggingface_hub import snapshot_download
        import transformers
        
        # Check if model already exists
        if local_path.exists() and any(local_path.iterdir()):
            logger.warning(f"Model directory already exists: {local_path}")
            overwrite = input("Overwrite? (y/N): ").strip().lower()
            if overwrite != 'y':
                logger.info("Skipping download.")
                return True
        
        logger.info(f"Downloading {model_name} to {local_path}...")
        logger.info("This may take several minutes depending on model size and internet speed...")
        
        # Download model
        snapshot_download(
            repo_id=model_name,
            local_dir=str(local_path),
            ignore_patterns=["*.md", "*.txt", "*.ipynb", "*.git*"]  # Skip documentation files
        )
        
        logger.info(f"✓ Successfully downloaded {model_name}")
        logger.info(f"  Location: {local_path}")
        
        # Calculate size
        size = sum(f.stat().st_size for f in local_path.rglob('*') if f.is_file())
        logger.info(f"  Size: {size / (1024*1024):.1f} MB")
        
        # Verify model files exist
        required_files = ["config.json", "pytorch_model.bin"]  # Common model files
        has_model_files = any((local_path / f).exists() for f in ["pytorch_model.bin", "model.safetensors", "model.bin"])
        if not has_model_files:
            logger.warning("  ⚠ Warning: Model files may be incomplete. Check the directory.")
        else:
            logger.info("  ✓ Model files verified")
        
        return True
        
    except ImportError:
        logger.error("huggingface_hub not installed!")
        logger.info("Install with: pip install huggingface-hub transformers")
        return False
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to download model: {e}")
        
        if "401" in error_msg or "Repository Not Found" in error_msg:
            logger.error("  ⚠ This model doesn't exist or requires authentication")
            logger.info("  Try a different model name or check: https://huggingface.co/models")
        elif "403" in error_msg:
            logger.error("  ⚠ Access denied - this model may be private or gated")
            logger.info("  You may need to accept the model's license first on huggingface.co")
        else:
            logger.info("  Make sure the model name is correct and you have internet access")
            logger.info("  Check the model exists at: https://huggingface.co/models")
        
        return False


def main():
    """Download recommended models for VOID Framework"""
    models_dir = Path(settings.models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("VOID Framework - Model Download Script")
    logger.info("=" * 60)
    logger.info("")
    logger.info("This script downloads large AI models for offline use.")
    logger.info("Models will be saved to: " + str(models_dir))
    logger.info("")
    
    # Recommended models (smaller, faster, good for IPC testing)
    # IMPORTANT: Time-series models are OPTIONAL - VOID works fine without them using sklearn
    # Most time-series models on Hugging Face are large or require training
    # The system will use fallback methods if models aren't available
    
    recommended_models = [
        {
            "name": "microsoft/phi-1_5",
            "path": models_dir / "phi1_5_small_llm",
            "description": "Small Language Model (1.3B) - for error analysis and reasoning",
            "size": "~2.5 GB",
            "required": False,
            "note": "Optional - VOID works fine without large models"
        }
    ]
    
    # Alternative models
    alternative_models = [
        {
            "name": "microsoft/phi-2",
            "path": models_dir / "phi2_small_llm",
            "description": "Small Language Model (2.7B) - larger alternative",
            "size": "~5 GB",
            "required": False
        }
    ]
    
    # Note about time-series models
    logger.info("⚠ IMPORTANT: Time-series models are OPTIONAL!")
    logger.info("   VOID uses sklearn models (Isolation Forest, One-Class SVM) by default")
    logger.info("   These work well for IPC testing and don't require downloads.")
    logger.info("   Large models are only needed for advanced analysis.")
    logger.info("")
    
    # Note: Anomaly detection models are typically not available as pre-trained Hugging Face models
    # The system uses sklearn models (Isolation Forest, One-Class SVM) for anomaly detection
    # If you want to use a transformer for anomaly detection, you would need to fine-tune one
    
    logger.info("Recommended models:")
    for i, model in enumerate(recommended_models, 1):
        logger.info(f"  {i}. {model['name']}")
        logger.info(f"     {model['description']}")
        logger.info(f"     Size: {model['size']}")
        if 'note' in model:
            logger.info(f"     Note: {model['note']}")
        logger.info("")
    
    logger.info("Alternative models (if recommended ones don't work):")
    for model in alternative_models:
        logger.info(f"  - {model['name']} ({model['size']})")
    logger.info("")
    
    # Ask user which models to download
    print("\nWhich models would you like to download?")
    print("  [1] Small LLM (phi-1.5) only (~2.5 GB, optional)")
    print("  [2] Large LLM (phi-2) only (~5 GB, optional)")
    print("  [3] Custom model (enter any Hugging Face model name)")
    print("  [0] Cancel / Skip (VOID works fine without large models)")
    print("\n⚠ Note: All models are OPTIONAL!")
    print("   VOID uses sklearn models by default (no download needed)")
    print("   Large models only provide advanced analysis features")
    
    choice = input("\nEnter choice (0-3): ").strip()
    
    models_to_download = []
    
    if choice == "1":
        models_to_download = [recommended_models[0]]  # phi-1.5 only
    elif choice == "2":
        models_to_download = [alternative_models[0]]  # phi-2 only
    elif choice == "3":
        model_name = input("Enter Hugging Face model name (e.g., facebook/time-series-forecasting): ").strip()
        if model_name:
            local_name = model_name.replace("/", "_").replace("-", "_")
            # Ask for target path
            target_path_name = input(f"Enter local folder name (default: {local_name}): ").strip()
            if not target_path_name:
                target_path_name = local_name
            models_to_download = [{
                "name": model_name,
                "path": models_dir / target_path_name,
                "description": "Custom model",
                "size": "Unknown"
            }]
    elif choice == "0":
        logger.info("Cancelled.")
        return
    else:
        logger.error("Invalid choice.")
        return
    
    # Download models
    logger.info("")
    logger.info("Starting downloads...")
    logger.info("=" * 60)
    
    success_count = 0
    for model in models_to_download:
        logger.info("")
        if download_model(model["name"], model["path"]):
            success_count += 1
    
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Download complete: {success_count}/{len(models_to_download)} models downloaded")
    logger.info("")
    
    if success_count > 0:
        logger.info("✓ Models are now available for offline use!")
        logger.info("  VOID will automatically load these models on next startup.")
        logger.info("")
        logger.info("Expected model locations:")
        for model in models_to_download:
            if (model["path"]).exists():
                logger.info(f"  ✓ {model['name']} -> {model['path']}")
            else:
                logger.info(f"  ✗ {model['name']} -> {model['path']} (not found)")
    else:
        logger.warning("⚠ No models were downloaded.")
        logger.info("  VOID will use sklearn models instead (which work fine for most cases).")


if __name__ == "__main__":
    main()

