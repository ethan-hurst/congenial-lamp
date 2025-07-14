"""
Infrastructure Cost Analytics Service
Tracks and analyzes costs for all infrastructure components
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import logging

from ...models.infrastructure import (
    Domain, SSLCertificate, CDNConfiguration, LoadBalancer, EdgeDeployment,
    InfrastructureMetrics
)
from ...models.project import Project
from ...models.user import User

logger = logging.getLogger(__name__)


class CostCalculator:
    """
    Calculates costs for different infrastructure components
    """
    
    # Pricing tiers (per month unless specified)
    PRICING = {
        "domains": {
            "free_subdomain": 0.0,
            "custom_domain": 0.0,  # User provides domain
            "premium_domain": 120.0  # If we provide premium domains
        },
        "ssl": {
            "letsencrypt": 0.0,
            "custom": 0.0,
            "ev_certificate": 100.0
        },
        "cdn": {
            "free_tier_gb": 100,
            "per_gb_after_free": 0.08,
            "purge_requests": 0.0,
            "advanced_features": 10.0  # WAF, DDoS protection per month
        },
        "load_balancer": {
            "basic_2_backends": 0.0,
            "standard_10_backends": 10.0,
            "premium_unlimited": 50.0,
            "per_backend_hour": 0.01
        },
        "edge_deployment": {
            "free_regions": 3,
            "per_region_month": 5.0,
            "per_gb_traffic": 0.01,
            "per_request": 0.0001,
            "memory_gb_hour": 0.05,
            "cpu_hour": 0.10
        }
    }
    
    @staticmethod
    def calculate_domain_cost(domain: Domain, days: int = 30) -> Dict[str, float]:
        """Calculate domain costs"""
        monthly_cost = 0.0
        
        # Check if it's a free subdomain
        if domain.domain_name.endswith('.codeforge.app'):
            monthly_cost = CostCalculator.PRICING["domains"]["free_subdomain"]
        else:
            monthly_cost = CostCalculator.PRICING["domains"]["custom_domain"]
        
        daily_cost = monthly_cost / 30
        period_cost = daily_cost * days
        
        return {
            "monthly_cost": monthly_cost,
            "period_cost": period_cost,
            "daily_cost": daily_cost,
            "cost_breakdown": {
                "domain_fee": period_cost
            }
        }
    
    @staticmethod
    def calculate_ssl_cost(certificate: SSLCertificate, days: int = 30) -> Dict[str, float]:
        """Calculate SSL certificate costs"""
        monthly_cost = 0.0
        
        if certificate.certificate_authority == "letsencrypt":
            monthly_cost = CostCalculator.PRICING["ssl"]["letsencrypt"]
        elif certificate.certificate_type == "ev":
            monthly_cost = CostCalculator.PRICING["ssl"]["ev_certificate"]
        else:
            monthly_cost = CostCalculator.PRICING["ssl"]["custom"]
        
        daily_cost = monthly_cost / 30
        period_cost = daily_cost * days
        
        return {
            "monthly_cost": monthly_cost,
            "period_cost": period_cost,
            "daily_cost": daily_cost,
            "cost_breakdown": {
                "certificate_fee": period_cost
            }
        }
    
    @staticmethod
    def calculate_cdn_cost(cdn: CDNConfiguration, days: int = 30) -> Dict[str, float]:
        """Calculate CDN costs"""
        # Base cost for advanced features
        base_monthly = 0.0
        if cdn.waf_enabled or cdn.ddos_protection:
            base_monthly = CostCalculator.PRICING["cdn"]["advanced_features"]
        
        # Bandwidth costs
        total_gb = cdn.bandwidth_usage.get("total_gb", 0) if cdn.bandwidth_usage else 0
        free_tier = CostCalculator.PRICING["cdn"]["free_tier_gb"]
        billable_gb = max(0, total_gb - free_tier)
        bandwidth_cost = billable_gb * CostCalculator.PRICING["cdn"]["per_gb_after_free"]
        
        daily_base = base_monthly / 30
        period_base = daily_base * days
        period_bandwidth = bandwidth_cost * (days / 30)  # Prorate bandwidth
        
        total_period_cost = period_base + period_bandwidth
        
        return {
            "monthly_cost": base_monthly + (bandwidth_cost * 1),  # Full month bandwidth
            "period_cost": total_period_cost,
            "daily_cost": total_period_cost / days,
            "cost_breakdown": {
                "base_features": period_base,
                "bandwidth": period_bandwidth,
                "total_gb": total_gb,
                "billable_gb": billable_gb
            }
        }
    
    @staticmethod
    def calculate_load_balancer_cost(lb: LoadBalancer, days: int = 30) -> Dict[str, float]:
        """Calculate load balancer costs"""
        backend_count = lb.backend_count
        
        # Determine tier
        if backend_count <= 2:
            monthly_base = CostCalculator.PRICING["load_balancer"]["basic_2_backends"]
        elif backend_count <= 10:
            monthly_base = CostCalculator.PRICING["load_balancer"]["standard_10_backends"]
        else:
            monthly_base = CostCalculator.PRICING["load_balancer"]["premium_unlimited"]
        
        # Additional costs for extra backends if any
        extra_backend_hours = max(0, backend_count - 2) * 24 * days
        extra_backend_cost = extra_backend_hours * CostCalculator.PRICING["load_balancer"]["per_backend_hour"]
        
        daily_base = monthly_base / 30
        period_base = daily_base * days
        
        total_period_cost = period_base + extra_backend_cost
        
        return {
            "monthly_cost": monthly_base + (extra_backend_cost * 30 / days),
            "period_cost": total_period_cost,
            "daily_cost": total_period_cost / days,
            "cost_breakdown": {
                "base_tier": period_base,
                "extra_backends": extra_backend_cost,
                "backend_count": backend_count
            }
        }
    
    @staticmethod
    def calculate_edge_deployment_cost(edge: EdgeDeployment, days: int = 30) -> Dict[str, float]:
        """Calculate edge deployment costs"""
        # Region costs
        region_count = edge.edge_location_count
        free_regions = CostCalculator.PRICING["edge_deployment"]["free_regions"]
        billable_regions = max(0, region_count - free_regions)
        
        region_monthly = billable_regions * CostCalculator.PRICING["edge_deployment"]["per_region_month"]
        
        # Resource costs (memory and CPU)
        memory_gb = edge.memory_limit / 1024  # Convert MB to GB
        hours = 24 * days
        
        memory_cost = memory_gb * hours * CostCalculator.PRICING["edge_deployment"]["memory_gb_hour"]
        cpu_cost = hours * CostCalculator.PRICING["edge_deployment"]["cpu_hour"]
        
        # Traffic costs
        traffic_gb = edge.bandwidth_usage.get("total_gb", 0) if hasattr(edge, 'bandwidth_usage') and edge.bandwidth_usage else 0
        traffic_cost = traffic_gb * CostCalculator.PRICING["edge_deployment"]["per_gb_traffic"]
        
        # Request costs
        total_requests = edge.requests_per_minute * 60 * 24 * days  # Estimate for period
        request_cost = total_requests * CostCalculator.PRICING["edge_deployment"]["per_request"]
        
        daily_region = region_monthly / 30
        period_region = daily_region * days
        
        total_period_cost = period_region + memory_cost + cpu_cost + traffic_cost + request_cost
        
        return {
            "monthly_cost": region_monthly + (memory_cost + cpu_cost) * 30 / days + traffic_cost * 30 / days + request_cost * 30 / days,
            "period_cost": total_period_cost,
            "daily_cost": total_period_cost / days,
            "cost_breakdown": {
                "regions": period_region,
                "memory": memory_cost,
                "cpu": cpu_cost,
                "traffic": traffic_cost,
                "requests": request_cost,
                "region_count": region_count,
                "billable_regions": billable_regions
            }
        }


class InfrastructureCostAnalytics:
    """
    Comprehensive cost analytics for infrastructure
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_project_cost_summary(
        self,
        project_id: str,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive cost summary for a project
        
        Args:
            project_id: Project identifier
            user_id: User identifier
            days: Number of days to calculate costs for
            
        Returns:
            Cost summary with breakdowns
        """
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get all infrastructure components for the project
        domains = self.db.query(Domain).filter(
            and_(Domain.project_id == project_id, Domain.user_id == user_id)
        ).all()
        
        ssl_certs = self.db.query(SSLCertificate).filter(
            and_(SSLCertificate.project_id == project_id, SSLCertificate.user_id == user_id)
        ).all()
        
        cdn_configs = self.db.query(CDNConfiguration).filter(
            and_(CDNConfiguration.project_id == project_id, CDNConfiguration.user_id == user_id)
        ).all()
        
        load_balancers = self.db.query(LoadBalancer).filter(
            and_(LoadBalancer.project_id == project_id, LoadBalancer.user_id == user_id)
        ).all()
        
        edge_deployments = self.db.query(EdgeDeployment).filter(
            and_(EdgeDeployment.project_id == project_id, EdgeDeployment.user_id == user_id)
        ).all()
        
        # Calculate costs for each component type
        cost_summary = {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_cost": 0.0,
            "monthly_projection": 0.0,
            "components": {}
        }
        
        # Domain costs
        domain_costs = []
        total_domain_cost = 0.0
        for domain in domains:
            cost = CostCalculator.calculate_domain_cost(domain, days)
            domain_costs.append({
                "id": domain.id,
                "name": domain.domain_name,
                "cost": cost
            })
            total_domain_cost += cost["period_cost"]
        
        cost_summary["components"]["domains"] = {
            "count": len(domains),
            "total_cost": total_domain_cost,
            "items": domain_costs
        }
        
        # SSL costs
        ssl_costs = []
        total_ssl_cost = 0.0
        for cert in ssl_certs:
            cost = CostCalculator.calculate_ssl_cost(cert, days)
            ssl_costs.append({
                "id": cert.id,
                "domain": cert.common_name,
                "cost": cost
            })
            total_ssl_cost += cost["period_cost"]
        
        cost_summary["components"]["ssl_certificates"] = {
            "count": len(ssl_certs),
            "total_cost": total_ssl_cost,
            "items": ssl_costs
        }
        
        # CDN costs
        cdn_costs = []
        total_cdn_cost = 0.0
        for cdn in cdn_configs:
            cost = CostCalculator.calculate_cdn_cost(cdn, days)
            cdn_costs.append({
                "id": cdn.id,
                "provider": cdn.provider,
                "cost": cost
            })
            total_cdn_cost += cost["period_cost"]
        
        cost_summary["components"]["cdn_configurations"] = {
            "count": len(cdn_configs),
            "total_cost": total_cdn_cost,
            "items": cdn_costs
        }
        
        # Load balancer costs
        lb_costs = []
        total_lb_cost = 0.0
        for lb in load_balancers:
            cost = CostCalculator.calculate_load_balancer_cost(lb, days)
            lb_costs.append({
                "id": lb.id,
                "name": lb.name,
                "cost": cost
            })
            total_lb_cost += cost["period_cost"]
        
        cost_summary["components"]["load_balancers"] = {
            "count": len(load_balancers),
            "total_cost": total_lb_cost,
            "items": lb_costs
        }
        
        # Edge deployment costs
        edge_costs = []
        total_edge_cost = 0.0
        for edge in edge_deployments:
            cost = CostCalculator.calculate_edge_deployment_cost(edge, days)
            edge_costs.append({
                "id": edge.id,
                "name": edge.name,
                "cost": cost
            })
            total_edge_cost += cost["period_cost"]
        
        cost_summary["components"]["edge_deployments"] = {
            "count": len(edge_deployments),
            "total_cost": total_edge_cost,
            "items": edge_costs
        }
        
        # Calculate totals
        cost_summary["total_cost"] = (
            total_domain_cost + total_ssl_cost + total_cdn_cost + 
            total_lb_cost + total_edge_cost
        )
        
        cost_summary["monthly_projection"] = cost_summary["total_cost"] * 30 / days
        
        # Add cost distribution
        cost_summary["cost_distribution"] = {
            "domains": total_domain_cost,
            "ssl_certificates": total_ssl_cost,
            "cdn": total_cdn_cost,
            "load_balancers": total_lb_cost,
            "edge_deployments": total_edge_cost
        }
        
        return cost_summary
    
    async def get_cost_trends(
        self,
        project_id: str,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get cost trends over time"""
        
        # Calculate costs for different periods
        periods = []
        period_length = max(1, days // 7)  # Weekly periods
        
        for i in range(7):
            period_start = datetime.utcnow() - timedelta(days=days - (i * period_length))
            period_end = datetime.utcnow() - timedelta(days=days - ((i + 1) * period_length))
            
            # For simplicity, we'll calculate current costs and project backwards
            # In a real implementation, we'd store historical cost data
            current_summary = await self.get_project_cost_summary(project_id, user_id, period_length)
            
            periods.append({
                "start_date": period_start.date().isoformat(),
                "end_date": period_end.date().isoformat(),
                "total_cost": current_summary["total_cost"],
                "component_costs": current_summary["cost_distribution"]
            })
        
        return {
            "periods": periods,
            "trend_analysis": {
                "average_weekly_cost": sum(p["total_cost"] for p in periods) / len(periods),
                "cost_variance": "stable",  # Would calculate actual variance
                "highest_cost_component": max(
                    current_summary["cost_distribution"].items(),
                    key=lambda x: x[1]
                )[0] if current_summary["cost_distribution"] else None
            }
        }
    
    async def get_cost_optimization_suggestions(
        self,
        project_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Generate cost optimization suggestions"""
        
        suggestions = []
        
        # Get current cost summary
        summary = await self.get_project_cost_summary(project_id, user_id, 30)
        
        # Check CDN usage efficiency
        for cdn_item in summary["components"]["cdn_configurations"]["items"]:
            cost_breakdown = cdn_item["cost"]["cost_breakdown"]
            if cost_breakdown["billable_gb"] > 500:  # High bandwidth usage
                suggestions.append({
                    "type": "cdn_optimization",
                    "priority": "high",
                    "title": "Optimize CDN Cache Settings",
                    "description": f"High bandwidth usage detected ({cost_breakdown['total_gb']}GB). Consider increasing cache TTL to reduce origin requests.",
                    "potential_savings": cost_breakdown["bandwidth"] * 0.3,  # 30% potential savings
                    "resource_id": cdn_item["id"]
                })
        
        # Check load balancer efficiency
        for lb_item in summary["components"]["load_balancers"]["items"]:
            cost_breakdown = lb_item["cost"]["cost_breakdown"]
            if cost_breakdown["backend_count"] > 10:
                suggestions.append({
                    "type": "load_balancer_optimization",
                    "priority": "medium",
                    "title": "Review Load Balancer Backend Count",
                    "description": f"Large number of backends ({cost_breakdown['backend_count']}). Consider if all are necessary.",
                    "potential_savings": cost_breakdown["extra_backends"] * 0.5,
                    "resource_id": lb_item["id"]
                })
        
        # Check edge deployment regions
        for edge_item in summary["components"]["edge_deployments"]["items"]:
            cost_breakdown = edge_item["cost"]["cost_breakdown"]
            if cost_breakdown["billable_regions"] > 5:
                suggestions.append({
                    "type": "edge_optimization",
                    "priority": "medium",
                    "title": "Optimize Edge Deployment Regions",
                    "description": f"Deployed to {cost_breakdown['region_count']} regions. Consider if all regions are needed based on traffic patterns.",
                    "potential_savings": cost_breakdown["regions"] * 0.4,
                    "resource_id": edge_item["id"]
                })
        
        # Check for unused resources
        if summary["total_cost"] > 100 and summary["components"]["domains"]["count"] == 0:
            suggestions.append({
                "type": "resource_cleanup",
                "priority": "high",
                "title": "Review Infrastructure Usage",
                "description": "High infrastructure costs but no custom domains. Consider if all resources are being used effectively.",
                "potential_savings": summary["total_cost"] * 0.2
            })
        
        return suggestions
    
    async def get_cost_alerts(
        self,
        project_id: str,
        user_id: str,
        budget_limit: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Generate cost alerts"""
        
        alerts = []
        summary = await self.get_project_cost_summary(project_id, user_id, 30)
        monthly_projection = summary["monthly_projection"]
        
        # Budget alert
        if budget_limit and monthly_projection > budget_limit:
            alerts.append({
                "type": "budget_exceeded",
                "severity": "high",
                "title": "Monthly Budget Exceeded",
                "message": f"Projected monthly cost (${monthly_projection:.2f}) exceeds budget (${budget_limit:.2f})",
                "current_cost": monthly_projection,
                "budget_limit": budget_limit
            })
        
        # High growth alert
        if monthly_projection > 200:  # Arbitrary threshold
            alerts.append({
                "type": "high_cost",
                "severity": "medium",
                "title": "High Infrastructure Costs",
                "message": f"Monthly infrastructure costs are projected at ${monthly_projection:.2f}",
                "current_cost": monthly_projection
            })
        
        # Component-specific alerts
        for component_type, component_data in summary["components"].items():
            if component_data["total_cost"] > summary["total_cost"] * 0.6:  # Component is >60% of total cost
                alerts.append({
                    "type": "component_cost_spike",
                    "severity": "medium",
                    "title": f"High {component_type.replace('_', ' ').title()} Costs",
                    "message": f"{component_type.replace('_', ' ').title()} accounts for ${component_data['total_cost']:.2f} of your infrastructure costs",
                    "component": component_type,
                    "cost": component_data["total_cost"]
                })
        
        return alerts


# Global instances
_cost_analytics_instances = {}

def get_cost_analytics(db: Session) -> InfrastructureCostAnalytics:
    """Get cost analytics instance"""
    session_id = id(db)
    if session_id not in _cost_analytics_instances:
        _cost_analytics_instances[session_id] = InfrastructureCostAnalytics(db)
    return _cost_analytics_instances[session_id]