"""
AI Agent Success Metrics and Analytics
Tracks performance, quality, and success metrics for AI agents
"""
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import logging

from ...models.ai_agent import (
    AgentTask, AgentWorkflow, AgentArtifact, 
    TaskStatus, AgentType, WorkflowType
)
from ...models.user import User

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """
    Calculates various success metrics for AI agents
    """
    
    @staticmethod
    def calculate_success_rate(tasks: List[AgentTask]) -> float:
        """Calculate success rate from completed tasks"""
        if not tasks:
            return 0.0
        
        completed_tasks = [t for t in tasks if t.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]]
        if not completed_tasks:
            return 0.0
        
        successful_tasks = [t for t in completed_tasks if t.status == TaskStatus.COMPLETED.value]
        return len(successful_tasks) / len(completed_tasks)
    
    @staticmethod
    def calculate_average_execution_time(tasks: List[AgentTask]) -> float:
        """Calculate average execution time in seconds"""
        completed_tasks = [
            t for t in tasks 
            if t.status == TaskStatus.COMPLETED.value and t.started_at and t.completed_at
        ]
        
        if not completed_tasks:
            return 0.0
        
        total_time = sum(
            (t.completed_at - t.started_at).total_seconds() 
            for t in completed_tasks
        )
        
        return total_time / len(completed_tasks)
    
    @staticmethod
    def calculate_code_quality_score(artifacts: List[AgentArtifact]) -> float:
        """Calculate code quality score based on artifacts"""
        if not artifacts:
            return 0.0
        
        total_score = 0.0
        scored_artifacts = 0
        
        for artifact in artifacts:
            if artifact.artifact_type == "code" and artifact.content:
                score = MetricsCalculator._evaluate_code_quality(artifact.content, artifact.language)
                total_score += score
                scored_artifacts += 1
        
        return total_score / scored_artifacts if scored_artifacts > 0 else 0.0
    
    @staticmethod
    def _evaluate_code_quality(content: str, language: str = "python") -> float:
        """Evaluate code quality for a single file"""
        if not content:
            return 0.0
        
        score = 1.0
        lines = content.split('\n')
        
        # Basic quality checks
        if language == "python":
            # Check for docstrings
            if '"""' in content or "'''" in content:
                score += 0.2
            
            # Check for type hints
            if ': ' in content and '->' in content:
                score += 0.1
            
            # Check for error handling
            if 'try:' in content and 'except' in content:
                score += 0.1
            
            # Penalize very long functions
            function_lines = 0
            in_function = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('def '):
                    if in_function and function_lines > 50:
                        score -= 0.1
                    function_lines = 0
                    in_function = True
                elif in_function:
                    function_lines += 1
        
        # General checks
        # Check for comments
        comment_lines = len([line for line in lines if line.strip().startswith('#')])
        if comment_lines > 0:
            score += min(0.2, comment_lines / len(lines))
        
        # Check line length (penalize very long lines)
        long_lines = len([line for line in lines if len(line) > 120])
        if long_lines > 0:
            score -= min(0.2, long_lines / len(lines))
        
        return max(0.0, min(2.0, score))
    
    @staticmethod
    def calculate_user_satisfaction_proxy(tasks: List[AgentTask]) -> float:
        """Calculate user satisfaction proxy based on task patterns"""
        if not tasks:
            return 0.0
        
        # Factors that indicate satisfaction:
        # 1. High success rate
        # 2. Quick completion times
        # 3. High confidence scores
        # 4. Low cancellation rate
        
        success_rate = MetricsCalculator.calculate_success_rate(tasks)
        
        # Cancellation rate (negative indicator)
        cancelled_tasks = [t for t in tasks if t.status == TaskStatus.CANCELLED.value]
        cancellation_rate = len(cancelled_tasks) / len(tasks) if tasks else 0
        
        # Average confidence
        confidence_scores = [
            t.confidence_score for t in tasks 
            if t.confidence_score is not None and t.status == TaskStatus.COMPLETED.value
        ]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
        
        # Weighted satisfaction score
        satisfaction = (
            success_rate * 0.4 +
            (1 - cancellation_rate) * 0.3 +
            avg_confidence * 0.3
        )
        
        return satisfaction


class AgentAnalytics:
    """
    Comprehensive analytics for AI agent performance
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_agent_performance_summary(
        self,
        agent_type: Optional[AgentType] = None,
        time_range_days: int = 30,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive performance summary for agents
        
        Args:
            agent_type: Specific agent type to analyze
            time_range_days: Number of days to look back
            user_id: Optional user filter
            
        Returns:
            Performance summary with metrics
        """
        
        # Build query
        query = self.db.query(AgentTask)
        
        # Apply filters
        if agent_type:
            query = query.filter(AgentTask.agent_type == agent_type.value)
        
        if user_id:
            query = query.filter(AgentTask.user_id == user_id)
        
        if time_range_days > 0:
            cutoff_date = datetime.utcnow() - timedelta(days=time_range_days)
            query = query.filter(AgentTask.created_at >= cutoff_date)
        
        tasks = query.all()
        
        # Calculate metrics
        total_tasks = len(tasks)
        success_rate = MetricsCalculator.calculate_success_rate(tasks)
        avg_execution_time = MetricsCalculator.calculate_average_execution_time(tasks)
        satisfaction_proxy = MetricsCalculator.calculate_user_satisfaction_proxy(tasks)
        
        # Status breakdown
        status_counts = {}
        for status in TaskStatus:
            count = len([t for t in tasks if t.status == status.value])
            status_counts[status.value] = count
        
        # Complexity breakdown
        complexity_counts = {"low": 0, "medium": 0, "high": 0, "unknown": 0}
        for task in tasks:
            complexity = "unknown"
            if task.estimated_credits:
                if task.estimated_credits <= 20:
                    complexity = "low"
                elif task.estimated_credits <= 50:
                    complexity = "medium"
                else:
                    complexity = "high"
            complexity_counts[complexity] += 1
        
        # Get artifacts for quality analysis
        task_ids = [t.id for t in tasks]
        artifacts = self.db.query(AgentArtifact).filter(
            AgentArtifact.task_id.in_(task_ids)
        ).all() if task_ids else []
        
        code_quality_score = MetricsCalculator.calculate_code_quality_score(artifacts)
        
        # Calculate trends
        trends = await self._calculate_trends(agent_type, time_range_days, user_id)
        
        return {
            "summary": {
                "total_tasks": total_tasks,
                "success_rate": round(success_rate, 3),
                "average_execution_time_seconds": round(avg_execution_time, 1),
                "code_quality_score": round(code_quality_score, 2),
                "user_satisfaction_proxy": round(satisfaction_proxy, 3)
            },
            "status_breakdown": status_counts,
            "complexity_breakdown": complexity_counts,
            "trends": trends,
            "artifacts": {
                "total_files_generated": len(artifacts),
                "total_lines_of_code": sum(a.line_count or 0 for a in artifacts),
                "languages_used": list(set(a.language for a in artifacts if a.language))
            },
            "time_range_days": time_range_days,
            "agent_type": agent_type.value if agent_type else "all",
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def get_user_agent_usage(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get agent usage analytics for a specific user"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get user tasks
        tasks = self.db.query(AgentTask).filter(
            and_(
                AgentTask.user_id == user_id,
                AgentTask.created_at >= cutoff_date
            )
        ).all()
        
        # Get user workflows
        workflows = self.db.query(AgentWorkflow).filter(
            and_(
                AgentWorkflow.user_id == user_id,
                AgentWorkflow.created_at >= cutoff_date
            )
        ).all()
        
        # Agent type usage
        agent_usage = {}
        for agent_type in AgentType:
            agent_tasks = [t for t in tasks if t.agent_type == agent_type.value]
            agent_usage[agent_type.value] = {
                "tasks_count": len(agent_tasks),
                "success_rate": MetricsCalculator.calculate_success_rate(agent_tasks),
                "avg_execution_time": MetricsCalculator.calculate_average_execution_time(agent_tasks)
            }
        
        # Workflow usage
        workflow_usage = {}
        for workflow_type in WorkflowType:
            workflow_tasks = [w for w in workflows if w.workflow_type == workflow_type.value]
            workflow_usage[workflow_type.value] = len(workflow_tasks)
        
        # Daily usage pattern
        daily_usage = {}
        for task in tasks + workflows:
            day = task.created_at.date().isoformat()
            if day not in daily_usage:
                daily_usage[day] = 0
            daily_usage[day] += 1
        
        # Credits usage
        total_credits_used = sum(t.estimated_credits or 0 for t in tasks)
        
        return {
            "user_id": user_id,
            "time_period_days": days,
            "total_tasks": len(tasks),
            "total_workflows": len(workflows),
            "total_credits_used": total_credits_used,
            "agent_usage": agent_usage,
            "workflow_usage": workflow_usage,
            "daily_usage": daily_usage,
            "most_used_agent": max(agent_usage.items(), key=lambda x: x[1]["tasks_count"])[0] if agent_usage else None
        }
    
    async def get_system_wide_metrics(self, days: int = 7) -> Dict[str, Any]:
        """Get system-wide agent performance metrics"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Overall statistics
        total_tasks = self.db.query(AgentTask).filter(
            AgentTask.created_at >= cutoff_date
        ).count()
        
        total_workflows = self.db.query(AgentWorkflow).filter(
            AgentWorkflow.created_at >= cutoff_date
        ).count()
        
        total_users = self.db.query(func.count(func.distinct(AgentTask.user_id))).filter(
            AgentTask.created_at >= cutoff_date
        ).scalar()
        
        total_artifacts = self.db.query(AgentArtifact).join(AgentTask).filter(
            AgentTask.created_at >= cutoff_date
        ).count()
        
        # Performance metrics by agent type
        agent_performance = {}
        for agent_type in AgentType:
            tasks = self.db.query(AgentTask).filter(
                and_(
                    AgentTask.agent_type == agent_type.value,
                    AgentTask.created_at >= cutoff_date
                )
            ).all()
            
            agent_performance[agent_type.value] = {
                "total_tasks": len(tasks),
                "success_rate": MetricsCalculator.calculate_success_rate(tasks),
                "avg_execution_time": MetricsCalculator.calculate_average_execution_time(tasks)
            }
        
        # Peak usage hours
        hourly_usage = {}
        tasks = self.db.query(AgentTask).filter(
            AgentTask.created_at >= cutoff_date
        ).all()
        
        for task in tasks:
            hour = task.created_at.hour
            if hour not in hourly_usage:
                hourly_usage[hour] = 0
            hourly_usage[hour] += 1
        
        peak_hour = max(hourly_usage.items(), key=lambda x: x[1])[0] if hourly_usage else 0
        
        return {
            "system_overview": {
                "total_tasks": total_tasks,
                "total_workflows": total_workflows,
                "active_users": total_users,
                "total_artifacts_generated": total_artifacts,
                "time_period_days": days
            },
            "agent_performance": agent_performance,
            "usage_patterns": {
                "peak_hour": peak_hour,
                "hourly_distribution": hourly_usage
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def _calculate_trends(
        self,
        agent_type: Optional[AgentType],
        days: int,
        user_id: Optional[str]
    ) -> Dict[str, Any]:
        """Calculate trend data over time"""
        
        # Split time range into periods
        periods = min(7, days)  # Max 7 data points
        period_length = days // periods
        
        trends = {
            "success_rate": [],
            "task_count": [],
            "avg_execution_time": [],
            "periods": []
        }
        
        for i in range(periods):
            period_start = datetime.utcnow() - timedelta(days=days - (i * period_length))
            period_end = datetime.utcnow() - timedelta(days=days - ((i + 1) * period_length))
            
            # Build query for this period
            query = self.db.query(AgentTask).filter(
                and_(
                    AgentTask.created_at >= period_end,
                    AgentTask.created_at < period_start
                )
            )
            
            if agent_type:
                query = query.filter(AgentTask.agent_type == agent_type.value)
            
            if user_id:
                query = query.filter(AgentTask.user_id == user_id)
            
            period_tasks = query.all()
            
            trends["periods"].append(period_start.date().isoformat())
            trends["task_count"].append(len(period_tasks))
            trends["success_rate"].append(MetricsCalculator.calculate_success_rate(period_tasks))
            trends["avg_execution_time"].append(
                MetricsCalculator.calculate_average_execution_time(period_tasks)
            )
        
        return trends
    
    async def generate_performance_report(
        self,
        user_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        
        report = {
            "report_type": "performance_analysis",
            "generated_at": datetime.utcnow().isoformat(),
            "time_period_days": days,
            "user_id": user_id
        }
        
        if user_id:
            # User-specific report
            report["user_analytics"] = await self.get_user_agent_usage(user_id, days)
            
            # Per-agent performance for this user
            report["agent_performance"] = {}
            for agent_type in AgentType:
                perf = await self.get_agent_performance_summary(agent_type, days, user_id)
                report["agent_performance"][agent_type.value] = perf
        else:
            # System-wide report
            report["system_metrics"] = await self.get_system_wide_metrics(days)
            
            # Overall agent performance
            report["overall_performance"] = await self.get_agent_performance_summary(
                time_range_days=days
            )
        
        # Add insights and recommendations
        report["insights"] = await self._generate_insights(report)
        
        return report
    
    async def _generate_insights(self, report: Dict[str, Any]) -> List[str]:
        """Generate insights from performance data"""
        
        insights = []
        
        # Check overall performance
        if "overall_performance" in report:
            perf = report["overall_performance"]["summary"]
            
            if perf["success_rate"] < 0.7:
                insights.append("⚠️ Success rate is below 70% - consider reviewing agent prompts or constraints")
            
            if perf["average_execution_time_seconds"] > 300:  # 5 minutes
                insights.append("⏱️ Average execution time is high - consider optimizing agent workflows")
            
            if perf["code_quality_score"] < 1.0:
                insights.append("📝 Code quality scores could be improved - consider adding style guides")
            
            if perf["user_satisfaction_proxy"] > 0.8:
                insights.append("✅ High user satisfaction indicators - agents are performing well")
        
        # Check user-specific patterns
        if "user_analytics" in report:
            user_data = report["user_analytics"]
            
            if user_data["total_credits_used"] > 1000:
                insights.append("💰 High credit usage detected - consider optimizing agent selection")
            
            if user_data["most_used_agent"]:
                insights.append(f"🔄 Most used agent: {user_data['most_used_agent']} - consider workflow automation")
        
        # Add trend insights
        if len(insights) == 0:
            insights.append("📊 Performance metrics are within normal ranges")
        
        return insights


class RealTimeMetrics:
    """
    Real-time metrics for active agent tasks
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._metrics_cache = {}
        self._cache_ttl = 60  # seconds
    
    async def get_live_agent_status(self) -> Dict[str, Any]:
        """Get current status of all active agents"""
        
        # Get currently running tasks
        running_tasks = self.db.query(AgentTask).filter(
            AgentTask.status == TaskStatus.RUNNING.value
        ).all()
        
        running_workflows = self.db.query(AgentWorkflow).filter(
            AgentWorkflow.status == TaskStatus.RUNNING.value
        ).all()
        
        # Calculate queue lengths
        pending_tasks = self.db.query(AgentTask).filter(
            AgentTask.status == TaskStatus.PENDING.value
        ).count()
        
        pending_workflows = self.db.query(AgentWorkflow).filter(
            AgentWorkflow.status == TaskStatus.PENDING.value
        ).count()
        
        # Agent utilization
        agent_utilization = {}
        for agent_type in AgentType:
            running_count = len([t for t in running_tasks if t.agent_type == agent_type.value])
            agent_utilization[agent_type.value] = {
                "running_tasks": running_count,
                "utilization": min(1.0, running_count / 5)  # Assume max 5 concurrent per agent
            }
        
        return {
            "active_tasks": len(running_tasks),
            "active_workflows": len(running_workflows),
            "pending_tasks": pending_tasks,
            "pending_workflows": pending_workflows,
            "agent_utilization": agent_utilization,
            "system_load": len(running_tasks) + len(running_workflows),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_task_progress_metrics(self, task_id: str) -> Dict[str, Any]:
        """Get detailed progress metrics for a specific task"""
        
        task = self.db.query(AgentTask).filter(AgentTask.id == task_id).first()
        if not task:
            # Check workflows
            workflow = self.db.query(AgentWorkflow).filter(AgentWorkflow.id == task_id).first()
            if workflow:
                return {
                    "task_id": task_id,
                    "type": "workflow",
                    "status": workflow.status,
                    "progress": workflow.current_step / len(workflow.steps) if workflow.steps else 0,
                    "current_step": workflow.current_step,
                    "total_steps": len(workflow.steps) if workflow.steps else 0,
                    "estimated_completion": None
                }
            return {"error": "Task not found"}
        
        # Calculate metrics
        elapsed_time = 0
        if task.started_at:
            elapsed_time = (datetime.utcnow() - task.started_at).total_seconds()
        
        estimated_completion = None
        if task.progress and task.progress > 0:
            total_estimated = elapsed_time / task.progress
            remaining = total_estimated - elapsed_time
            if remaining > 0:
                estimated_completion = (datetime.utcnow() + timedelta(seconds=remaining)).isoformat()
        
        return {
            "task_id": task_id,
            "type": "task",
            "status": task.status,
            "progress": task.progress or 0,
            "current_step": task.current_step,
            "elapsed_time_seconds": elapsed_time,
            "estimated_completion": estimated_completion,
            "confidence_score": task.confidence_score
        }


# Global instances
_analytics_instances = {}

def get_agent_analytics(db: Session) -> AgentAnalytics:
    """Get agent analytics instance"""
    session_id = id(db)
    if session_id not in _analytics_instances:
        _analytics_instances[session_id] = AgentAnalytics(db)
    return _analytics_instances[session_id]

def get_realtime_metrics(db: Session) -> RealTimeMetrics:
    """Get real-time metrics instance"""
    return RealTimeMetrics(db)