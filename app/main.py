"""
VOID Framework - Main FastAPI Application
Validation Of Industrial Devices
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.api.endpoints import router
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="VOID Framework API",
    description="Validation Of Industrial Devices - Automated IPC Testing System",
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api", tags=["VOID API"])

# Serve static files and dashboard
static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_dashboard():
    """Serve main dashboard"""
    dashboard_file = Path("static/index.html")
    if dashboard_file.exists():
        return FileResponse(dashboard_file)
    elif Path("static/dashboard.html").exists():
        return FileResponse(Path("static/dashboard.html"))
    else:
        return {
            "message": "VOID Framework API",
            "version": settings.app_version,
            "docs": "/api/docs",
            "dashboard": "Not configured"
        }


@app.get("/session_details.html")
async def serve_session_details():
    """Serve session details page"""
    details_file = Path("static/session_details.html")
    if details_file.exists():
        return FileResponse(details_file)
    else:
        return {"error": "Session details page not found"}


@app.get("/test_selection.html")
async def serve_test_selection():
    """Serve test selection page"""
    test_selection_file = Path("static/test_selection.html")
    if test_selection_file.exists():
        return FileResponse(test_selection_file)
    else:
        return {"error": "Test selection page not found"}


@app.get("/test_management.html")
async def serve_test_management():
    """Serve test case management page"""
    management_file = Path("static/test_management.html")
    if management_file.exists():
        return FileResponse(management_file)
    else:
        return {"error": "Test management page not found"}


@app.get("/reports/{report_path:path}")
async def serve_report(report_path: str):
    """Serve generated report files"""
    report_file = Path("reports") / report_path
    if report_file.exists() and report_file.is_file():
        return FileResponse(report_file)
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Report not found")

@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("=" * 60)
    logger.info("VOID Framework Starting...")
    logger.info(f"Validation Of Industrial Devices {settings.app_version}")
    logger.info("=" * 60)
    
    # Create necessary directories
    Path("testcases").mkdir(exist_ok=True)
    Path("reports/json").mkdir(parents=True, exist_ok=True)
    Path("reports/html").mkdir(parents=True, exist_ok=True)
    Path("reports/pdf").mkdir(parents=True, exist_ok=True)
    Path("static").mkdir(exist_ok=True)
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)  # AI model storage
    Path("logs").mkdir(exist_ok=True)
    
    logger.info("✓ Directories initialized")
    
    # Pre-load AI models to verify they're available
    logger.info("Loading AI models...")
    try:
        from app.ai.anomaly_detection import AnomalyDetector
        from app.ai.pattern_recognition import PatternRecognizer
        from app.ai.large_models import LargeModelManager
        
        # Load sklearn models (always available)
        anomaly_detector = AnomalyDetector()
        logger.info("✓ AnomalyDetector initialized")
        
        pattern_recognizer = PatternRecognizer()
        logger.info("✓ PatternRecognizer initialized")
        
        # Load large models (if available)
        large_model_manager = LargeModelManager()
        model_info = large_model_manager.get_model_info()
        if model_info["models_loaded"]:
            logger.info(f"✓ Large models loaded: {', '.join(model_info['models_loaded'])}")
        else:
            logger.info("⚠ No large models loaded (use scripts/download_models.py to download)")
        
        logger.info("✓ AI models initialized")
    except Exception as e:
        logger.warning(f"⚠ AI model initialization warning: {e}")
    
    logger.info("✓ API Server ready")
    logger.info("✓ Dashboard available at http://localhost:8000")
    logger.info("✓ API Docs at http://localhost:8000/api/docs")
    logger.info("=" * 60)

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("VOID Framework shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

