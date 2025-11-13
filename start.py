#!/usr/bin/env python3
"""
VOID Framework Starter
Quick start script for VOID Framework
"""

import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Check if Python version is 3.10+"""
    if sys.version_info < (3, 10):
        print("❌ Python 3.10 or higher is required!")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    print(f"✓ Python version: {sys.version.split()[0]}")


def create_directories():
    """Create necessary directories"""
    dirs = [
        "testcases",
        "reports/json",
        "reports/html",
        "reports/pdf",
        "static",
        "logs",
        "config"
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print("✓ Directories created")


def check_dependencies():
    """Check if dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import psutil
        import sklearn
        import yaml
        print("✓ All dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e.name}")
        print("   Run: pip install -r requirements.txt")
        return False


def main():
    """Main startup sequence"""
    print("=" * 60)
    print("🚀 VOID Framework Starting...")
    print("   Validation Of Industrial Devices v1.0.0")
    print("=" * 60)
    print()
    
    # Check Python version
    check_python_version()
    
    # Create directories
    create_directories()
    
    # Check dependencies
    if not check_dependencies():
        print()
        print("Please install dependencies first:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✓ All checks passed!")
    print()
    print("Starting VOID Framework Server...")
    print()
    print("🌐 Dashboard:  http://localhost:8000")
    print("📚 API Docs:   http://localhost:8000/api/docs")
    print("📊 ReDoc:      http://localhost:8000/api/redoc")
    print()
    print("Press CTRL+C to stop the server")
    print("=" * 60)
    print()
    
    # Start the server
    try:
        subprocess.run([
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print()
        print("=" * 60)
        print("🛑 VOID Framework stopped")
        print("=" * 60)


if __name__ == "__main__":
    main()

