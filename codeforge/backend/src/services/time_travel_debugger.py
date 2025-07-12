"""
Time-Travel Debugging Service
Revolutionary debugging that allows stepping through execution history
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import pickle
import gzip
import base64
from pathlib import Path

from ..config.settings import settings


class DebugEventType(str, Enum):
    """Types of debug events"""
    FUNCTION_CALL = "function_call"
    FUNCTION_RETURN = "function_return"
    VARIABLE_CHANGE = "variable_change"
    LINE_EXECUTED = "line_executed"
    EXCEPTION_RAISED = "exception_raised"
    EXCEPTION_CAUGHT = "exception_caught"
    BREAKPOINT_HIT = "breakpoint_hit"
    LOOP_ITERATION = "loop_iteration"
    CONDITION_EVALUATED = "condition_evaluated"


@dataclass
class VariableState:
    """State of a variable at a point in time"""
    name: str
    value: Any
    type_name: str
    memory_address: Optional[str] = None
    is_mutable: bool = True
    scope: str = "local"
    
    def serialize_value(self) -> str:
        """Serialize value for storage"""
        try:
            # Handle common types efficiently
            if isinstance(self.value, (str, int, float, bool, type(None))):
                return json.dumps(self.value)
            elif isinstance(self.value, (list, dict, tuple)):
                return json.dumps(self.value, default=str)
            else:
                # Use pickle for complex objects
                pickled = pickle.dumps(self.value)
                compressed = gzip.compress(pickled)
                return base64.b64encode(compressed).decode('utf-8')
        except Exception:
            return f"<{self.type_name} object at {self.memory_address}>"


@dataclass
class StackFrame:
    """Stack frame information"""
    function_name: str
    file_path: str
    line_number: int
    locals_vars: Dict[str, VariableState]
    args: Dict[str, Any]
    is_user_code: bool = True


@dataclass
class DebugEvent:
    """Single debug event in the execution timeline"""
    id: str
    timestamp: datetime
    event_type: DebugEventType
    file_path: str
    line_number: int
    function_name: str
    stack_frames: List[StackFrame]
    variables: Dict[str, VariableState]
    code_line: str
    thread_id: str
    process_id: str
    
    # Event-specific data
    exception_info: Optional[Dict] = None
    condition_result: Optional[bool] = None
    loop_vars: Optional[Dict] = None
    return_value: Optional[Any] = None


@dataclass
class ExecutionSession:
    """Complete execution session with timeline"""
    session_id: str
    project_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime]
    entry_point: str
    events: List[DebugEvent]
    breakpoints: List[Dict]
    is_active: bool = True
    total_events: int = 0
    
    def __post_init__(self):
        if not hasattr(self, 'events'):
            self.events = []


class TimePoint:
    """Represents a specific point in execution time"""
    
    def __init__(self, session_id: str, event_index: int, microsecond_offset: int = 0):
        self.session_id = session_id
        self.event_index = event_index
        self.microsecond_offset = microsecond_offset
    
    def __lt__(self, other: 'TimePoint') -> bool:
        if self.session_id != other.session_id:
            return False
        if self.event_index != other.event_index:
            return self.event_index < other.event_index
        return self.microsecond_offset < other.microsecond_offset
    
    def __eq__(self, other: 'TimePoint') -> bool:
        return (self.session_id == other.session_id and 
                self.event_index == other.event_index and
                self.microsecond_offset == other.microsecond_offset)


class TimeTravelDebugger:
    """
    Time-travel debugging system that captures execution history
    and allows navigation through time
    """
    
    def __init__(self):
        self.sessions: Dict[str, ExecutionSession] = {}
        self.active_sessions: Dict[str, str] = {}  # project_id -> session_id
        self.storage_path = Path(settings.DEBUG_STORAGE_PATH)
        self.storage_path.mkdir(exist_ok=True)
        
        # Performance settings
        self.max_events_in_memory = 10000
        self.compression_enabled = True
        self.variable_capture_depth = 5
        
    async def start_session(
        self,
        project_id: str,
        user_id: str,
        entry_point: str,
        breakpoints: List[Dict] = None
    ) -> str:
        """Start a new time-travel debugging session"""
        session_id = str(uuid.uuid4())
        
        session = ExecutionSession(
            session_id=session_id,
            project_id=project_id,
            user_id=user_id,
            start_time=datetime.now(timezone.utc),
            end_time=None,
            entry_point=entry_point,
            events=[],
            breakpoints=breakpoints or [],
            is_active=True
        )
        
        self.sessions[session_id] = session
        self.active_sessions[project_id] = session_id
        
        await self._persist_session_metadata(session)
        
        return session_id
    
    async def end_session(self, session_id: str) -> None:
        """End a debugging session and persist data"""
        session = self.sessions.get(session_id)
        if not session:
            return
            
        session.end_time = datetime.now(timezone.utc)
        session.is_active = False
        session.total_events = len(session.events)
        
        # Remove from active sessions
        if session.project_id in self.active_sessions:
            del self.active_sessions[session.project_id]
        
        # Persist complete session
        await self._persist_session_complete(session)
        
        # Keep in memory for a while for quick access
        # Could be moved to LRU cache in production
    
    async def capture_event(
        self,
        session_id: str,
        event_type: DebugEventType,
        file_path: str,
        line_number: int,
        function_name: str,
        locals_dict: Dict[str, Any],
        globals_dict: Dict[str, Any],
        stack_info: List[Dict],
        code_line: str,
        thread_id: str = "main",
        process_id: str = "main",
        **kwargs
    ) -> str:
        """Capture a debug event"""
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            return ""
        
        # Build stack frames
        stack_frames = []
        for frame_info in stack_info:
            frame_locals = {}
            for var_name, var_value in frame_info.get('locals', {}).items():
                if not var_name.startswith('__'):  # Skip internal variables
                    frame_locals[var_name] = VariableState(
                        name=var_name,
                        value=var_value,
                        type_name=type(var_value).__name__,
                        memory_address=hex(id(var_value)),
                        scope="local"
                    )
            
            stack_frames.append(StackFrame(
                function_name=frame_info.get('function', 'unknown'),
                file_path=frame_info.get('file', file_path),
                line_number=frame_info.get('line', line_number),
                locals_vars=frame_locals,
                args=frame_info.get('args', {}),
                is_user_code=not frame_info.get('file', '').startswith('/usr/')
            ))
        
        # Capture variable states
        variables = {}
        for var_name, var_value in locals_dict.items():
            if not var_name.startswith('__'):
                variables[var_name] = VariableState(
                    name=var_name,
                    value=var_value,
                    type_name=type(var_value).__name__,
                    memory_address=hex(id(var_value)),
                    scope="local"
                )
        
        # Add relevant global variables
        for var_name, var_value in globals_dict.items():
            if (not var_name.startswith('__') and 
                var_name not in variables and
                not callable(var_value)):
                variables[var_name] = VariableState(
                    name=var_name,
                    value=var_value,
                    type_name=type(var_value).__name__,
                    memory_address=hex(id(var_value)),
                    scope="global"
                )
        
        # Create debug event
        event = DebugEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            file_path=file_path,
            line_number=line_number,
            function_name=function_name,
            stack_frames=stack_frames,
            variables=variables,
            code_line=code_line,
            thread_id=thread_id,
            process_id=process_id,
            **kwargs
        )
        
        session.events.append(event)
        
        # Persist event if memory limit reached
        if len(session.events) > self.max_events_in_memory:
            await self._persist_events_batch(session)
        
        return event.id
    
    async def travel_to_time(self, session_id: str, time_point: TimePoint) -> Dict[str, Any]:
        """Travel to a specific point in execution time"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Load events if not in memory
        if time_point.event_index >= len(session.events):
            await self._load_session_events(session_id)
        
        if time_point.event_index >= len(session.events):
            raise ValueError(f"Event index {time_point.event_index} out of range")
        
        target_event = session.events[time_point.event_index]
        
        # Build execution state at this point
        return {
            "session_id": session_id,
            "time_point": {
                "event_index": time_point.event_index,
                "timestamp": target_event.timestamp.isoformat(),
                "event_type": target_event.event_type
            },
            "execution_state": {
                "file_path": target_event.file_path,
                "line_number": target_event.line_number,
                "function_name": target_event.function_name,
                "code_line": target_event.code_line,
                "variables": {
                    name: {
                        "name": var.name,
                        "value": var.serialize_value(),
                        "type": var.type_name,
                        "scope": var.scope
                    }
                    for name, var in target_event.variables.items()
                },
                "stack_frames": [
                    {
                        "function": frame.function_name,
                        "file": frame.file_path,
                        "line": frame.line_number,
                        "is_user_code": frame.is_user_code,
                        "locals": {
                            name: var.serialize_value()
                            for name, var in frame.locals_vars.items()
                        }
                    }
                    for frame in target_event.stack_frames
                ]
            },
            "navigation": {
                "can_step_back": time_point.event_index > 0,
                "can_step_forward": time_point.event_index < len(session.events) - 1,
                "total_events": len(session.events)
            }
        }
    
    async def step_back(self, session_id: str, current_time: TimePoint, steps: int = 1) -> TimePoint:
        """Step back in time by N steps"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        new_index = max(0, current_time.event_index - steps)
        return TimePoint(session_id, new_index)
    
    async def step_forward(self, session_id: str, current_time: TimePoint, steps: int = 1) -> TimePoint:
        """Step forward in time by N steps"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        new_index = min(len(session.events) - 1, current_time.event_index + steps)
        return TimePoint(session_id, new_index)
    
    async def find_variable_changes(
        self,
        session_id: str,
        variable_name: str,
        start_time: Optional[TimePoint] = None,
        end_time: Optional[TimePoint] = None
    ) -> List[Dict]:
        """Find all points where a variable changed"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        start_idx = start_time.event_index if start_time else 0
        end_idx = end_time.event_index if end_time else len(session.events) - 1
        
        changes = []
        last_value = None
        
        for i in range(start_idx, min(end_idx + 1, len(session.events))):
            event = session.events[i]
            
            if variable_name in event.variables:
                current_value = event.variables[variable_name].serialize_value()
                
                if last_value is None or current_value != last_value:
                    changes.append({
                        "time_point": {"event_index": i, "timestamp": event.timestamp.isoformat()},
                        "old_value": last_value,
                        "new_value": current_value,
                        "file_path": event.file_path,
                        "line_number": event.line_number,
                        "function_name": event.function_name
                    })
                    last_value = current_value
        
        return changes
    
    async def find_function_calls(
        self,
        session_id: str,
        function_name: str,
        start_time: Optional[TimePoint] = None,
        end_time: Optional[TimePoint] = None
    ) -> List[Dict]:
        """Find all calls to a specific function"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        start_idx = start_time.event_index if start_time else 0
        end_idx = end_time.event_index if end_time else len(session.events) - 1
        
        calls = []
        
        for i in range(start_idx, min(end_idx + 1, len(session.events))):
            event = session.events[i]
            
            if (event.event_type == DebugEventType.FUNCTION_CALL and 
                event.function_name == function_name):
                
                # Find corresponding return
                return_event = None
                for j in range(i + 1, min(end_idx + 1, len(session.events))):
                    if (session.events[j].event_type == DebugEventType.FUNCTION_RETURN and
                        session.events[j].function_name == function_name):
                        return_event = session.events[j]
                        break
                
                calls.append({
                    "call_time": {"event_index": i, "timestamp": event.timestamp.isoformat()},
                    "return_time": {
                        "event_index": j if return_event else None,
                        "timestamp": return_event.timestamp.isoformat() if return_event else None
                    },
                    "file_path": event.file_path,
                    "line_number": event.line_number,
                    "arguments": {
                        name: var.serialize_value()
                        for name, var in event.variables.items()
                        if var.scope == "local"
                    },
                    "return_value": return_event.return_value if return_event else None
                })
        
        return calls
    
    async def search_timeline(
        self,
        session_id: str,
        query: Dict[str, Any],
        limit: int = 100
    ) -> List[Dict]:
        """Search execution timeline with filters"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        results = []
        
        for i, event in enumerate(session.events):
            if len(results) >= limit:
                break
            
            matches = True
            
            # Filter by event type
            if "event_type" in query and event.event_type != query["event_type"]:
                matches = False
            
            # Filter by file
            if "file_path" in query and query["file_path"] not in event.file_path:
                matches = False
            
            # Filter by function
            if "function_name" in query and event.function_name != query["function_name"]:
                matches = False
            
            # Filter by line range
            if "line_range" in query:
                line_start, line_end = query["line_range"]
                if not (line_start <= event.line_number <= line_end):
                    matches = False
            
            # Filter by variable presence
            if "has_variable" in query and query["has_variable"] not in event.variables:
                matches = False
            
            # Filter by time range
            if "time_range" in query:
                start_time, end_time = query["time_range"]
                if not (start_time <= event.timestamp <= end_time):
                    matches = False
            
            if matches:
                results.append({
                    "time_point": {"event_index": i, "timestamp": event.timestamp.isoformat()},
                    "event_type": event.event_type,
                    "file_path": event.file_path,
                    "line_number": event.line_number,
                    "function_name": event.function_name,
                    "code_line": event.code_line,
                    "variable_count": len(event.variables)
                })
        
        return results
    
    async def get_session_timeline(self, session_id: str) -> Dict[str, Any]:
        """Get complete session timeline summary"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Calculate statistics
        event_types = {}
        files_touched = set()
        functions_called = set()
        
        for event in session.events:
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
            files_touched.add(event.file_path)
            functions_called.add(event.function_name)
        
        return {
            "session_id": session_id,
            "project_id": session.project_id,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "entry_point": session.entry_point,
            "is_active": session.is_active,
            "statistics": {
                "total_events": len(session.events),
                "event_types": event_types,
                "files_touched": len(files_touched),
                "functions_called": len(functions_called),
                "duration_seconds": (
                    (session.end_time or datetime.now(timezone.utc)) - session.start_time
                ).total_seconds()
            },
            "breakpoints": session.breakpoints
        }
    
    async def _persist_session_metadata(self, session: ExecutionSession) -> None:
        """Persist session metadata"""
        metadata_path = self.storage_path / f"{session.session_id}_metadata.json"
        
        metadata = {
            "session_id": session.session_id,
            "project_id": session.project_id,
            "user_id": session.user_id,
            "start_time": session.start_time.isoformat(),
            "entry_point": session.entry_point,
            "breakpoints": session.breakpoints
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    async def _persist_session_complete(self, session: ExecutionSession) -> None:
        """Persist complete session data"""
        session_path = self.storage_path / f"{session.session_id}_complete.json.gz"
        
        session_data = asdict(session)
        
        # Serialize datetime objects
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)
        
        json_data = json.dumps(session_data, default=serialize_datetime)
        
        if self.compression_enabled:
            compressed_data = gzip.compress(json_data.encode('utf-8'))
            with open(session_path, 'wb') as f:
                f.write(compressed_data)
        else:
            with open(session_path, 'w') as f:
                f.write(json_data)
    
    async def _persist_events_batch(self, session: ExecutionSession) -> None:
        """Persist a batch of events to free memory"""
        # In production, this would use a more efficient storage format
        # and keep only recent events in memory
        pass
    
    async def _load_session_events(self, session_id: str) -> None:
        """Load session events from storage"""
        # In production, this would load events on demand
        pass
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return [
            session_id for session_id, session in self.sessions.items()
            if session.is_active
        ]
    
    async def cleanup_old_sessions(self, max_age_hours: int = 24) -> None:
        """Clean up old debugging sessions"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        
        sessions_to_remove = []
        for session_id, session in self.sessions.items():
            if (not session.is_active and 
                session.start_time.timestamp() < cutoff_time):
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.sessions[session_id]