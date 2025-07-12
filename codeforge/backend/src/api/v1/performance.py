"""
Performance Monitoring API endpoints for CodeForge
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from datetime import datetime

from ...services.performance_service import PerformanceService, MetricType
from ...auth.dependencies import get_current_user
from ...models.user import User


router = APIRouter(prefix="/performance", tags=["performance"])

# Shared performance service instance
performance_service = PerformanceService()


class MetricRecordRequest(BaseModel):
    metric_type: str
    value: float
    unit: str
    labels: Dict[str, str] = {}


class MetricsQuery(BaseModel):
    metric_types: Optional[List[str]] = None
    time_range: Optional[int] = 60  # minutes
    labels: Optional[Dict[str, str]] = None


class AggregationQuery(BaseModel):
    metric_type: str
    aggregation: str = "avg"  # avg, min, max, sum, count
    time_range: int = 60  # minutes
    group_by: Optional[str] = None


@router.post("/metrics/record")
async def record_metric(
    request: MetricRecordRequest,
    current_user: User = Depends(get_current_user)
):
    """Record a new metric data point"""
    try:
        # Validate metric type
        metric_type = MetricType(request.metric_type)
        
        await performance_service.record_metric(
            metric_type=metric_type,
            value=request.value,
            unit=request.unit,
            labels=request.labels
        )
        
        return {"success": True, "message": "Metric recorded successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric type: {request.metric_type}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record metric: {str(e)}"
        )


@router.get("/metrics")
async def get_metrics(
    metric_types: Optional[str] = Query(None, description="Comma-separated metric types"),
    time_range: Optional[int] = Query(60, description="Time range in minutes"),
    labels: Optional[str] = Query(None, description="JSON string of label filters"),
    current_user: User = Depends(get_current_user)
):
    """Get metrics with optional filtering"""
    try:
        # Parse metric types
        parsed_metric_types = None
        if metric_types:
            parsed_metric_types = [MetricType(mt.strip()) for mt in metric_types.split(",")]
        
        # Parse labels
        parsed_labels = None
        if labels:
            import json
            parsed_labels = json.loads(labels)
        
        metrics = await performance_service.get_metrics(
            metric_types=parsed_metric_types,
            time_range=time_range,
            labels=parsed_labels
        )
        
        return {
            "metrics": metrics,
            "count": len(metrics),
            "time_range": time_range
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameter: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.post("/metrics/aggregate")
async def get_aggregated_metrics(
    query: AggregationQuery,
    current_user: User = Depends(get_current_user)
):
    """Get aggregated metrics"""
    try:
        metric_type = MetricType(query.metric_type)
        
        result = await performance_service.get_aggregated_metrics(
            metric_type=metric_type,
            aggregation=query.aggregation,
            time_range=query.time_range,
            group_by=query.group_by
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric type: {query.metric_type}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to aggregate metrics: {str(e)}"
        )


@router.get("/health")
async def get_system_health(
    current_user: User = Depends(get_current_user)
):
    """Get overall system health status"""
    try:
        health = await performance_service.get_system_health()
        return health
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system health: {str(e)}"
        )


@router.get("/insights")
async def get_performance_insights(
    current_user: User = Depends(get_current_user)
):
    """Get performance insights and recommendations"""
    try:
        insights = await performance_service.get_performance_insights()
        return {
            "insights": insights,
            "count": len(insights)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get insights: {str(e)}"
        )


@router.get("/alerts")
async def get_alerts(
    include_resolved: bool = Query(False, description="Include resolved alerts"),
    current_user: User = Depends(get_current_user)
):
    """Get performance alerts"""
    try:
        alerts = await performance_service.get_alerts(include_resolved=include_resolved)
        return {
            "alerts": alerts,
            "count": len(alerts)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alerts: {str(e)}"
        )


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user)
):
    """Resolve a performance alert"""
    try:
        success = await performance_service.resolve_alert(alert_id)
        
        if success:
            return {"success": True, "message": "Alert resolved successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found or already resolved"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve alert: {str(e)}"
        )


@router.get("/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive performance dashboard data"""
    try:
        dashboard_data = await performance_service.get_performance_dashboard_data()
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard data: {str(e)}"
        )


@router.get("/metrics/types")
async def get_metric_types(
    current_user: User = Depends(get_current_user)
):
    """Get available metric types"""
    return {
        "metric_types": [
            {
                "id": metric_type.value,
                "name": metric_type.value.replace("_", " ").title(),
                "description": _get_metric_description(metric_type)
            }
            for metric_type in MetricType
        ]
    }


def _get_metric_description(metric_type: MetricType) -> str:
    """Get description for metric type"""
    descriptions = {
        MetricType.SYSTEM_CPU: "System CPU usage percentage",
        MetricType.SYSTEM_MEMORY: "System memory usage percentage", 
        MetricType.SYSTEM_DISK: "System disk usage percentage",
        MetricType.CONTAINER_CPU: "Container CPU usage percentage",
        MetricType.CONTAINER_MEMORY: "Container memory usage percentage",
        MetricType.PROJECT_BUILD_TIME: "Project build time in milliseconds",
        MetricType.PROJECT_DEPLOY_TIME: "Project deployment time in milliseconds",
        MetricType.API_RESPONSE_TIME: "API response time in milliseconds",
        MetricType.AI_REQUEST_TIME: "AI request processing time in milliseconds",
        MetricType.COLLABORATION_LATENCY: "Real-time collaboration latency in milliseconds",
        MetricType.USER_SESSION_DURATION: "User session duration in seconds"
    }
    return descriptions.get(metric_type, "Unknown metric type")


@router.get("/system/stats")
async def get_system_stats(
    current_user: User = Depends(get_current_user)
):
    """Get detailed system statistics"""
    try:
        import psutil
        import docker
        
        docker_client = docker.from_env()
        
        # System stats
        cpu_count = psutil.cpu_count()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Container stats
        containers = docker_client.containers.list()
        codeforge_containers = [c for c in containers if 'codeforge' in c.name]
        
        return {
            "system": {
                "cpu_count": cpu_count,
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "uptime_seconds": performance_service.start_time
            },
            "containers": {
                "total": len(containers),
                "codeforge": len(codeforge_containers),
                "running": len([c for c in codeforge_containers if c.status == 'running'])
            },
            "performance": {
                "total_metrics": len(performance_service.metrics),
                "active_alerts": len([a for a in performance_service.alerts if a.resolved_at is None]),
                "total_alerts": len(performance_service.alerts)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system stats: {str(e)}"
        )


@router.get("/export")
async def export_metrics(
    format: str = Query("json", description="Export format: json, csv"),
    time_range: int = Query(1440, description="Time range in minutes (default: 24 hours)"),
    current_user: User = Depends(get_current_user)
):
    """Export metrics data"""
    try:
        metrics = await performance_service.get_metrics(time_range=time_range)
        
        if format.lower() == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(["timestamp", "metric_type", "value", "unit", "labels"])
            
            # Write data
            for metric in metrics:
                labels_str = ",".join([f"{k}={v}" for k, v in metric.get("labels", {}).items()])
                writer.writerow([
                    metric["timestamp"],
                    metric["metric_type"],
                    metric["value"],
                    metric["unit"],
                    labels_str
                ])
            
            return {
                "format": "csv",
                "data": output.getvalue(),
                "count": len(metrics)
            }
        
        else:  # JSON format
            return {
                "format": "json",
                "data": metrics,
                "count": len(metrics),
                "time_range": time_range
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export metrics: {str(e)}"
        )