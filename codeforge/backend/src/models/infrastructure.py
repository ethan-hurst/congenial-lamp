"""
Infrastructure Management Data Models
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, Float, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timedelta
import uuid
import enum

from ..database.connection import Base


class DomainStatus(enum.Enum):
    """Domain status enumeration"""
    PENDING = "pending"
    ACTIVE = "active"
    FAILED = "failed"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class SSLStatus(enum.Enum):
    """SSL certificate status enumeration"""
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    FAILED = "failed"
    RENEWING = "renewing"


class CDNStatus(enum.Enum):
    """CDN configuration status enumeration"""
    PENDING = "pending"
    ACTIVE = "active"
    UPDATING = "updating"
    FAILED = "failed"
    DISABLED = "disabled"


class LoadBalancerStatus(enum.Enum):
    """Load balancer status enumeration"""
    PENDING = "pending"
    ACTIVE = "active"
    UPDATING = "updating"
    FAILED = "failed"
    STOPPED = "stopped"


class EdgeDeploymentStatus(enum.Enum):
    """Edge deployment status enumeration"""
    PENDING = "pending"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    FAILED = "failed"
    UPDATING = "updating"
    STOPPED = "stopped"


class HealthCheckType(enum.Enum):
    """Health check type enumeration"""
    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"
    UDP = "udp"


class Domain(Base):
    """Domain model for custom domain management"""
    __tablename__ = "domains"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    # Domain details
    domain_name = Column(String, nullable=False, unique=True, index=True)
    subdomain = Column(String, nullable=True)
    root_domain = Column(String, nullable=False, index=True)
    
    # DNS Configuration
    dns_provider = Column(String, default="cloudflare")
    nameservers = Column(JSON, default=list)
    dns_records = Column(JSON, default=dict)
    
    # Status and metadata
    status = Column(Enum(DomainStatus), default=DomainStatus.PENDING)
    verification_token = Column(String, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    propagation_status = Column(JSON, default=dict)
    
    # Configuration
    redirect_to_https = Column(Boolean, default=True)
    www_redirect = Column(Boolean, default=True)
    custom_headers = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    ssl_certificates = relationship("SSLCertificate", back_populates="domain", cascade="all, delete-orphan")
    cdn_config = relationship("CDNConfiguration", back_populates="domain", uselist=False)
    load_balancers = relationship("LoadBalancer", back_populates="domain")

    def __repr__(self):
        return f"<Domain {self.domain_name}>"

    @property
    def is_verified(self):
        return self.verified_at is not None and self.status == DomainStatus.ACTIVE

    @property
    def full_domain(self):
        if self.subdomain:
            return f"{self.subdomain}.{self.root_domain}"
        return self.root_domain


class SSLCertificate(Base):
    """SSL certificate model for HTTPS support"""
    __tablename__ = "ssl_certificates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    domain_id = Column(String, ForeignKey("domains.id"), nullable=False)
    project_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    # Certificate details
    certificate_authority = Column(String, default="letsencrypt")
    certificate_type = Column(String, default="domain_validated")
    common_name = Column(String, nullable=False)
    subject_alternative_names = Column(JSON, default=list)
    
    # Certificate data
    certificate_pem = Column(Text, nullable=True)
    private_key_pem = Column(Text, nullable=True)
    certificate_chain = Column(Text, nullable=True)
    
    # Status and validation
    status = Column(Enum(SSLStatus), default=SSLStatus.PENDING)
    validation_method = Column(String, default="dns")
    validation_records = Column(JSON, default=dict)
    
    # Lifecycle
    issued_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    auto_renew = Column(Boolean, default=True)
    renewal_threshold_days = Column(Integer, default=30)
    
    # Metadata
    serial_number = Column(String, nullable=True)
    fingerprint = Column(String, nullable=True)
    key_size = Column(Integer, default=2048)
    signature_algorithm = Column(String, default="SHA256withRSA")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    domain = relationship("Domain", back_populates="ssl_certificates")

    def __repr__(self):
        return f"<SSLCertificate {self.common_name}>"

    @property
    def is_valid(self):
        return (
            self.status == SSLStatus.ACTIVE and
            self.expires_at and
            self.expires_at > datetime.utcnow()
        )

    @property
    def days_until_expiry(self):
        if self.expires_at:
            return (self.expires_at - datetime.utcnow()).days
        return None

    @property
    def needs_renewal(self):
        return (
            self.auto_renew and
            self.days_until_expiry is not None and
            self.days_until_expiry <= self.renewal_threshold_days
        )


class CDNConfiguration(Base):
    """CDN configuration model for global content delivery"""
    __tablename__ = "cdn_configurations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    domain_id = Column(String, ForeignKey("domains.id"), nullable=False)
    project_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    # CDN Provider
    provider = Column(String, default="cloudflare")
    distribution_id = Column(String, nullable=True)
    cname = Column(String, nullable=True)
    
    # Caching configuration
    default_ttl = Column(Integer, default=3600)  # 1 hour
    max_ttl = Column(Integer, default=86400)     # 24 hours
    cache_rules = Column(JSON, default=list)
    cache_behaviors = Column(JSON, default=dict)
    
    # Edge locations
    edge_locations = Column(JSON, default=list)
    geographic_restrictions = Column(JSON, default=dict)
    
    # Origin configuration
    origin_domain = Column(String, nullable=False)
    origin_path = Column(String, default="/")
    origin_protocol = Column(String, default="https")
    origin_port = Column(Integer, default=443)
    
    # Security
    waf_enabled = Column(Boolean, default=True)
    ddos_protection = Column(Boolean, default=True)
    rate_limiting = Column(JSON, default=dict)
    security_headers = Column(JSON, default=dict)
    
    # Compression and optimization
    compression_enabled = Column(Boolean, default=True)
    brotli_enabled = Column(Boolean, default=True)
    image_optimization = Column(Boolean, default=True)
    minification = Column(JSON, default={"html": True, "css": True, "js": True})
    
    # Status and metrics
    status = Column(Enum(CDNStatus), default=CDNStatus.PENDING)
    last_deployment = Column(DateTime, nullable=True)
    cache_hit_ratio = Column(Float, default=0.0)
    bandwidth_usage = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    domain = relationship("Domain", back_populates="cdn_config")

    def __repr__(self):
        return f"<CDNConfiguration {self.domain.domain_name}>"

    @property
    def is_active(self):
        return self.status == CDNStatus.ACTIVE

    @property
    def cache_efficiency(self):
        return self.cache_hit_ratio


class LoadBalancer(Base):
    """Load balancer model for traffic distribution"""
    __tablename__ = "load_balancers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    domain_id = Column(String, ForeignKey("domains.id"), nullable=False)
    project_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    # Load balancer details
    name = Column(String, nullable=False)
    type = Column(String, default="application")  # application, network, gateway
    scheme = Column(String, default="internet-facing")  # internet-facing, internal
    
    # Target groups and backends
    backend_servers = Column(JSON, default=list)
    target_groups = Column(JSON, default=list)
    
    # Load balancing configuration
    algorithm = Column(String, default="round_robin")  # round_robin, least_connections, ip_hash
    session_affinity = Column(Boolean, default=False)
    sticky_sessions = Column(JSON, default=dict)
    
    # Health checks
    health_check_enabled = Column(Boolean, default=True)
    health_check_type = Column(Enum(HealthCheckType), default=HealthCheckType.HTTP)
    health_check_path = Column(String, default="/health")
    health_check_interval = Column(Integer, default=30)
    health_check_timeout = Column(Integer, default=5)
    health_check_retries = Column(Integer, default=3)
    
    # SSL termination
    ssl_termination = Column(Boolean, default=True)
    ssl_certificate_id = Column(String, nullable=True)
    ssl_protocols = Column(JSON, default=["TLSv1.2", "TLSv1.3"])
    
    # Traffic configuration
    connection_timeout = Column(Integer, default=60)
    idle_timeout = Column(Integer, default=300)
    keep_alive_timeout = Column(Integer, default=75)
    max_connections = Column(Integer, default=1000)
    
    # Security
    security_groups = Column(JSON, default=list)
    access_logs_enabled = Column(Boolean, default=True)
    waf_integration = Column(Boolean, default=True)
    
    # Status and metrics
    status = Column(Enum(LoadBalancerStatus), default=LoadBalancerStatus.PENDING)
    external_ip = Column(String, nullable=True)
    internal_ip = Column(String, nullable=True)
    dns_name = Column(String, nullable=True)
    
    # Performance metrics
    active_connections = Column(Integer, default=0)
    requests_per_second = Column(Float, default=0.0)
    response_time_p95 = Column(Float, default=0.0)
    error_rate = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    domain = relationship("Domain", back_populates="load_balancers")

    def __repr__(self):
        return f"<LoadBalancer {self.name}>"

    @property
    def is_healthy(self):
        return self.status == LoadBalancerStatus.ACTIVE and self.error_rate < 0.05

    @property
    def backend_count(self):
        return len(self.backend_servers)


class EdgeDeployment(Base):
    """Edge deployment model for global deployment"""
    __tablename__ = "edge_deployments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    # Deployment details
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String, nullable=False)
    
    # Edge configuration
    edge_locations = Column(JSON, default=list)
    deployment_strategy = Column(String, default="rolling")  # rolling, blue_green, canary
    traffic_allocation = Column(JSON, default=dict)
    
    # Runtime configuration
    runtime = Column(String, default="nodejs")
    runtime_version = Column(String, default="18")
    memory_limit = Column(Integer, default=512)  # MB
    timeout = Column(Integer, default=30)        # seconds
    
    # Code and assets
    code_bundle_url = Column(String, nullable=True)
    code_checksum = Column(String, nullable=True)
    static_assets = Column(JSON, default=dict)
    
    # Environment
    environment_variables = Column(JSON, default=dict)
    secrets = Column(JSON, default=dict)
    
    # Network configuration
    custom_domains = Column(JSON, default=list)
    origin_servers = Column(JSON, default=list)
    
    # Security
    waf_rules = Column(JSON, default=list)
    rate_limits = Column(JSON, default=dict)
    ip_whitelist = Column(JSON, default=list)
    ip_blacklist = Column(JSON, default=list)
    
    # Status and monitoring
    status = Column(Enum(EdgeDeploymentStatus), default=EdgeDeploymentStatus.PENDING)
    deployment_url = Column(String, nullable=True)
    last_deployed_at = Column(DateTime, nullable=True)
    
    # Performance metrics
    requests_per_minute = Column(Float, default=0.0)
    average_response_time = Column(Float, default=0.0)
    error_rate = Column(Float, default=0.0)
    cache_hit_ratio = Column(Float, default=0.0)
    
    # Resource usage
    cpu_usage = Column(Float, default=0.0)
    memory_usage = Column(Float, default=0.0)
    bandwidth_usage = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<EdgeDeployment {self.name}>"

    @property
    def is_active(self):
        return self.status == EdgeDeploymentStatus.ACTIVE

    @property
    def edge_location_count(self):
        return len(self.edge_locations)

    @property
    def is_healthy(self):
        return self.status == EdgeDeploymentStatus.ACTIVE and self.error_rate < 0.01


class InfrastructureMetrics(Base):
    """Infrastructure metrics model for monitoring and analytics"""
    __tablename__ = "infrastructure_metrics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    resource_id = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=False, index=True)  # domain, ssl, cdn, lb, edge
    project_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Metrics data
    metrics = Column(JSON, default=dict)
    
    # Performance metrics
    latency = Column(Float, nullable=True)
    throughput = Column(Float, nullable=True)
    error_rate = Column(Float, nullable=True)
    availability = Column(Float, nullable=True)
    
    # Resource utilization
    cpu_usage = Column(Float, nullable=True)
    memory_usage = Column(Float, nullable=True)
    network_usage = Column(Float, nullable=True)
    storage_usage = Column(Float, nullable=True)
    
    # Cost metrics
    cost_per_hour = Column(Float, nullable=True)
    cost_accumulated = Column(Float, nullable=True)
    
    def __repr__(self):
        return f"<InfrastructureMetrics {self.resource_type}:{self.resource_id}>"