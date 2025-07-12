"""
Time-Travel Debugging API endpoints for CodeForge
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import datetime

from ...services.time_travel_debugger import (
    TimeTravelDebugger, TimePoint, DebugEventType
)
from ...auth.dependencies import get_current_user
from ...models.user import User


router = APIRouter(prefix="/debug", tags=["debug"])

# Shared time-travel debugger instance
debugger = TimeTravelDebugger()


class StartSessionRequest(BaseModel):
    project_id: str
    entry_point: str
    breakpoints: List[Dict] = []


class CaptureEventRequest(BaseModel):
    session_id: str
    event_type: str
    file_path: str
    line_number: int
    function_name: str
    locals_dict: Dict[str, Any]
    globals_dict: Dict[str, Any]
    stack_info: List[Dict]
    code_line: str
    thread_id: str = "main"
    process_id: str = "main"


class TravelToTimeRequest(BaseModel):
    session_id: str
    event_index: int
    microsecond_offset: int = 0


class SearchTimelineRequest(BaseModel):
    session_id: str
    query: Dict[str, Any]
    limit: int = 100


class StepRequest(BaseModel):
    session_id: str
    current_event_index: int
    steps: int = 1


@router.post("/sessions/start")
async def start_debug_session(
    request: StartSessionRequest,
    current_user: User = Depends(get_current_user)
):
    """Start a new time-travel debugging session"""
    try:
        session_id = await debugger.start_session(
            project_id=request.project_id,
            user_id=current_user.id,
            entry_point=request.entry_point,
            breakpoints=request.breakpoints
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Time-travel debugging session started",
            "instructions": {
                "1": "Set breakpoints in your code editor",
                "2": "Run your code with time-travel debugging enabled",
                "3": "Use the debugger to step through execution history",
                "4": "Travel back in time to any point in execution"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start debug session: {str(e)}"
        )


@router.post("/sessions/{session_id}/end")
async def end_debug_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """End a debugging session"""
    try:
        await debugger.end_session(session_id)
        
        return {
            "success": True,
            "message": "Debug session ended and data persisted"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end debug session: {str(e)}"
        )


@router.post("/sessions/{session_id}/events")
async def capture_debug_event(
    session_id: str,
    request: CaptureEventRequest,
    current_user: User = Depends(get_current_user)
):
    """Capture a debug event during execution"""
    try:
        event_id = await debugger.capture_event(
            session_id=session_id,
            event_type=DebugEventType(request.event_type),
            file_path=request.file_path,
            line_number=request.line_number,
            function_name=request.function_name,
            locals_dict=request.locals_dict,
            globals_dict=request.globals_dict,
            stack_info=request.stack_info,
            code_line=request.code_line,
            thread_id=request.thread_id,
            process_id=request.process_id
        )
        
        return {
            "success": True,
            "event_id": event_id,
            "captured_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to capture debug event: {str(e)}"
        )


@router.post("/travel")
async def travel_to_time(
    request: TravelToTimeRequest,
    current_user: User = Depends(get_current_user)
):
    """Travel to a specific point in execution time"""
    try:
        time_point = TimePoint(
            session_id=request.session_id,
            event_index=request.event_index,
            microsecond_offset=request.microsecond_offset
        )
        
        execution_state = await debugger.travel_to_time(request.session_id, time_point)
        
        return {
            "success": True,
            "execution_state": execution_state,
            "message": f"Traveled to event {request.event_index}"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to travel to time: {str(e)}"
        )


@router.post("/step-back")
async def step_back_in_time(
    request: StepRequest,
    current_user: User = Depends(get_current_user)
):
    """Step back in execution time"""
    try:
        current_time = TimePoint(request.session_id, request.current_event_index)
        new_time = await debugger.step_back(request.session_id, current_time, request.steps)
        
        execution_state = await debugger.travel_to_time(request.session_id, new_time)
        
        return {
            "success": True,
            "new_time_point": {
                "event_index": new_time.event_index,
                "steps_back": request.steps
            },
            "execution_state": execution_state
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to step back: {str(e)}"
        )


@router.post("/step-forward")
async def step_forward_in_time(
    request: StepRequest,
    current_user: User = Depends(get_current_user)
):
    """Step forward in execution time"""
    try:
        current_time = TimePoint(request.session_id, request.current_event_index)
        new_time = await debugger.step_forward(request.session_id, current_time, request.steps)
        
        execution_state = await debugger.travel_to_time(request.session_id, new_time)
        
        return {
            "success": True,
            "new_time_point": {
                "event_index": new_time.event_index,
                "steps_forward": request.steps
            },
            "execution_state": execution_state
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to step forward: {str(e)}"
        )


@router.get("/sessions/{session_id}/timeline")
async def get_session_timeline(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get complete session timeline and statistics"""
    try:
        timeline = await debugger.get_session_timeline(session_id)
        
        return timeline
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get timeline: {str(e)}"
        )


@router.post("/search")
async def search_execution_timeline(
    request: SearchTimelineRequest,
    current_user: User = Depends(get_current_user)
):
    """Search execution timeline with filters"""
    try:
        results = await debugger.search_timeline(
            session_id=request.session_id,
            query=request.query,
            limit=request.limit
        )
        
        return {
            "success": True,
            "results": results,
            "total_found": len(results),
            "query": request.query
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search timeline: {str(e)}"
        )


@router.get("/sessions/{session_id}/variables/{variable_name}/changes")
async def get_variable_changes(
    session_id: str,
    variable_name: str,
    start_event: int = 0,
    end_event: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all changes to a specific variable over time"""
    try:
        start_time = TimePoint(session_id, start_event)
        end_time = TimePoint(session_id, end_event) if end_event is not None else None
        
        changes = await debugger.find_variable_changes(
            session_id=session_id,
            variable_name=variable_name,
            start_time=start_time,
            end_time=end_time
        )
        
        return {
            "success": True,
            "variable_name": variable_name,
            "changes": changes,
            "total_changes": len(changes)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get variable changes: {str(e)}"
        )


@router.get("/sessions/{session_id}/functions/{function_name}/calls")
async def get_function_calls(
    session_id: str,
    function_name: str,
    start_event: int = 0,
    end_event: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all calls to a specific function over time"""
    try:
        start_time = TimePoint(session_id, start_event)
        end_time = TimePoint(session_id, end_event) if end_event is not None else None
        
        calls = await debugger.find_function_calls(
            session_id=session_id,
            function_name=function_name,
            start_time=start_time,
            end_time=end_time
        )
        
        return {
            "success": True,
            "function_name": function_name,
            "calls": calls,
            "total_calls": len(calls)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get function calls: {str(e)}"
        )


@router.get("/sessions/active")
async def get_active_sessions(
    current_user: User = Depends(get_current_user)
):
    """Get all active debugging sessions"""
    try:
        active_sessions = debugger.get_active_sessions()
        
        session_details = []
        for session_id in active_sessions:
            timeline = await debugger.get_session_timeline(session_id)
            session_details.append(timeline)
        
        return {
            "active_sessions": session_details,
            "total_count": len(active_sessions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active sessions: {str(e)}"
        )


@router.get("/features")
async def get_debug_features(
    current_user: User = Depends(get_current_user)
):
    """Get available time-travel debugging features"""
    return {
        "features": {
            "time_travel": {
                "description": "Step back and forward through execution history",
                "capabilities": [
                    "Navigate to any point in execution",
                    "View variable states at any time",
                    "Inspect stack frames across time",
                    "Compare states between time points"
                ]
            },
            "variable_tracking": {
                "description": "Track variable changes over time",
                "capabilities": [
                    "Find all modifications to a variable",
                    "See variable evolution timeline",
                    "Compare values across time",
                    "Detect unexpected changes"
                ]
            },
            "function_analysis": {
                "description": "Analyze function behavior over time",
                "capabilities": [
                    "Track all function calls",
                    "Measure execution time",
                    "Analyze return values",
                    "Find performance bottlenecks"
                ]
            },
            "advanced_search": {
                "description": "Search execution history with filters",
                "capabilities": [
                    "Filter by event type",
                    "Search by file or function",
                    "Time range filtering",
                    "Condition-based searches"
                ]
            }
        },
        "supported_languages": ["Python", "JavaScript", "TypeScript"],
        "performance": {
            "max_events_in_memory": debugger.max_events_in_memory,
            "compression_enabled": debugger.compression_enabled,
            "variable_capture_depth": debugger.variable_capture_depth
        }
    }


@router.delete("/sessions/{session_id}")
async def delete_debug_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a debugging session and its data"""
    try:
        await debugger.end_session(session_id)
        
        # Remove from memory
        if session_id in debugger.sessions:
            del debugger.sessions[session_id]
        
        return {
            "success": True,
            "message": f"Debug session {session_id} deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete debug session: {str(e)}"
        )


@router.get("/health")
async def debug_service_health():
    """Get debugging service health status"""
    active_sessions = debugger.get_active_sessions()
    
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "total_sessions": len(debugger.sessions),
        "memory_usage": {
            "sessions_in_memory": len(debugger.sessions),
            "max_events_per_session": debugger.max_events_in_memory
        },
        "features_enabled": {
            "time_travel": True,
            "variable_tracking": True,
            "function_analysis": True,
            "compression": debugger.compression_enabled
        }
    }