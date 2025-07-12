"""
CodeForge Usage Calculator - Real-time compute usage tracking
Tracks CPU, RAM, GPU, bandwidth usage and calculates credits in real-time
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from decimal import Decimal
import psutil
import docker
from dataclasses import dataclass
from collections import defaultdict

from ..config.settings import settings
from ..models.usage import ResourceUsage, UsageSnapshot
from ..services.credits_service import CreditsService


@dataclass
class ResourceMetrics:
    """Container resource metrics snapshot"""
    cpu_percent: float
    memory_mb: float
    disk_read_mb: float
    disk_write_mb: float
    network_rx_mb: float
    network_tx_mb: float
    gpu_percent: Optional[float] = None
    gpu_memory_mb: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class UsageCalculator:
    """
    Real-time compute usage tracking and credit calculation
    Features:
    - Sub-second resource monitoring
    - Smart idle detection (auto-sleep after 5 min)
    - GPU usage tracking
    - Bandwidth monitoring
    - Predictive credit warnings
    """
    
    # Idle thresholds
    IDLE_CPU_THRESHOLD = 1.0  # 1% CPU usage
    IDLE_MEMORY_THRESHOLD = 100  # 100MB active memory
    IDLE_TIMEOUT_SECONDS = 300  # 5 minutes
    
    # Sampling rates
    SAMPLE_INTERVAL_SECONDS = 1.0  # Sample every second
    AGGREGATE_INTERVAL_SECONDS = 60  # Aggregate every minute
    
    def __init__(self, docker_client=None):
        self.docker = docker_client or docker.from_env()
        self.active_sessions: Dict[str, Dict] = {}
        self.usage_history: Dict[str, List[ResourceMetrics]] = defaultdict(list)
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        
    async def start_tracking(
        self, 
        session_id: str, 
        container_id: str,
        user_id: str,
        project_id: str,
        environment_type: str = "development"
    ):
        """Start tracking resource usage for a container"""
        self.active_sessions[session_id] = {
            "container_id": container_id,
            "user_id": user_id,
            "project_id": project_id,
            "environment_type": environment_type,
            "start_time": datetime.utcnow(),
            "last_active": datetime.utcnow(),
            "total_credits_used": 0,
            "is_idle": False
        }
        
        # Start monitoring task
        task = asyncio.create_task(
            self._monitor_container(session_id, container_id)
        )
        self.monitoring_tasks[session_id] = task
        
    async def stop_tracking(self, session_id: str) -> Dict:
        """Stop tracking and return final usage summary"""
        if session_id not in self.active_sessions:
            return {}
            
        # Cancel monitoring task
        if session_id in self.monitoring_tasks:
            self.monitoring_tasks[session_id].cancel()
            try:
                await self.monitoring_tasks[session_id]
            except asyncio.CancelledError:
                pass
            del self.monitoring_tasks[session_id]
            
        # Calculate final usage
        session = self.active_sessions[session_id]
        duration = (datetime.utcnow() - session["start_time"]).total_seconds()
        
        summary = {
            "session_id": session_id,
            "duration_seconds": duration,
            "total_credits_used": session["total_credits_used"],
            "average_cpu": self._calculate_average_metric(session_id, "cpu_percent"),
            "average_memory_mb": self._calculate_average_metric(session_id, "memory_mb"),
            "total_bandwidth_mb": self._calculate_total_bandwidth(session_id),
            "environment_type": session["environment_type"]
        }
        
        # Cleanup
        del self.active_sessions[session_id]
        if session_id in self.usage_history:
            del self.usage_history[session_id]
            
        return summary
        
    async def _monitor_container(self, session_id: str, container_id: str):
        """Monitor container resources in real-time"""
        while session_id in self.active_sessions:
            try:
                # Get container
                container = self.docker.containers.get(container_id)
                if container.status != "running":
                    break
                    
                # Collect metrics
                metrics = await self._collect_metrics(container)
                
                # Store metrics
                self.usage_history[session_id].append(metrics)
                
                # Check for idle state
                await self._check_idle_state(session_id, metrics)
                
                # Calculate credits used in this interval
                if not self.active_sessions[session_id]["is_idle"]:
                    credits = self._calculate_interval_credits(metrics)
                    self.active_sessions[session_id]["total_credits_used"] += credits
                    
                # Cleanup old history (keep last 5 minutes)
                cutoff_time = datetime.utcnow() - timedelta(minutes=5)
                self.usage_history[session_id] = [
                    m for m in self.usage_history[session_id]
                    if m.timestamp > cutoff_time
                ]
                
                # Sleep until next sample
                await asyncio.sleep(self.SAMPLE_INTERVAL_SECONDS)
                
            except docker.errors.NotFound:
                # Container was removed
                break
            except Exception as e:
                # Log error but continue monitoring
                print(f"Monitoring error for {session_id}: {e}")
                await asyncio.sleep(self.SAMPLE_INTERVAL_SECONDS)
                
    async def _collect_metrics(self, container) -> ResourceMetrics:
        """Collect resource metrics from container"""
        stats = container.stats(stream=False)
        
        # CPU calculation
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                   stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                      stats["precpu_stats"]["system_cpu_usage"]
        cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0
        
        # Memory calculation
        memory_usage = stats["memory_stats"]["usage"]
        memory_mb = memory_usage / (1024 * 1024)
        
        # Disk I/O
        disk_read_mb = 0
        disk_write_mb = 0
        if "blkio_stats" in stats:
            for stat in stats["blkio_stats"]["io_service_bytes_recursive"] or []:
                if stat["op"] == "Read":
                    disk_read_mb += stat["value"] / (1024 * 1024)
                elif stat["op"] == "Write":
                    disk_write_mb += stat["value"] / (1024 * 1024)
                    
        # Network I/O
        network_rx_mb = 0
        network_tx_mb = 0
        if "networks" in stats:
            for interface in stats["networks"].values():
                network_rx_mb += interface["rx_bytes"] / (1024 * 1024)
                network_tx_mb += interface["tx_bytes"] / (1024 * 1024)
                
        # GPU metrics (if available)
        gpu_percent = None
        gpu_memory_mb = None
        # GPU monitoring would require nvidia-docker and nvidia-ml-py
        
        return ResourceMetrics(
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            disk_read_mb=disk_read_mb,
            disk_write_mb=disk_write_mb,
            network_rx_mb=network_rx_mb,
            network_tx_mb=network_tx_mb,
            gpu_percent=gpu_percent,
            gpu_memory_mb=gpu_memory_mb
        )
        
    async def _check_idle_state(self, session_id: str, metrics: ResourceMetrics):
        """Check if container is idle and should stop charging credits"""
        session = self.active_sessions[session_id]
        
        # Check if resources are below idle thresholds
        is_idle = (
            metrics.cpu_percent < self.IDLE_CPU_THRESHOLD and
            metrics.memory_mb < self.IDLE_MEMORY_THRESHOLD
        )
        
        if is_idle:
            # Check if it's been idle for timeout period
            if not session["is_idle"]:
                idle_duration = (datetime.utcnow() - session["last_active"]).total_seconds()
                if idle_duration >= self.IDLE_TIMEOUT_SECONDS:
                    session["is_idle"] = True
                    # Could trigger auto-sleep here
        else:
            # Container is active
            session["is_idle"] = False
            session["last_active"] = datetime.utcnow()
            
    def _calculate_interval_credits(self, metrics: ResourceMetrics) -> float:
        """Calculate credits used in sampling interval"""
        interval_hours = self.SAMPLE_INTERVAL_SECONDS / 3600
        
        # CPU credits (based on percentage of allocated cores)
        cpu_cores = metrics.cpu_percent / 100  # Convert percentage to cores
        cpu_credits = cpu_cores * interval_hours * settings.CREDITS_PER_CPU_HOUR
        
        # Memory credits
        memory_gb = metrics.memory_mb / 1024
        memory_credits = memory_gb * interval_hours * settings.CREDITS_PER_GB_RAM_HOUR
        
        # GPU credits (if applicable)
        gpu_credits = 0
        if metrics.gpu_percent is not None:
            gpu_multiplier = 10  # GPU is 10x more expensive
            gpu_credits = (metrics.gpu_percent / 100) * interval_hours * \
                         settings.CREDITS_PER_CPU_HOUR * gpu_multiplier
                         
        return cpu_credits + memory_credits + gpu_credits
        
    def _calculate_average_metric(self, session_id: str, metric_name: str) -> float:
        """Calculate average value for a metric"""
        if session_id not in self.usage_history:
            return 0
            
        values = [getattr(m, metric_name) for m in self.usage_history[session_id]]
        return sum(values) / len(values) if values else 0
        
    def _calculate_total_bandwidth(self, session_id: str) -> float:
        """Calculate total bandwidth used"""
        if session_id not in self.usage_history:
            return 0
            
        total = 0
        for metric in self.usage_history[session_id]:
            total += metric.network_rx_mb + metric.network_tx_mb
            
        return total
        
    async def get_current_usage(self, session_id: str) -> Optional[Dict]:
        """Get current usage statistics for active session"""
        if session_id not in self.active_sessions:
            return None
            
        session = self.active_sessions[session_id]
        recent_metrics = self.usage_history[session_id][-10:] if session_id in self.usage_history else []
        
        if not recent_metrics:
            return None
            
        latest = recent_metrics[-1]
        
        return {
            "session_id": session_id,
            "is_idle": session["is_idle"],
            "current_cpu_percent": latest.cpu_percent,
            "current_memory_mb": latest.memory_mb,
            "credits_used_so_far": session["total_credits_used"],
            "credits_per_hour_rate": self._estimate_hourly_rate(recent_metrics),
            "uptime_seconds": (datetime.utcnow() - session["start_time"]).total_seconds()
        }
        
    def _estimate_hourly_rate(self, recent_metrics: List[ResourceMetrics]) -> float:
        """Estimate credits per hour based on recent usage"""
        if not recent_metrics:
            return 0
            
        # Average the last few samples
        total_credits = 0
        for metric in recent_metrics:
            total_credits += self._calculate_interval_credits(metric)
            
        # Scale to hourly rate
        samples_per_hour = 3600 / self.SAMPLE_INTERVAL_SECONDS
        return (total_credits / len(recent_metrics)) * samples_per_hour
        
    async def predict_credits_remaining(
        self, 
        session_id: str, 
        available_credits: int
    ) -> Optional[Dict]:
        """Predict how long current session can run with available credits"""
        current_usage = await self.get_current_usage(session_id)
        if not current_usage:
            return None
            
        hourly_rate = current_usage["credits_per_hour_rate"]
        if hourly_rate <= 0:
            return {"hours_remaining": float('inf'), "warning": None}
            
        hours_remaining = available_credits / hourly_rate
        
        warning = None
        if hours_remaining < 1:
            warning = "Less than 1 hour of credits remaining"
        elif hours_remaining < 4:
            warning = f"Only {hours_remaining:.1f} hours of credits remaining"
            
        return {
            "hours_remaining": hours_remaining,
            "minutes_remaining": hours_remaining * 60,
            "warning": warning
        }
        
    def get_environment_multiplier(self, environment_type: str) -> float:
        """Get credit multiplier based on environment type"""
        multipliers = {
            "development": 0.0,  # Free for development!
            "staging": 0.5,      # 50% discount for staging
            "production": 1.0,   # Full price for production
            "gpu": 5.0,         # GPU environments cost more
            "high-memory": 2.0   # High memory environments
        }
        return multipliers.get(environment_type, 1.0)