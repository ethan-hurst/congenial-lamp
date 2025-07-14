"""
Infrastructure Management API endpoints
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

from ...database.connection import get_database_session
from ...auth.dependencies import get_current_user
from ...models.user import User
from ...services.infrastructure.domain_service import DomainService
from ...services.infrastructure.ssl_service import SSLService
from ...services.infrastructure.cdn_service import CDNService
from ...services.infrastructure.load_balancer_service import LoadBalancerService
from ...services.infrastructure.edge_service import EdgeDeploymentService
from ...services.credits_service import CreditsService


router = APIRouter(prefix="/infrastructure", tags=["infrastructure"])


# Request/Response Models

class DomainAddRequest(BaseModel):
    """Request to add a domain"""
    domain_name: str = Field(..., min_length=3, max_length=253)
    dns_provider: str = Field(default="cloudflare")


class DomainUpdateRequest(BaseModel):
    """Request to update domain DNS records"""
    records: List[Dict[str, Any]]


class SSLProvisionRequest(BaseModel):
    """Request to provision SSL certificate"""
    certificate_authority: str = Field(default="letsencrypt")
    validation_method: str = Field(default="dns")


class CDNConfigurationRequest(BaseModel):
    """Request to create CDN configuration"""
    provider: str = Field(default="cloudflare")
    default_ttl: int = Field(default=3600, ge=60, le=86400)
    max_ttl: int = Field(default=86400, ge=300, le=604800)
    compression_enabled: bool = Field(default=True)
    waf_enabled: bool = Field(default=True)
    ddos_protection: bool = Field(default=True)
    minification: Dict[str, bool] = Field(default={"html": True, "css": True, "js": True})


class CDNUpdateRequest(BaseModel):
    """Request to update CDN configuration"""
    default_ttl: Optional[int] = Field(None, ge=60, le=86400)
    max_ttl: Optional[int] = Field(None, ge=300, le=604800)
    compression_enabled: Optional[bool] = None
    waf_enabled: Optional[bool] = None
    ddos_protection: Optional[bool] = None
    minification: Optional[Dict[str, bool]] = None


class LoadBalancerCreateRequest(BaseModel):
    """Request to create load balancer"""
    name: str = Field(..., min_length=1, max_length=100)
    backend_servers: List[Dict[str, Any]] = Field(..., min_items=1)
    algorithm: str = Field(default="round_robin")
    health_check_config: Optional[Dict[str, Any]] = None


class LoadBalancerUpdateRequest(BaseModel):
    """Request to update load balancer"""
    name: Optional[str] = None
    algorithm: Optional[str] = None
    health_check_enabled: Optional[bool] = None
    health_check_interval: Optional[int] = None


class EdgeDeploymentCreateRequest(BaseModel):
    """Request to create edge deployment"""
    name: str = Field(..., min_length=1, max_length=100)
    runtime: str = Field(default="nodejs")
    runtime_version: str = Field(default="18")
    memory_limit: int = Field(default=512, ge=128, le=4096)
    timeout: int = Field(default=30, ge=1, le=300)
    environment_variables: Dict[str, str] = Field(default={})
    target_regions: List[str] = Field(default=["North America", "Europe", "Asia Pacific"])
    deployment_strategy: str = Field(default="rolling")


# Domain Management Endpoints

@router.post("/domains", response_model=Dict[str, Any])
async def add_domain(
    project_id: str,
    request: DomainAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Add a custom domain to a project"""
    try:
        domain_service = DomainService(db)
        domain = await domain_service.add_domain(
            project_id=project_id,
            user_id=current_user.id,
            domain_name=request.domain_name,
            dns_provider=request.dns_provider
        )
        
        return {
            "id": domain.id,
            "domain_name": domain.domain_name,
            "status": domain.status.value,
            "verification_token": domain.verification_token,
            "created_at": domain.created_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/domains", response_model=List[Dict[str, Any]])
async def list_domains(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """List all domains for a project"""
    try:
        domain_service = DomainService(db)
        domains = await domain_service.list_domains(project_id, current_user.id)
        return domains
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domains/{domain_id}", response_model=Dict[str, Any])
async def get_domain_status(
    domain_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get domain status and configuration"""
    try:
        domain_service = DomainService(db)
        status = await domain_service.get_domain_status(domain_id)
        return status
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/domains/{domain_id}/verify")
async def verify_domain(
    domain_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Manually trigger domain verification"""
    try:
        domain_service = DomainService(db)
        verified = await domain_service.verify_domain(domain_id)
        
        return {"verified": verified}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/domains/{domain_id}/dns", response_model=Dict[str, Any])
async def update_dns_records(
    domain_id: str,
    request: DomainUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Update DNS records for a domain"""
    try:
        domain_service = DomainService(db)
        success = await domain_service.update_dns_records(domain_id, request.records)
        
        return {"success": success}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/domains/{domain_id}")
async def remove_domain(
    domain_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Remove a domain"""
    try:
        domain_service = DomainService(db)
        success = await domain_service.remove_domain(domain_id, current_user.id)
        
        return {"success": success}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# SSL Certificate Management Endpoints

@router.post("/ssl/provision", response_model=Dict[str, Any])
async def provision_ssl_certificate(
    domain_id: str,
    request: SSLProvisionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Provision SSL certificate for a domain"""
    try:
        ssl_service = SSLService(db)
        certificate = await ssl_service.provision_certificate(
            domain_id=domain_id,
            certificate_authority=request.certificate_authority,
            validation_method=request.validation_method
        )
        
        return {
            "id": certificate.id,
            "common_name": certificate.common_name,
            "status": certificate.status.value,
            "created_at": certificate.created_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ssl/certificates", response_model=List[Dict[str, Any]])
async def list_ssl_certificates(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """List all SSL certificates for a project"""
    try:
        ssl_service = SSLService(db)
        certificates = await ssl_service.list_certificates(project_id, current_user.id)
        return certificates
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ssl/certificates/{cert_id}", response_model=Dict[str, Any])
async def get_ssl_certificate_status(
    cert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get SSL certificate status and details"""
    try:
        ssl_service = SSLService(db)
        status = await ssl_service.get_certificate_status(cert_id)
        return status
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/ssl/certificates/{cert_id}/renew")
async def renew_ssl_certificate(
    cert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Manually renew SSL certificate"""
    try:
        ssl_service = SSLService(db)
        success = await ssl_service.renew_certificate(cert_id)
        
        return {"success": success}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ssl/certificates/{cert_id}/revoke")
async def revoke_ssl_certificate(
    cert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Revoke SSL certificate"""
    try:
        ssl_service = SSLService(db)
        success = await ssl_service.revoke_certificate(cert_id)
        
        return {"success": success}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# CDN Management Endpoints

@router.post("/cdn", response_model=Dict[str, Any])
async def create_cdn_configuration(
    domain_id: str,
    request: CDNConfigurationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Create CDN configuration for a domain"""
    try:
        cdn_service = CDNService(db)
        
        configuration = {
            "default_ttl": request.default_ttl,
            "max_ttl": request.max_ttl,
            "compression_enabled": request.compression_enabled,
            "waf_enabled": request.waf_enabled,
            "ddos_protection": request.ddos_protection,
            "minification": request.minification
        }
        
        cdn_config = await cdn_service.create_cdn_configuration(
            domain_id=domain_id,
            provider=request.provider,
            configuration=configuration
        )
        
        return {
            "id": cdn_config.id,
            "domain_id": cdn_config.domain_id,
            "provider": cdn_config.provider,
            "status": cdn_config.status.value,
            "created_at": cdn_config.created_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cdn", response_model=List[Dict[str, Any]])
async def list_cdn_configurations(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """List all CDN configurations for a project"""
    try:
        cdn_service = CDNService(db)
        configurations = await cdn_service.list_cdn_configurations(project_id, current_user.id)
        return configurations
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cdn/{cdn_id}", response_model=Dict[str, Any])
async def get_cdn_status(
    cdn_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get CDN configuration status and analytics"""
    try:
        cdn_service = CDNService(db)
        status = await cdn_service.get_cdn_status(cdn_id)
        return status
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/cdn/{cdn_id}", response_model=Dict[str, Any])
async def update_cdn_configuration(
    cdn_id: str,
    request: CDNUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Update CDN configuration"""
    try:
        cdn_service = CDNService(db)
        
        # Filter out None values
        configuration = {k: v for k, v in request.dict().items() if v is not None}
        
        success = await cdn_service.update_cdn_configuration(cdn_id, configuration)
        
        return {"success": success}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cdn/{cdn_id}/purge")
async def purge_cdn_cache(
    cdn_id: str,
    paths: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Purge CDN cache"""
    try:
        cdn_service = CDNService(db)
        success = await cdn_service.purge_cache(cdn_id, paths)
        
        return {"success": success}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cdn/{cdn_id}/analytics", response_model=Dict[str, Any])
async def get_cdn_analytics(
    cdn_id: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get CDN analytics data"""
    try:
        cdn_service = CDNService(db)
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        analytics = await cdn_service.get_cdn_analytics(cdn_id, start_date, end_date)
        return analytics
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/cdn/{cdn_id}")
async def delete_cdn_configuration(
    cdn_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Delete CDN configuration"""
    try:
        cdn_service = CDNService(db)
        success = await cdn_service.delete_cdn_configuration(cdn_id, current_user.id)
        
        return {"success": success}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Load Balancer Management Endpoints

@router.post("/load-balancers", response_model=Dict[str, Any])
async def create_load_balancer(
    domain_id: str,
    request: LoadBalancerCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Create a new load balancer"""
    try:
        lb_service = LoadBalancerService(db)
        
        load_balancer = await lb_service.create_load_balancer(
            domain_id=domain_id,
            name=request.name,
            backend_servers=request.backend_servers,
            algorithm=request.algorithm,
            health_check_config=request.health_check_config
        )
        
        return {
            "id": load_balancer.id,
            "name": load_balancer.name,
            "algorithm": load_balancer.algorithm,
            "status": load_balancer.status.value,
            "created_at": load_balancer.created_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/load-balancers", response_model=List[Dict[str, Any]])
async def list_load_balancers(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """List all load balancers for a project"""
    try:
        lb_service = LoadBalancerService(db)
        load_balancers = await lb_service.list_load_balancers(project_id, current_user.id)
        return load_balancers
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/load-balancers/{lb_id}", response_model=Dict[str, Any])
async def get_load_balancer_status(
    lb_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get load balancer status and metrics"""
    try:
        lb_service = LoadBalancerService(db)
        status = await lb_service.get_load_balancer_status(lb_id)
        return status
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/load-balancers/{lb_id}", response_model=Dict[str, Any])
async def update_load_balancer(
    lb_id: str,
    request: LoadBalancerUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Update load balancer configuration"""
    try:
        lb_service = LoadBalancerService(db)
        
        # Filter out None values
        updates = {k: v for k, v in request.dict().items() if v is not None}
        
        success = await lb_service.update_load_balancer(lb_id, updates)
        
        return {"success": success}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/load-balancers/{lb_id}/servers")
async def add_backend_server(
    lb_id: str,
    server: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Add backend server to load balancer"""
    try:
        lb_service = LoadBalancerService(db)
        success = await lb_service.add_backend_server(lb_id, server)
        
        return {"success": success}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/load-balancers/{lb_id}/servers/{server_index}")
async def remove_backend_server(
    lb_id: str,
    server_index: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Remove backend server from load balancer"""
    try:
        lb_service = LoadBalancerService(db)
        success = await lb_service.remove_backend_server(lb_id, server_index)
        
        return {"success": success}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/load-balancers/{lb_id}")
async def delete_load_balancer(
    lb_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Delete load balancer"""
    try:
        lb_service = LoadBalancerService(db)
        success = await lb_service.delete_load_balancer(lb_id, current_user.id)
        
        return {"success": success}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Edge Deployment Management Endpoints

@router.post("/edge/deployments", response_model=Dict[str, Any])
async def create_edge_deployment(
    request: EdgeDeploymentCreateRequest,
    code_bundle: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Create a new edge deployment"""
    try:
        edge_service = EdgeDeploymentService(db)
        
        # Read code bundle
        code_bundle_data = await code_bundle.read()
        
        # Get project_id from request or context
        project_id = "default-project"  # This should come from context
        
        deployment = await edge_service.create_edge_deployment(
            project_id=project_id,
            user_id=current_user.id,
            name=request.name,
            code_bundle=code_bundle_data,
            runtime=request.runtime,
            runtime_version=request.runtime_version,
            configuration={
                "memory_limit": request.memory_limit,
                "timeout": request.timeout,
                "environment_variables": request.environment_variables,
                "target_regions": request.target_regions,
                "deployment_strategy": request.deployment_strategy
            }
        )
        
        return {
            "id": deployment.id,
            "name": deployment.name,
            "version": deployment.version,
            "status": deployment.status.value,
            "created_at": deployment.created_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/edge/deployments", response_model=List[Dict[str, Any]])
async def list_edge_deployments(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """List all edge deployments for a project"""
    try:
        edge_service = EdgeDeploymentService(db)
        deployments = await edge_service.list_edge_deployments(project_id, current_user.id)
        return deployments
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edge/deployments/{deployment_id}", response_model=Dict[str, Any])
async def get_edge_deployment_status(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get edge deployment status and metrics"""
    try:
        edge_service = EdgeDeploymentService(db)
        status = await edge_service.get_edge_deployment_status(deployment_id)
        return status
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/edge/deployments/{deployment_id}")
async def update_edge_deployment(
    deployment_id: str,
    code_bundle: Optional[UploadFile] = File(None),
    configuration: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Update edge deployment"""
    try:
        edge_service = EdgeDeploymentService(db)
        
        code_bundle_data = None
        if code_bundle:
            code_bundle_data = await code_bundle.read()
        
        config_dict = None
        if configuration:
            config_dict = json.loads(configuration)
        
        success = await edge_service.update_edge_deployment(
            deployment_id,
            code_bundle_data,
            config_dict
        )
        
        return {"success": success}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/edge/deployments/{deployment_id}/scale")
async def scale_edge_deployment(
    deployment_id: str,
    scale_factor: float = Query(..., ge=0.1, le=10.0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Scale edge deployment up or down"""
    try:
        edge_service = EdgeDeploymentService(db)
        success = await edge_service.scale_edge_deployment(deployment_id, scale_factor=scale_factor)
        
        return {"success": success}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/edge/deployments/{deployment_id}/logs", response_model=List[Dict[str, Any]])
async def get_deployment_logs(
    deployment_id: str,
    location_code: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get deployment logs"""
    try:
        edge_service = EdgeDeploymentService(db)
        logs = await edge_service.get_deployment_logs(
            deployment_id,
            location_code,
            start_time,
            end_time
        )
        return logs
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/edge/deployments/{deployment_id}")
async def delete_edge_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Delete edge deployment"""
    try:
        edge_service = EdgeDeploymentService(db)
        success = await edge_service.delete_edge_deployment(deployment_id, current_user.id)
        
        return {"success": success}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Global Infrastructure Endpoints

@router.get("/edge/locations", response_model=Dict[str, Any])
async def get_edge_locations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get global edge location map"""
    try:
        edge_service = EdgeDeploymentService(db)
        map_data = await edge_service.get_global_edge_map()
        return map_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview", response_model=Dict[str, Any])
async def get_infrastructure_overview(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get infrastructure overview for a project"""
    try:
        # Get counts and status for all infrastructure components
        domain_service = DomainService(db)
        ssl_service = SSLService(db)
        cdn_service = CDNService(db)
        lb_service = LoadBalancerService(db)
        edge_service = EdgeDeploymentService(db)
        
        domains = await domain_service.list_domains(project_id, current_user.id)
        certificates = await ssl_service.list_certificates(project_id, current_user.id)
        cdn_configs = await cdn_service.list_cdn_configurations(project_id, current_user.id)
        load_balancers = await lb_service.list_load_balancers(project_id, current_user.id)
        edge_deployments = await edge_service.list_edge_deployments(project_id, current_user.id)
        
        return {
            "domains": {
                "total": len(domains),
                "active": len([d for d in domains if d.get("domain", {}).get("status") == "active"]),
                "items": domains[:5]  # Latest 5
            },
            "ssl_certificates": {
                "total": len(certificates),
                "active": len([c for c in certificates if c.get("certificate", {}).get("status") == "active"]),
                "items": certificates[:5]
            },
            "cdn_configurations": {
                "total": len(cdn_configs),
                "active": len([c for c in cdn_configs if c.get("configuration", {}).get("status") == "active"]),
                "items": cdn_configs[:5]
            },
            "load_balancers": {
                "total": len(load_balancers),
                "active": len([lb for lb in load_balancers if lb.get("load_balancer", {}).get("status") == "active"]),
                "items": load_balancers[:5]
            },
            "edge_deployments": {
                "total": len(edge_deployments),
                "active": len([e for e in edge_deployments if e.get("deployment", {}).get("status") == "active"]),
                "items": edge_deployments[:5]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))