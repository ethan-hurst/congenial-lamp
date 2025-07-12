/**
 * Time-Travel Debugger Interface
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  HiPlay,
  HiPause,
  HiRewind,
  HiFastForward,
  HiSkipBack,
  HiSkipForward,
  HiRefresh,
  HiClock,
  HiVariable,
  HiCode,
  HiSearch,
  HiChevronLeft,
  HiChevronRight,
  HiEye,
  HiPencil
} from 'react-icons/hi';
import { FaStepBackward, FaStepForward } from 'react-icons/fa';

import { api } from '../../services/api';
import { useProjectStore } from '../../stores/projectStore';

interface TimePoint {
  event_index: number;
  timestamp: string;
  event_type: string;
}

interface ExecutionState {
  file_path: string;
  line_number: number;
  function_name: string;
  code_line: string;
  variables: Record<string, any>;
  stack_frames: Array<{
    function: string;
    file: string;
    line: number;
    is_user_code: boolean;
    locals: Record<string, any>;
  }>;
}

interface DebugSession {
  session_id: string;
  project_id: string;
  start_time: string;
  is_active: boolean;
  statistics: {
    total_events: number;
    event_types: Record<string, number>;
    files_touched: number;
    functions_called: number;
    duration_seconds: number;
  };
}

interface TimeTravelDebuggerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const TimeTravelDebugger: React.FC<TimeTravelDebuggerProps> = ({ isOpen, onClose }) => {
  const { currentProject } = useProjectStore();
  
  // State
  const [session, setSession] = useState<DebugSession | null>(null);
  const [currentTimePoint, setCurrentTimePoint] = useState<TimePoint | null>(null);
  const [executionState, setExecutionState] = useState<ExecutionState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  
  // UI State
  const [selectedTab, setSelectedTab] = useState<'timeline' | 'variables' | 'stack' | 'search'>('timeline');
  const [searchQuery, setSearchQuery] = useState('');
  const [variableFilter, setVariableFilter] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  
  // Timeline state
  const [timelineEvents, setTimelineEvents] = useState<any[]>([]);
  const [variableChanges, setVariableChanges] = useState<Record<string, any[]>>({});
  
  // Refs
  const playbackInterval = useRef<NodeJS.Timeout | null>(null);

  // Start a new debugging session
  const startSession = useCallback(async () => {
    if (!currentProject) return;

    try {
      setIsLoading(true);
      const response = await api.startDebugSession({
        project_id: currentProject.id,
        entry_point: 'main.py', // This would be configurable
        breakpoints: []
      });

      if (response.success) {
        setIsRecording(true);
        // Load session details
        await loadSessionTimeline(response.session_id);
      }
    } catch (error) {
      console.error('Failed to start debug session:', error);
    } finally {
      setIsLoading(false);
    }
  }, [currentProject]);

  // Load session timeline
  const loadSessionTimeline = useCallback(async (sessionId: string) => {
    try {
      const timeline = await api.getDebugTimeline(sessionId);
      setSession(timeline);
      
      // Load recent events for timeline view
      const searchResults = await api.searchDebugTimeline(sessionId, {}, 1000);
      setTimelineEvents(searchResults.results);
      
      // If we have events, go to the latest one
      if (searchResults.results.length > 0) {
        const latestEvent = searchResults.results[searchResults.results.length - 1];
        await travelToTime(sessionId, latestEvent.time_point.event_index);
      }
    } catch (error) {
      console.error('Failed to load timeline:', error);
    }
  }, []);

  // Travel to specific time point
  const travelToTime = useCallback(async (sessionId: string, eventIndex: number) => {
    try {
      setIsLoading(true);
      const response = await api.travelToTime({
        session_id: sessionId,
        event_index: eventIndex
      });

      if (response.success) {
        setCurrentTimePoint(response.execution_state.time_point);
        setExecutionState(response.execution_state.execution_state);
      }
    } catch (error) {
      console.error('Failed to travel to time:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Step back in time
  const stepBack = useCallback(async (steps = 1) => {
    if (!session || !currentTimePoint) return;

    try {
      const response = await api.stepBackInTime({
        session_id: session.session_id,
        current_event_index: currentTimePoint.event_index,
        steps
      });

      if (response.success) {
        setCurrentTimePoint(response.execution_state.time_point);
        setExecutionState(response.execution_state.execution_state);
      }
    } catch (error) {
      console.error('Failed to step back:', error);
    }
  }, [session, currentTimePoint]);

  // Step forward in time
  const stepForward = useCallback(async (steps = 1) => {
    if (!session || !currentTimePoint) return;

    try {
      const response = await api.stepForwardInTime({
        session_id: session.session_id,
        current_event_index: currentTimePoint.event_index,
        steps
      });

      if (response.success) {
        setCurrentTimePoint(response.execution_state.time_point);
        setExecutionState(response.execution_state.execution_state);
      }
    } catch (error) {
      console.error('Failed to step forward:', error);
    }
  }, [session, currentTimePoint]);

  // Auto-play through timeline
  const togglePlayback = useCallback(() => {
    if (isPlaying) {
      if (playbackInterval.current) {
        clearInterval(playbackInterval.current);
        playbackInterval.current = null;
      }
      setIsPlaying(false);
    } else {
      setIsPlaying(true);
      playbackInterval.current = setInterval(() => {
        stepForward(1);
      }, 1000 / playbackSpeed);
    }
  }, [isPlaying, playbackSpeed, stepForward]);

  // Load variable changes for a specific variable
  const loadVariableChanges = useCallback(async (variableName: string) => {
    if (!session) return;

    try {
      const changes = await api.getVariableChanges(session.session_id, variableName);
      setVariableChanges(prev => ({
        ...prev,
        [variableName]: changes.changes
      }));
    } catch (error) {
      console.error('Failed to load variable changes:', error);
    }
  }, [session]);

  // Search timeline
  const searchTimeline = useCallback(async () => {
    if (!session || !searchQuery.trim()) return;

    try {
      const results = await api.searchDebugTimeline(session.session_id, {
        function_name: searchQuery.includes('function:') ? searchQuery.replace('function:', '') : undefined,
        file_path: searchQuery.includes('file:') ? searchQuery.replace('file:', '') : undefined,
        has_variable: searchQuery.includes('var:') ? searchQuery.replace('var:', '') : undefined,
      });
      
      setTimelineEvents(results.results);
    } catch (error) {
      console.error('Failed to search timeline:', error);
    }
  }, [session, searchQuery]);

  // Format variable value for display
  const formatVariableValue = (value: any) => {
    if (typeof value === 'string' && value.startsWith('"') && value.endsWith('"')) {
      try {
        return JSON.parse(value);
      } catch {
        return value;
      }
    }
    return value;
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (playbackInterval.current) {
        clearInterval(playbackInterval.current);
      }
    };
  }, []);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-7xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <HiClock className="w-6 h-6 text-primary-600 dark:text-primary-400" />
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                Time-Travel Debugger
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Debug across time - step through execution history
              </p>
            </div>
          </div>
          
          {/* Session Controls */}
          <div className="flex items-center space-x-3">
            {!session ? (
              <button
                onClick={startSession}
                disabled={isLoading}
                className="flex items-center space-x-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white rounded-lg transition"
              >
                {isLoading ? (
                  <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                ) : (
                  <HiPlay className="w-4 h-4" />
                )}
                <span>Start Session</span>
              </button>
            ) : (
              <div className="flex items-center space-x-2 text-sm">
                <div className={`w-2 h-2 rounded-full ${isRecording ? 'bg-red-500' : 'bg-gray-400'}`} />
                <span className="text-gray-600 dark:text-gray-400">
                  {session.statistics.total_events} events captured
                </span>
              </div>
            )}
            
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <HiClock className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Panel - Navigation & Controls */}
          <div className="w-80 border-r border-gray-200 dark:border-gray-700 flex flex-col">
            {/* Time Navigation Controls */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Time Navigation</h3>
              
              {/* Playback Controls */}
              <div className="flex items-center justify-center space-x-2 mb-4">
                <button
                  onClick={() => stepBack(10)}
                  disabled={!currentTimePoint || currentTimePoint.event_index <= 9}
                  className="p-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 rounded"
                >
                  <FaStepBackward className="w-4 h-4" />
                </button>
                
                <button
                  onClick={() => stepBack(1)}
                  disabled={!currentTimePoint || currentTimePoint.event_index <= 0}
                  className="p-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 rounded"
                >
                  <HiChevronLeft className="w-4 h-4" />
                </button>
                
                <button
                  onClick={togglePlayback}
                  disabled={!session}
                  className="p-3 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white rounded"
                >
                  {isPlaying ? (
                    <HiPause className="w-5 h-5" />
                  ) : (
                    <HiPlay className="w-5 h-5" />
                  )}
                </button>
                
                <button
                  onClick={() => stepForward(1)}
                  disabled={!session || !currentTimePoint}
                  className="p-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 rounded"
                >
                  <HiChevronRight className="w-4 h-4" />
                </button>
                
                <button
                  onClick={() => stepForward(10)}
                  disabled={!session || !currentTimePoint}
                  className="p-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 rounded"
                >
                  <FaStepForward className="w-4 h-4" />
                </button>
              </div>
              
              {/* Current Time Point */}
              {currentTimePoint && (
                <div className="text-center text-sm">
                  <div className="font-mono text-gray-900 dark:text-white">
                    Event {currentTimePoint.event_index}
                  </div>
                  <div className="text-gray-500 dark:text-gray-400">
                    {new Date(currentTimePoint.timestamp).toLocaleTimeString()}
                  </div>
                  <div className="text-xs text-gray-400">
                    {currentTimePoint.event_type.replace('_', ' ')}
                  </div>
                </div>
              )}
              
              {/* Playback Speed */}
              <div className="mt-3">
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Playback Speed
                </label>
                <select
                  value={playbackSpeed}
                  onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
                  className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700"
                >
                  <option value={0.25}>0.25x</option>
                  <option value={0.5}>0.5x</option>
                  <option value={1}>1x</option>
                  <option value={2}>2x</option>
                  <option value={4}>4x</option>
                </select>
              </div>
            </div>

            {/* Session Statistics */}
            {session && (
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Session Stats</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Total Events:</span>
                    <span className="font-mono">{session.statistics.total_events}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Files Touched:</span>
                    <span className="font-mono">{session.statistics.files_touched}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Functions:</span>
                    <span className="font-mono">{session.statistics.functions_called}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Duration:</span>
                    <span className="font-mono">{session.statistics.duration_seconds.toFixed(1)}s</span>
                  </div>
                </div>
              </div>
            )}

            {/* Quick Search */}
            <div className="p-4">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Quick Search</h3>
              <div className="flex space-x-2">
                <input
                  type="text"
                  placeholder="function:name or var:variable"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="flex-1 text-sm border border-gray-300 dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-700"
                />
                <button
                  onClick={searchTimeline}
                  className="p-2 bg-primary-600 hover:bg-primary-700 text-white rounded"
                >
                  <HiSearch className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Right Panel - Details */}
          <div className="flex-1 flex flex-col">
            {/* Tab Navigation */}
            <div className="border-b border-gray-200 dark:border-gray-700">
              <nav className="flex space-x-8 px-6">
                {[
                  { id: 'timeline', label: 'Timeline', icon: HiClock },
                  { id: 'variables', label: 'Variables', icon: HiVariable },
                  { id: 'stack', label: 'Call Stack', icon: HiCode },
                  { id: 'search', label: 'Search', icon: HiSearch },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setSelectedTab(tab.id as any)}
                    className={`flex items-center space-x-2 py-4 px-2 border-b-2 font-medium text-sm ${
                      selectedTab === tab.id
                        ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                        : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
                    }`}
                  >
                    <tab.icon className="w-4 h-4" />
                    <span>{tab.label}</span>
                  </button>
                ))}
              </nav>
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-auto p-6">
              {selectedTab === 'timeline' && (
                <div className="space-y-4">
                  <h3 className="font-semibold text-gray-900 dark:text-white">Execution Timeline</h3>
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {timelineEvents.map((event, index) => (
                      <div
                        key={index}
                        onClick={() => session && travelToTime(session.session_id, event.time_point.event_index)}
                        className={`p-3 border rounded-lg cursor-pointer transition ${
                          currentTimePoint?.event_index === event.time_point.event_index
                            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            <span className="font-mono text-sm text-gray-500">
                              #{event.time_point.event_index}
                            </span>
                            <span className="text-sm font-medium">
                              {event.function_name}
                            </span>
                            <span className="text-xs text-gray-500">
                              {event.event_type.replace('_', ' ')}
                            </span>
                          </div>
                          <span className="text-xs text-gray-400">
                            {new Date(event.time_point.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                          {event.file_path}:{event.line_number}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedTab === 'variables' && executionState && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-gray-900 dark:text-white">Variables</h3>
                    <input
                      type="text"
                      placeholder="Filter variables..."
                      value={variableFilter}
                      onChange={(e) => setVariableFilter(e.target.value)}
                      className="text-sm border border-gray-300 dark:border-gray-600 rounded px-3 py-1 bg-white dark:bg-gray-700"
                    />
                  </div>
                  
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {Object.entries(executionState.variables)
                      .filter(([name]) => 
                        !variableFilter || name.toLowerCase().includes(variableFilter.toLowerCase())
                      )
                      .map(([name, variable]) => (
                        <div
                          key={name}
                          className="p-3 border border-gray-200 dark:border-gray-700 rounded-lg"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <span className="font-mono text-sm font-medium">{name}</span>
                              <span className="text-xs text-gray-500">({variable.type})</span>
                              <button
                                onClick={() => loadVariableChanges(name)}
                                className="text-xs text-primary-600 hover:text-primary-700"
                              >
                                <HiEye className="w-3 h-3" />
                              </button>
                            </div>
                            <span className="text-xs text-gray-400">{variable.scope}</span>
                          </div>
                          <div className="mt-2 text-sm font-mono bg-gray-50 dark:bg-gray-700 p-2 rounded">
                            {JSON.stringify(formatVariableValue(variable.value), null, 2)}
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              )}

              {selectedTab === 'stack' && executionState && (
                <div className="space-y-4">
                  <h3 className="font-semibold text-gray-900 dark:text-white">Call Stack</h3>
                  <div className="space-y-2">
                    {executionState.stack_frames.map((frame, index) => (
                      <div
                        key={index}
                        className={`p-3 border rounded-lg ${
                          frame.is_user_code
                            ? 'border-blue-200 bg-blue-50 dark:bg-blue-900/20'
                            : 'border-gray-200 bg-gray-50 dark:bg-gray-700'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-sm font-medium">{frame.function}</span>
                          <span className="text-xs text-gray-500">
                            {frame.is_user_code ? 'User Code' : 'System'}
                          </span>
                        </div>
                        <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                          {frame.file}:{frame.line}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedTab === 'search' && (
                <div className="space-y-4">
                  <h3 className="font-semibold text-gray-900 dark:text-white">Advanced Search</h3>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    <p>Search patterns:</p>
                    <ul className="list-disc ml-4 mt-2 space-y-1">
                      <li><code>function:myFunction</code> - Find function calls</li>
                      <li><code>var:myVariable</code> - Find variable usage</li>
                      <li><code>file:myFile.py</code> - Filter by file</li>
                      <li><code>event:function_call</code> - Filter by event type</li>
                    </ul>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};