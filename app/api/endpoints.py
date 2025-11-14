"""
FastAPI Endpoints
REST API for VOID Framework
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Body
from typing import Optional, List, Dict, Any
from app.models.schemas import TestSession, SystemStatus, TestCase
from app.core.session_manager import SessionManager
from app.core.preset_loader import PresetLoader
from config.settings import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
session_manager = SessionManager()
preset_loader = PresetLoader()


@router.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "VOID Framework API",
        "version": settings.app_version,
        "description": "Validation Of Industrial Devices",
        "endpoints": {
            "sessions": "/api/sessions",
            "create_session": "/api/sessions/create",
            "run_test": "/api/sessions/{session_id}/run",
            "status": "/api/sessions/{session_id}/status",
            "system": "/api/system/status"
        }
    }


@router.post("/sessions/create")
async def create_session(ipc_id: Optional[str] = None):
    """Create a new test session"""
    try:
        session = session_manager.create_session(ipc_id)
        return {
            "status": "success",
            "session_id": session.session_id,
            "ipc_id": session.ipc_id,
            "message": "Session created successfully"
        }
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/run")
async def run_test_session(
    session_id: str, 
    background_tasks: BackgroundTasks, 
    selected_test_ids: Optional[List[str]] = Query(None),
    preset_id: Optional[str] = Query(None)
):
    """Start test execution for a session with optional test selection or preset"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # If preset_id is provided, load test cases from preset
    if preset_id:
        preset = preset_loader.get_by_id(preset_id)
        if not preset:
            raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found")
        
        selected_test_ids = preset.test_cases
        logger.info(f"Running session {session_id} with preset '{preset.name}' ({len(selected_test_ids)} tests)")
    
    # Log selected tests
    if selected_test_ids:
        logger.info(f"Running session {session_id} with {len(selected_test_ids)} selected tests: {selected_test_ids}")
    else:
        logger.info(f"Running session {session_id} with all available tests")
    
    # Run test cycle in background with optional test selection
    background_tasks.add_task(
        session_manager.run_complete_test_cycle, 
        session_id,
        selected_test_ids=selected_test_ids
    )
    
    return {
        "status": "success",
        "session_id": session_id,
        "message": f"Test cycle started with {len(selected_test_ids) if selected_test_ids else 'all'} test(s)",
        "selected_tests": selected_test_ids if selected_test_ids else None,
        "preset_id": preset_id if preset_id else None
    }


@router.get("/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get current status of a test session"""
    status = session_manager.get_session_status(session_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    
    return status


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get complete session data"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Ensure test_cases are loaded if missing
    if not session.test_cases and session.test_results:
        # Load test cases from test loader based on test_ids in results
        test_ids = [tr.test_id for tr in session.test_results]
        all_tests = session_manager.test_loader.load_all()
        session.test_cases = [t for t in all_tests if t.id in test_ids]
        if session.test_cases:
            logger.info(f"Loaded {len(session.test_cases)} test cases for session {session_id}")
            # Save updated session
            session_manager.db.save_session(session)
    
    return session


@router.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop a running test session"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if session is already stopped or completed
    if session.status in ["stopped", "completed", "error"]:
        return {
            "status": "success",
            "session_id": session_id,
            "message": f"Session is already {session.status}",
            "current_status": session.status
        }
    
    # Try to stop the session (even if not in running_tasks, update status)
    stopped = await session_manager.stop_session(session_id)
    
    if stopped:
        return {
            "status": "success",
            "session_id": session_id,
            "message": "Session stopped successfully"
        }
    else:
        # If stop_session returned False, it might not be in running_tasks
        # But we can still mark it as stopped if it has a running status
        if session.status in ["testing", "analyzing", "detecting", "planning"]:
            session.status = "stopped"
            session.end_time = datetime.now()
            if session.start_time:
                session.total_duration = (session.end_time - session.start_time).total_seconds() / 3600
            session_manager.db.save_session(session)
            return {
                "status": "success",
                "session_id": session_id,
                "message": "Session marked as stopped"
            }
        else:
            raise HTTPException(status_code=400, detail=f"Session is not running (status: {session.status})")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a test session"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    deleted = session_manager.delete_session(session_id)
    
    if deleted:
        return {
            "status": "success",
            "session_id": session_id,
            "message": "Session deleted successfully"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to delete session")


@router.get("/sessions")
async def list_sessions():
    """List all test sessions"""
    sessions = session_manager.list_sessions()
    return {
        "total": len(sessions),
        "sessions": [
            {
                "session_id": s.session_id,
                "ipc_id": s.ipc_id,
                "status": s.status,
                "progress_percent": s.progress_percent,
                "start_time": s.start_time.isoformat()
            }
            for s in sessions
        ]
    }


@router.get("/system/status")
async def get_system_status():
    """Get system status"""
    from app.core.hardware_detection import HardwareDetector
    import re
    
    detector = HardwareDetector()
    current_ipc_model = detector.get_current_ipc_model()
    
    # Find matching preset
    matching_preset_id = None
    presets = preset_loader.load_all()
    current_model_lower = current_ipc_model.lower()
    
    logger.info(f"Matching presets for IPC model: {current_ipc_model}")
    
    for preset in presets:
        preset_model_lower = preset.model.lower()
        
        # Check if current IPC model matches preset model (bidirectional)
        # Remove common prefixes/suffixes for better matching
        current_clean = current_model_lower.replace('simatic ipc', '').replace('simatic', '').replace('siemens ag', '').strip()
        preset_clean = preset_model_lower.replace('simatic ipc', '').replace('simatic', '').strip()
        
        # Direct match (bidirectional substring check)
        # Example: "rw-545a" in "simatic ipc rw-545a" -> True
        if preset_model_lower in current_model_lower or current_model_lower in preset_model_lower:
            matching_preset_id = preset.id
            logger.info(f"Found matching preset via direct match: {preset.id} (current: {current_ipc_model}, preset: {preset.model})")
            break
        
        # Clean match (without prefixes) - e.g., "rw-545a" matches "rw-545a"
        if preset_clean and current_clean:
            if preset_clean in current_clean or current_clean in preset_clean:
                matching_preset_id = preset.id
                logger.info(f"Found matching preset via clean match: {preset.id} (current_clean: {current_clean}, preset_clean: {preset_clean})")
                break
        
        # Check for model numbers using regex (e.g., RW-545A, BX-39A)
        # Map preset IDs to their model patterns
        preset_patterns = {
            'simatic_ipc_rw_545a': r'rw[-\s]?545a',
            'simatic_ipc_bx_39a': r'bx[-\s]?39a',
            'simatic_ipc_bx_32a': r'bx[-\s]?32a'
        }
        
        if preset.id in preset_patterns:
            pattern = preset_patterns[preset.id]
            if re.search(pattern, current_model_lower, re.IGNORECASE):
                matching_preset_id = preset.id
                logger.info(f"Found matching preset via regex pattern: {preset.id} (pattern: {pattern})")
                break
        
        if matching_preset_id:
            break
    
    sessions = session_manager.list_sessions()
    active_sessions = len([s for s in sessions if s.status in ["testing", "analyzing", "detecting", "planning"]])
    completed_sessions = len([s for s in sessions if s.status == "completed"])
    
    return {
        "active_sessions": active_sessions,
        "total_sessions_completed": completed_sessions,
        "system_health": "healthy" if active_sessions < 10 else "degraded",
        "current_ipc_model": current_ipc_model,
        "matching_preset_id": matching_preset_id,
        "last_update": datetime.now().isoformat()
    }


@router.get("/tests/available")
async def get_available_tests(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=10, le=1000),
    category: Optional[str] = None,
    test_type: Optional[str] = None,
    priority_min: Optional[int] = None,
    priority_max: Optional[int] = None,
    duration_min: Optional[int] = None,
    duration_max: Optional[int] = None,
    search: Optional[str] = None,
    return_summary_only: bool = Query(False)
):
    """Get available tests with pagination and filtering"""
    all_tests = session_manager.test_loader.load_all()
    
    # Apply filters
    filtered_tests = all_tests
    
    if category:
        filtered_tests = [t for t in filtered_tests if t.category == category]
    
    if test_type:
        filtered_tests = [t for t in filtered_tests if t.test_type == test_type]
    
    if priority_min is not None:
        filtered_tests = [t for t in filtered_tests if t.priority >= priority_min]
    
    if priority_max is not None:
        filtered_tests = [t for t in filtered_tests if t.priority <= priority_max]
    
    if duration_min is not None:
        filtered_tests = [t for t in filtered_tests if t.duration_estimate >= duration_min]
    
    if duration_max is not None:
        filtered_tests = [t for t in filtered_tests if t.duration_estimate <= duration_max]
    
    if search:
        search_lower = search.lower()
        filtered_tests = [
            t for t in filtered_tests
            if search_lower in t.id.lower() or 
               search_lower in t.name.lower() or
               (t.description and search_lower in t.description.lower())
        ]
    
    total_filtered = len(filtered_tests)
    
    # If summary only requested, return just counts
    if return_summary_only:
        # Group by category for summary
        by_category = {}
        for test in filtered_tests:
            if test.category not in by_category:
                by_category[test.category] = 0
            by_category[test.category] += 1
        
        total_duration = sum(t.duration_estimate for t in filtered_tests)
        
        return {
            "total_tests": total_filtered,
            "total_duration_seconds": total_duration,
            "total_duration_hours": round(total_duration / 3600, 2),
            "categories": by_category,
            "page": 1,
            "page_size": total_filtered,
            "total_pages": 1
        }
    
    # Pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_tests = filtered_tests[start_idx:end_idx]
    
    # Group by category for paginated results
    by_category = {}
    for test in paginated_tests:
        if test.category not in by_category:
            by_category[test.category] = []
        by_category[test.category].append({
            "id": test.id,
            "name": test.name,
            "category": test.category,
            "test_type": test.test_type,
            "description": test.description,
            "duration_estimate": test.duration_estimate,
            "duration_minutes": round(test.duration_estimate / 60, 1),
            "priority": test.priority
        })
    
    # Calculate totals for filtered results
    total_duration = sum(t.duration_estimate for t in filtered_tests)
    total_pages = (total_filtered + page_size - 1) // page_size
    
    return {
        "total_tests": total_filtered,
        "total_duration_seconds": total_duration,
        "total_duration_hours": round(total_duration / 3600, 2),
        "categories": by_category,
        "tests": [
            {
                "id": test.id,
                "name": test.name,
                "category": test.category,
                "test_type": test.test_type,
                "description": test.description,
                "duration_estimate": test.duration_estimate,
                "duration_minutes": round(test.duration_estimate / 60, 1),
                "priority": test.priority
            }
            for test in paginated_tests
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_items": total_filtered,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


@router.post("/tests/bulk-select")
async def bulk_select_tests(
    filters: Dict[str, Any] = Body(...)
):
    """Get test IDs matching filters for bulk selection"""
    all_tests = session_manager.test_loader.load_all()
    
    # Apply same filters as get_available_tests
    filtered_tests = all_tests
    
    if filters.get("category"):
        filtered_tests = [t for t in filtered_tests if t.category == filters["category"]]
    
    if filters.get("test_type"):
        filtered_tests = [t for t in filtered_tests if t.test_type == filters["test_type"]]
    
    if filters.get("priority_min") is not None:
        filtered_tests = [t for t in filtered_tests if t.priority >= filters["priority_min"]]
    
    if filters.get("priority_max") is not None:
        filtered_tests = [t for t in filtered_tests if t.priority <= filters["priority_max"]]
    
    if filters.get("duration_min") is not None:
        filtered_tests = [t for t in filtered_tests if t.duration_estimate >= filters["duration_min"]]
    
    if filters.get("duration_max") is not None:
        filtered_tests = [t for t in filtered_tests if t.duration_estimate <= filters["duration_max"]]
    
    if filters.get("search"):
        search_lower = filters["search"].lower()
        filtered_tests = [
            t for t in filtered_tests
            if search_lower in t.id.lower() or 
               search_lower in t.name.lower() or
               (t.description and search_lower in t.description.lower())
        ]
    
    # Return only IDs for performance
    test_ids = [t.id for t in filtered_tests]
    total_duration = sum(t.duration_estimate for t in filtered_tests)
    
    return {
        "test_ids": test_ids,
        "count": len(test_ids),
        "total_duration_seconds": total_duration,
        "total_duration_hours": round(total_duration / 3600, 2)
    }


@router.get("/tests/{test_id}")
async def get_test_case(test_id: str):
    """Get a specific test case by ID"""
    test_case = session_manager.test_loader.get_by_id(test_id)
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    return test_case


@router.post("/tests/create")
async def create_test_case(test_case: TestCase):
    """Create a new test case"""
    try:
        # Check if test ID already exists
        existing = session_manager.test_loader.get_by_id(test_case.id)
        if existing:
            raise HTTPException(status_code=400, detail=f"Test case with ID '{test_case.id}' already exists")
        
        # Save to YAML file
        file_path = session_manager.test_loader.save_test_case(test_case)
        
        return {
            "status": "success",
            "test_id": test_case.id,
            "file_path": str(file_path),
            "message": "Test case created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create test case: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tests/{test_id}")
async def update_test_case(test_id: str, test_case: TestCase):
    """Update an existing test case"""
    try:
        # Check if test exists
        existing = session_manager.test_loader.get_by_id(test_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Test case not found")
        
        # If ID changed, delete old file
        if test_id != test_case.id:
            session_manager.test_loader.delete_test_case(test_id)
        
        # Save updated test case
        file_path = session_manager.test_loader.save_test_case(test_case)
        
        return {
            "status": "success",
            "test_id": test_case.id,
            "file_path": str(file_path),
            "message": "Test case updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update test case: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tests/{test_id}")
async def delete_test_case(test_id: str):
    """Delete a test case"""
    try:
        success = session_manager.test_loader.delete_test_case(test_id)
        if not success:
            raise HTTPException(status_code=404, detail="Test case not found")
        
        return {
            "status": "success",
            "test_id": test_id,
            "message": "Test case deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete test case: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/info")
async def get_model_info():
    """Get information about loaded AI models"""
    try:
        from app.ai.large_models import LargeModelManager
        manager = LargeModelManager()
        info = manager.get_model_info()
        return info
    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/version")
async def get_version():
    """Get framework version information"""
    return {
        "version": settings.app_version,
        "app_name": settings.app_name,
        "description": "Validation Of Industrial Devices"
    }


@router.get("/presets")
async def list_presets():
    """List all available test presets"""
    from app.core.hardware_detection import HardwareDetector
    import re
    
    detector = HardwareDetector()
    current_ipc_model = detector.get_current_ipc_model()
    
    presets = preset_loader.load_all()
    
    # Find matching preset
    matching_preset_id = None
    current_model_lower = current_ipc_model.lower()
    
    for preset in presets:
        preset_model_lower = preset.model.lower()
        
        # Check if current IPC model matches preset model (bidirectional)
        # Remove common prefixes/suffixes for better matching
        current_clean = current_model_lower.replace('simatic ipc', '').replace('simatic', '').replace('siemens ag', '').strip()
        preset_clean = preset_model_lower.replace('simatic ipc', '').replace('simatic', '').strip()
        
        # Direct match (bidirectional substring check)
        # Example: "rw-545a" in "simatic ipc rw-545a" -> True
        if preset_model_lower in current_model_lower or current_model_lower in preset_model_lower:
            matching_preset_id = preset.id
            break
        
        # Clean match (without prefixes) - e.g., "rw-545a" matches "rw-545a"
        if preset_clean and current_clean:
            if preset_clean in current_clean or current_clean in preset_clean:
                matching_preset_id = preset.id
                break
        
        # Check for model numbers using regex (e.g., RW-545A, BX-39A)
        # Map preset IDs to their model patterns
        preset_patterns = {
            'simatic_ipc_rw_545a': r'rw[-\s]?545a',
            'simatic_ipc_bx_39a': r'bx[-\s]?39a',
            'simatic_ipc_bx_32a': r'bx[-\s]?32a'
        }
        
        if preset.id in preset_patterns:
            pattern = preset_patterns[preset.id]
            if re.search(pattern, current_model_lower, re.IGNORECASE):
                matching_preset_id = preset.id
                break
        
        if matching_preset_id:
            break
    
    return {
        "total": len(presets),
        "current_ipc_model": current_ipc_model,
        "matching_preset_id": matching_preset_id,
        "presets": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "device_type": p.device_type,
                "manufacturer": p.manufacturer,
                "model": p.model,
                "test_case_count": len(p.test_cases),
                "hardware": p.hardware.model_dump() if p.hardware else None,
                "is_matching": p.id == matching_preset_id
            }
            for p in presets
        ]
    }


@router.get("/presets/{preset_id}")
async def get_preset(preset_id: str):
    """Get a specific preset with test case details"""
    preset = preset_loader.get_by_id(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    # Load test case details for the preset
    all_tests = session_manager.test_loader.load_all()
    preset_tests = [t for t in all_tests if t.id in preset.test_cases]
    
    return {
        "preset": {
            "id": preset.id,
            "name": preset.name,
            "description": preset.description,
            "device_type": preset.device_type,
            "manufacturer": preset.manufacturer,
            "model": preset.model,
            "hardware": preset.hardware.model_dump() if preset.hardware else None
        },
        "test_cases": [
            {
                "id": t.id,
                "name": t.name,
                "category": t.category,
                "test_type": t.test_type,
                "duration_estimate": t.duration_estimate,
                "priority": t.priority,
                "description": t.description
            }
            for t in preset_tests
        ],
        "total_tests": len(preset_tests),
        "total_duration_seconds": sum(t.duration_estimate for t in preset_tests),
        "total_duration_hours": round(sum(t.duration_estimate for t in preset_tests) / 3600, 2)
    }

