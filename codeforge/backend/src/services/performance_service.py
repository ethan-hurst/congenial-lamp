"""
Performance Monitoring Service
Real-time metrics and analytics for CodeForge
"""
import asyncio
import time
import psutil
import docker
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json

from ..config.settings import settings


class MetricType(str, Enum):
    """Types of metrics we track"""
    SYSTEM_CPU = "system_cpu"
    SYSTEM_MEMORY = "system_memory"
    SYSTEM_DISK = "system_disk"
    CONTAINER_CPU = "container_cpu"
    CONTAINER_MEMORY = "container_memory"
    PROJECT_BUILD_TIME = "project_build_time"
    PROJECT_DEPLOY_TIME = "project_deploy_time"
    API_RESPONSE_TIME = "api_response_time"
    AI_REQUEST_TIME = "ai_request_time"
    COLLABORATION_LATENCY = "collaboration_latency"
    USER_SESSION_DURATION = "user_session_duration"


@dataclass
class MetricEntry:
    """Single metric data point"""
    timestamp: datetime
    metric_type: MetricType
    value: float
    unit: str
    labels: Dict[str, str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}


@dataclass
class PerformanceAlert:
    """Performance alert"""
    id: str
    metric_type: MetricType
    threshold: float
    current_value: float
    severity: str  # low, medium, high, critical
    message: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    
    
@dataclass
class SystemHealth:
    """Overall system health status"""
    status: str  # healthy, degraded, critical
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_containers: int
    active_users: int
    api_latency_p95: float
    uptime_seconds: float
    alerts_count: int


class PerformanceService:
    """
    Performance monitoring and analytics service
    """
    
    def __init__(self):
        self.metrics: List[MetricEntry] = []
        self.alerts: List[PerformanceAlert] = []
        self.docker_client = docker.from_env()
        self.start_time = time.time()
        
        # Metric thresholds for alerts
        self.thresholds = {
            MetricType.SYSTEM_CPU: 80.0,  # 80% CPU usage
            MetricType.SYSTEM_MEMORY: 85.0,  # 85% memory usage
            MetricType.SYSTEM_DISK: 90.0,  # 90% disk usage
            MetricType.API_RESPONSE_TIME: 2000.0,  # 2 second response time
            MetricType.AI_REQUEST_TIME: 10000.0,  # 10 second AI response
            MetricType.PROJECT_BUILD_TIME: 300000.0,  # 5 minute build time
        }
        
        # Start background monitoring
        asyncio.create_task(self._monitor_system_metrics())
    
    async def record_metric(
        self,
        metric_type: MetricType,
        value: float,
        unit: str,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a new metric data point"""
        metric = MetricEntry(
            timestamp=datetime.now(timezone.utc),
            metric_type=metric_type,
            value=value,
            unit=unit,
            labels=labels or {}
        )
        
        self.metrics.append(metric)
        
        # Keep only last 24 hours of metrics
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        self.metrics = [m for m in self.metrics if m.timestamp > cutoff]
        
        # Check for alert conditions
        await self._check_alert_thresholds(metric)
    
    async def _check_alert_thresholds(self, metric: MetricEntry) -> None:
        """Check if metric triggers any alerts"""
        threshold = self.thresholds.get(metric.metric_type)
        if not threshold:
            return
        
        if metric.value > threshold:
            # Check if we already have an active alert for this metric
            active_alerts = [
                a for a in self.alerts 
                if a.metric_type == metric.metric_type and a.resolved_at is None
            ]
            
            if not active_alerts:
                # Create new alert
                alert = PerformanceAlert(
                    id=f"alert_{int(time.time())}_{metric.metric_type}",
                    metric_type=metric.metric_type,
                    threshold=threshold,
                    current_value=metric.value,
                    severity=self._get_alert_severity(metric.value, threshold),
                    message=f"{metric.metric_type} exceeded threshold: {metric.value:.2f}{metric.unit} > {threshold}{metric.unit}",
                    created_at=datetime.now(timezone.utc)
                )
                self.alerts.append(alert)
    
    def _get_alert_severity(self, value: float, threshold: float) -> str:
        """Determine alert severity based on how much threshold is exceeded"""
        ratio = value / threshold
        if ratio >= 2.0:
            return "critical"
        elif ratio >= 1.5:
            return "high"
        elif ratio >= 1.2:
            return "medium"
        else:
            return "low"
    
    async def _monitor_system_metrics(self) -> None:
        """Background task to monitor system metrics"""
        while True:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                await self.record_metric(
                    MetricType.SYSTEM_CPU,
                    cpu_percent,
                    "%",
                    {"host": "main"}
                )
                
                # Memory usage
                memory = psutil.virtual_memory()
                await self.record_metric(
                    MetricType.SYSTEM_MEMORY,
                    memory.percent,
                    "%",
                    {"host": "main"}
                )
                
                # Disk usage
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                await self.record_metric(
                    MetricType.SYSTEM_DISK,
                    disk_percent,
                    "%",
                    {"host": "main", "mount": "/"}
                )
                
                # Container metrics
                await self._monitor_container_metrics()
                
                # Wait before next collection
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                print(f"Error monitoring system metrics: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _monitor_container_metrics(self) -> None:
        """Monitor Docker container metrics"""
        try:
            containers = self.docker_client.containers.list()
            
            for container in containers:
                if 'codeforge' in container.name:
                    stats = container.stats(stream=False)
                    
                    # CPU usage
                    cpu_usage = self._calculate_cpu_percent(stats)
                    await self.record_metric(
                        MetricType.CONTAINER_CPU,
                        cpu_usage,
                        "%",
                        {"container": container.name, "container_id": container.id[:12]}
                    )
                    
                    # Memory usage
                    memory_usage = self._calculate_memory_percent(stats)
                    await self.record_metric(
                        MetricType.CONTAINER_MEMORY,
                        memory_usage,
                        "%",
                        {"container": container.name, "container_id": container.id[:12]}
                    )
                    
        except Exception as e:
            print(f"Error monitoring container metrics: {e}")
    
    def _calculate_cpu_percent(self, stats: Dict) -> float:
        """Calculate CPU percentage from Docker stats"""
        try:
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            
            if system_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100
                return round(cpu_percent, 2)
        except (KeyError, ZeroDivisionError):
            pass
        return 0.0
    
    def _calculate_memory_percent(self, stats: Dict) -> float:
        """Calculate memory percentage from Docker stats"""
        try:
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            if memory_limit > 0:
                return round((memory_usage / memory_limit) * 100, 2)
        except KeyError:
            pass
        return 0.0
    
    async def get_metrics(
        self,
        metric_types: Optional[List[MetricType]] = None,
        time_range: Optional[int] = None,  # minutes
        labels: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Get metrics with optional filtering"""
        filtered_metrics = self.metrics
        
        # Filter by time range
        if time_range:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=time_range)
            filtered_metrics = [m for m in filtered_metrics if m.timestamp > cutoff]
        
        # Filter by metric types
        if metric_types:
            filtered_metrics = [m for m in filtered_metrics if m.metric_type in metric_types]
        
        # Filter by labels
        if labels:
            filtered_metrics = [
                m for m in filtered_metrics
                if all(m.labels.get(k) == v for k, v in labels.items())
            ]
        
        return [asdict(metric) for metric in filtered_metrics]
    
    async def get_aggregated_metrics(
        self,
        metric_type: MetricType,
        aggregation: str = "avg",  # avg, min, max, sum, count
        time_range: int = 60,  # minutes
        group_by: Optional[str] = None  # group by label key
    ) -> Dict[str, Any]:
        """Get aggregated metrics"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=time_range)
        metrics = [
            m for m in self.metrics
            if m.metric_type == metric_type and m.timestamp > cutoff
        ]
        
        if not metrics:
            return {"aggregation": aggregation, "value": 0, "count": 0}
        
        values = [m.value for m in metrics]
        
        if aggregation == "avg":
            result = sum(values) / len(values)
        elif aggregation == "min":
            result = min(values)
        elif aggregation == "max":
            result = max(values)
        elif aggregation == "sum":
            result = sum(values)
        elif aggregation == "count":
            result = len(values)
        else:
            result = sum(values) / len(values)  # default to avg
        
        return {
            "aggregation": aggregation,
            "value": round(result, 2),
            "count": len(values),
            "time_range": time_range,
            "metric_type": metric_type
        }
    
    async def get_system_health(self) -> SystemHealth:
        """Get overall system health status"""
        now = datetime.now(timezone.utc)
        last_5_min = now - timedelta(minutes=5)
        
        # Get recent metrics
        recent_metrics = [m for m in self.metrics if m.timestamp > last_5_min]
        
        # Calculate averages
        cpu_metrics = [m.value for m in recent_metrics if m.metric_type == MetricType.SYSTEM_CPU]
        memory_metrics = [m.value for m in recent_metrics if m.metric_type == MetricType.SYSTEM_MEMORY]
        disk_metrics = [m.value for m in recent_metrics if m.metric_type == MetricType.SYSTEM_DISK]
        
        cpu_usage = sum(cpu_metrics) / len(cpu_metrics) if cpu_metrics else 0
        memory_usage = sum(memory_metrics) / len(memory_metrics) if memory_metrics else 0
        disk_usage = sum(disk_metrics) / len(disk_metrics) if disk_metrics else 0
        
        # Count active containers
        try:
            active_containers = len([
                c for c in self.docker_client.containers.list()
                if 'codeforge' in c.name
            ])
        except:
            active_containers = 0
        
        # API latency (simulated for now)
        api_metrics = [m.value for m in recent_metrics if m.metric_type == MetricType.API_RESPONSE_TIME]
        api_latency_p95 = max(api_metrics) if api_metrics else 0
        
        # Count unresolved alerts
        unresolved_alerts = len([a for a in self.alerts if a.resolved_at is None])
        
        # Determine overall status
        status = "healthy"
        if cpu_usage > 90 or memory_usage > 90 or disk_usage > 95 or unresolved_alerts > 5:
            status = "critical"
        elif cpu_usage > 80 or memory_usage > 80 or disk_usage > 90 or unresolved_alerts > 2:
            status = "degraded"
        
        return SystemHealth(
            status=status,
            cpu_usage=round(cpu_usage, 2),
            memory_usage=round(memory_usage, 2),
            disk_usage=round(disk_usage, 2),
            active_containers=active_containers,
            active_users=0,  # TODO: Get from user session service
            api_latency_p95=round(api_latency_p95, 2),
            uptime_seconds=round(time.time() - self.start_time, 2),
            alerts_count=unresolved_alerts
        )
    
    async def get_performance_insights(self) -> List[Dict[str, Any]]:
        """Get performance insights and recommendations"""
        insights = []
        
        # Analyze recent performance
        now = datetime.now(timezone.utc)
        last_hour = now - timedelta(hours=1)
        recent_metrics = [m for m in self.metrics if m.timestamp > last_hour]
        
        # CPU analysis
        cpu_metrics = [m.value for m in recent_metrics if m.metric_type == MetricType.SYSTEM_CPU]
        if cpu_metrics:
            avg_cpu = sum(cpu_metrics) / len(cpu_metrics)
            if avg_cpu > 70:
                insights.append({
                    "type": "performance",
                    "severity": "medium" if avg_cpu < 85 else "high",
                    "title": "High CPU Usage",
                    "description": f"Average CPU usage is {avg_cpu:.1f}% over the last hour",
                    "recommendation": "Consider scaling up resources or optimizing workloads",
                    "metric_type": MetricType.SYSTEM_CPU,
                    "value": avg_cpu
                })
        
        # Memory analysis
        memory_metrics = [m.value for m in recent_metrics if m.metric_type == MetricType.SYSTEM_MEMORY]
        if memory_metrics:
            avg_memory = sum(memory_metrics) / len(memory_metrics)
            if avg_memory > 75:
                insights.append({
                    "type": "performance",
                    "severity": "medium" if avg_memory < 90 else "high",
                    "title": "High Memory Usage",
                    "description": f"Average memory usage is {avg_memory:.1f}% over the last hour",
                    "recommendation": "Monitor memory leaks and consider adding more RAM",
                    "metric_type": MetricType.SYSTEM_MEMORY,
                    "value": avg_memory
                })
        
        # Build time analysis
        build_metrics = [m.value for m in recent_metrics if m.metric_type == MetricType.PROJECT_BUILD_TIME]
        if build_metrics:
            avg_build_time = sum(build_metrics) / len(build_metrics)
            if avg_build_time > 120000:  # 2 minutes
                insights.append({
                    "type": "optimization",
                    "severity": "low",
                    "title": "Slow Build Times",
                    "description": f"Average build time is {avg_build_time/1000:.1f} seconds",
                    "recommendation": "Consider optimizing build cache and dependencies",
                    "metric_type": MetricType.PROJECT_BUILD_TIME,
                    "value": avg_build_time
                })
        
        return insights
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        for alert in self.alerts:
            if alert.id == alert_id and alert.resolved_at is None:
                alert.resolved_at = datetime.now(timezone.utc)
                return True
        return False
    
    async def get_alerts(self, include_resolved: bool = False) -> List[Dict[str, Any]]:
        """Get alerts"""
        alerts = self.alerts
        if not include_resolved:
            alerts = [a for a in alerts if a.resolved_at is None]
        
        return [asdict(alert) for alert in alerts]
    
    async def get_performance_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        return {
            "system_health": asdict(await self.get_system_health()),
            "recent_metrics": {
                "cpu": await self.get_aggregated_metrics(MetricType.SYSTEM_CPU, "avg", 60),
                "memory": await self.get_aggregated_metrics(MetricType.SYSTEM_MEMORY, "avg", 60),
                "disk": await self.get_aggregated_metrics(MetricType.SYSTEM_DISK, "avg", 60),
                "api_latency": await self.get_aggregated_metrics(MetricType.API_RESPONSE_TIME, "p95", 60),
            },
            "alerts": await self.get_alerts(),
            "insights": await self.get_performance_insights(),
            "uptime": time.time() - self.start_time
        }