"""
Unit tests for infrastructure services
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.services.infrastructure.domain_service import DomainService
from src.services.infrastructure.ssl_service import SSLService
from src.services.infrastructure.cdn_service import CDNService
from src.services.infrastructure.load_balancer_service import LoadBalancerService
from src.services.infrastructure.edge_service import EdgeDeploymentService
from src.services.infrastructure.cost_analytics import CostCalculator, InfrastructureCostAnalytics
from src.models.infrastructure import (
    Domain, SSLCertificate, CDNConfiguration, LoadBalancer, EdgeDeployment,
    DomainStatus, SSLStatus, CDNStatus, LoadBalancerStatus, EdgeDeploymentStatus
)


class TestDomainService:
    """Test DomainService functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def domain_service(self, mock_db):
        """DomainService instance with mocked dependencies"""
        return DomainService(mock_db)
    
    @pytest.mark.asyncio
    async def test_add_domain_success(self, domain_service, mock_db):
        """Test successful domain addition"""
        # Setup
        domain_service._validate_domain_ownership = AsyncMock(return_value=True)
        domain_service._configure_dns_records = AsyncMock(return_value=True)
        domain_service._setup_monitoring = AsyncMock(return_value=True)
        
        mock_domain = Mock()
        mock_domain.id = "test-domain-id"
        mock_domain.domain_name = "example.com"
        mock_domain.status = DomainStatus.PENDING
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        
        # Execute
        with patch('src.models.infrastructure.Domain', return_value=mock_domain):
            result = await domain_service.add_domain(
                project_id="test-project",
                user_id="test-user",
                domain_name="example.com"
            )
        
        # Assert
        assert result == mock_domain
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_domain_dns_propagation(self, domain_service):
        """Test DNS propagation checking"""
        # Setup
        mock_domain = Mock()
        mock_domain.domain_name = "example.com"
        mock_domain.verification_token = "test-token"
        
        # Mock DNS lookup
        with patch('src.services.infrastructure.domain_service.dns.resolver.resolve') as mock_resolve:
            mock_resolve.return_value = [Mock(address="1.2.3.4")]
            
            # Execute
            result = await domain_service._check_dns_propagation(mock_domain)
            
            # Assert
            assert "propagation_percentage" in result
            assert result["propagation_percentage"] >= 0
    
    @pytest.mark.asyncio
    async def test_remove_domain_success(self, domain_service, mock_db):
        """Test successful domain removal"""
        # Setup
        mock_domain = Mock()
        mock_domain.id = "test-domain-id"
        mock_domain.user_id = "test-user"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_domain
        mock_db.delete.return_value = None
        mock_db.commit.return_value = None
        
        # Execute
        result = await domain_service.remove_domain("test-domain-id", "test-user")
        
        # Assert
        assert result is True
        mock_db.delete.assert_called_once_with(mock_domain)
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_remove_domain_not_found(self, domain_service, mock_db):
        """Test domain removal when domain not found"""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Execute & Assert
        with pytest.raises(ValueError, match="Domain not found"):
            await domain_service.remove_domain("nonexistent-id", "test-user")


class TestSSLService:
    """Test SSLService functionality"""
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def ssl_service(self, mock_db):
        return SSLService(mock_db)
    
    @pytest.mark.asyncio
    async def test_provision_certificate_letsencrypt(self, ssl_service, mock_db):
        """Test Let's Encrypt certificate provisioning"""
        # Setup
        ssl_service._validate_domain_ownership = AsyncMock(return_value=True)
        ssl_service._complete_acme_challenge = AsyncMock(return_value={
            "certificate": "test-cert",
            "private_key": "test-key",
            "chain": "test-chain"
        })
        ssl_service._setup_auto_renewal = AsyncMock(return_value=True)
        
        mock_cert = Mock()
        mock_cert.id = "test-cert-id"
        mock_cert.status = SSLStatus.PENDING
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        
        # Execute
        with patch('src.models.infrastructure.SSLCertificate', return_value=mock_cert):
            result = await ssl_service.provision_certificate(
                domain_id="test-domain",
                certificate_authority="letsencrypt"
            )
        
        # Assert
        assert result == mock_cert
        ssl_service._complete_acme_challenge.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_renew_certificate_success(self, ssl_service, mock_db):
        """Test certificate renewal"""
        # Setup
        mock_cert = Mock()
        mock_cert.id = "test-cert-id"
        mock_cert.needs_renewal = True
        mock_cert.certificate_authority = "letsencrypt"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_cert
        ssl_service._complete_acme_challenge = AsyncMock(return_value={
            "certificate": "new-cert",
            "private_key": "new-key"
        })
        
        # Execute
        result = await ssl_service.renew_certificate("test-cert-id")
        
        # Assert
        assert result is True
        ssl_service._complete_acme_challenge.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_certificate_expiry_check(self, ssl_service):
        """Test certificate expiry checking"""
        # Setup
        mock_cert = Mock()
        mock_cert.expires_at = datetime.utcnow() + timedelta(days=10)
        mock_cert.renewal_threshold_days = 30
        mock_cert.auto_renew = True
        
        # Execute
        needs_renewal = ssl_service._check_renewal_needed(mock_cert)
        
        # Assert
        assert needs_renewal is True


class TestCDNService:
    """Test CDNService functionality"""
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def cdn_service(self, mock_db):
        return CDNService(mock_db)
    
    @pytest.mark.asyncio
    async def test_create_cdn_configuration(self, cdn_service, mock_db):
        """Test CDN configuration creation"""
        # Setup
        cdn_service._setup_cdn_distribution = AsyncMock(return_value={
            "distribution_id": "test-dist-id",
            "cname": "test.cloudfront.net"
        })
        cdn_service._configure_cache_behaviors = AsyncMock(return_value=True)
        
        mock_config = Mock()
        mock_config.id = "test-config-id"
        mock_config.status = CDNStatus.PENDING
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        
        # Execute
        with patch('src.models.infrastructure.CDNConfiguration', return_value=mock_config):
            result = await cdn_service.create_cdn_configuration(
                domain_id="test-domain",
                provider="cloudflare",
                configuration={"default_ttl": 3600}
            )
        
        # Assert
        assert result == mock_config
        cdn_service._setup_cdn_distribution.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_purge_cache_success(self, cdn_service, mock_db):
        """Test cache purging"""
        # Setup
        mock_config = Mock()
        mock_config.provider = "cloudflare"
        mock_config.distribution_id = "test-dist-id"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_config
        cdn_service._purge_cloudflare_cache = AsyncMock(return_value=True)
        
        # Execute
        result = await cdn_service.purge_cache("test-config-id", ["/path1", "/path2"])
        
        # Assert
        assert result is True
        cdn_service._purge_cloudflare_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_cdn_analytics(self, cdn_service, mock_db):
        """Test CDN analytics retrieval"""
        # Setup
        mock_config = Mock()
        mock_config.provider = "cloudflare"
        mock_config.distribution_id = "test-dist-id"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_config
        cdn_service._get_cloudflare_analytics = AsyncMock(return_value={
            "requests": 1000,
            "bandwidth": 500,
            "cache_hit_ratio": 0.85
        })
        
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        # Execute
        result = await cdn_service.get_cdn_analytics("test-config-id", start_date, end_date)
        
        # Assert
        assert "requests" in result
        assert "bandwidth" in result
        assert "cache_hit_ratio" in result


class TestLoadBalancerService:
    """Test LoadBalancerService functionality"""
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def lb_service(self, mock_db):
        return LoadBalancerService(mock_db)
    
    @pytest.mark.asyncio
    async def test_create_load_balancer(self, lb_service, mock_db):
        """Test load balancer creation"""
        # Setup
        backend_servers = [
            {"ip": "192.168.1.10", "port": 80, "weight": 100},
            {"ip": "192.168.1.11", "port": 80, "weight": 100}
        ]
        
        lb_service._provision_load_balancer = AsyncMock(return_value={
            "external_ip": "203.0.113.1",
            "dns_name": "lb-test.elb.amazonaws.com"
        })
        lb_service._configure_health_checks = AsyncMock(return_value=True)
        
        mock_lb = Mock()
        mock_lb.id = "test-lb-id"
        mock_lb.status = LoadBalancerStatus.PENDING
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        
        # Execute
        with patch('src.models.infrastructure.LoadBalancer', return_value=mock_lb):
            result = await lb_service.create_load_balancer(
                domain_id="test-domain",
                name="test-lb",
                backend_servers=backend_servers,
                algorithm="round_robin"
            )
        
        # Assert
        assert result == mock_lb
        lb_service._provision_load_balancer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_monitoring(self, lb_service):
        """Test backend health monitoring"""
        # Setup
        backends = [
            {"ip": "192.168.1.10", "port": 80},
            {"ip": "192.168.1.11", "port": 80}
        ]
        
        lb_service._check_backend_health = AsyncMock(side_effect=[
            {"healthy": True, "response_time": 50},
            {"healthy": False, "error": "Connection timeout"}
        ])
        
        # Execute
        results = await lb_service._monitor_backend_health(backends)
        
        # Assert
        assert len(results) == 2
        assert results[0]["healthy"] is True
        assert results[1]["healthy"] is False
    
    @pytest.mark.asyncio
    async def test_add_backend_server(self, lb_service, mock_db):
        """Test adding backend server"""
        # Setup
        mock_lb = Mock()
        mock_lb.backend_servers = []
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_lb
        
        new_backend = {"ip": "192.168.1.12", "port": 80, "weight": 100}
        
        # Execute
        result = await lb_service.add_backend_server("test-lb-id", new_backend)
        
        # Assert
        assert result is True
        assert len(mock_lb.backend_servers) == 1


class TestEdgeDeploymentService:
    """Test EdgeDeploymentService functionality"""
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def edge_service(self, mock_db):
        return EdgeDeploymentService(mock_db)
    
    @pytest.mark.asyncio
    async def test_create_edge_deployment(self, edge_service, mock_db):
        """Test edge deployment creation"""
        # Setup
        code_bundle = b"test code bundle"
        
        edge_service._validate_code_bundle = AsyncMock(return_value=True)
        edge_service._deploy_to_edge_locations = AsyncMock(return_value={
            "deployed_locations": ["us-east-1", "eu-west-1"],
            "deployment_url": "https://test.edge.codeforge.app"
        })
        
        mock_deployment = Mock()
        mock_deployment.id = "test-deployment-id"
        mock_deployment.status = EdgeDeploymentStatus.PENDING
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        
        # Execute
        with patch('src.models.infrastructure.EdgeDeployment', return_value=mock_deployment):
            result = await edge_service.create_edge_deployment(
                project_id="test-project",
                user_id="test-user",
                name="test-deployment",
                code_bundle=code_bundle,
                runtime="nodejs",
                runtime_version="18"
            )
        
        # Assert
        assert result == mock_deployment
        edge_service._deploy_to_edge_locations.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scale_edge_deployment(self, edge_service, mock_db):
        """Test edge deployment scaling"""
        # Setup
        mock_deployment = Mock()
        mock_deployment.id = "test-deployment-id"
        mock_deployment.edge_locations = ["us-east-1", "eu-west-1"]
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_deployment
        edge_service._scale_deployment = AsyncMock(return_value=True)
        
        # Execute
        result = await edge_service.scale_edge_deployment("test-deployment-id", scale_factor=2.0)
        
        # Assert
        assert result is True
        edge_service._scale_deployment.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_deployment_logs(self, edge_service, mock_db):
        """Test deployment log retrieval"""
        # Setup
        mock_deployment = Mock()
        mock_deployment.id = "test-deployment-id"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_deployment
        edge_service._fetch_logs_from_locations = AsyncMock(return_value=[
            {"timestamp": "2023-01-01T12:00:00Z", "level": "INFO", "message": "Request processed"},
            {"timestamp": "2023-01-01T12:01:00Z", "level": "ERROR", "message": "Error occurred"}
        ])
        
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()
        
        # Execute
        result = await edge_service.get_deployment_logs(
            "test-deployment-id", 
            location_code="us-east-1",
            start_time=start_time,
            end_time=end_time
        )
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 2


class TestCostAnalytics:
    """Test cost analytics functionality"""
    
    def test_calculate_domain_cost(self):
        """Test domain cost calculation"""
        # Setup
        mock_domain = Mock()
        mock_domain.domain_name = "example.com"
        
        # Execute
        result = CostCalculator.calculate_domain_cost(mock_domain, days=30)
        
        # Assert
        assert "monthly_cost" in result
        assert "period_cost" in result
        assert "daily_cost" in result
        assert result["monthly_cost"] >= 0
    
    def test_calculate_cdn_cost_with_bandwidth(self):
        """Test CDN cost calculation with bandwidth usage"""
        # Setup
        mock_cdn = Mock()
        mock_cdn.waf_enabled = True
        mock_cdn.ddos_protection = True
        mock_cdn.bandwidth_usage = {"total_gb": 200}
        
        # Execute
        result = CostCalculator.calculate_cdn_cost(mock_cdn, days=30)
        
        # Assert
        assert result["cost_breakdown"]["total_gb"] == 200
        assert result["cost_breakdown"]["billable_gb"] == 100  # 200 - 100 free tier
        assert result["cost_breakdown"]["bandwidth"] > 0
    
    def test_calculate_edge_deployment_cost(self):
        """Test edge deployment cost calculation"""
        # Setup
        mock_edge = Mock()
        mock_edge.edge_location_count = 5
        mock_edge.memory_limit = 512
        mock_edge.requests_per_minute = 100
        mock_edge.bandwidth_usage = {"total_gb": 50}
        
        # Execute
        result = CostCalculator.calculate_edge_deployment_cost(mock_edge, days=30)
        
        # Assert
        assert result["cost_breakdown"]["billable_regions"] == 2  # 5 - 3 free
        assert result["cost_breakdown"]["memory"] > 0
        assert result["cost_breakdown"]["traffic"] > 0
    
    @pytest.mark.asyncio
    async def test_cost_optimization_suggestions(self):
        """Test cost optimization suggestion generation"""
        # Setup
        mock_db = Mock(spec=Session)
        analytics = InfrastructureCostAnalytics(mock_db)
        
        # Mock high bandwidth CDN
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            [],  # domains
            [],  # ssl_certs
            [Mock(bandwidth_usage={"total_gb": 600})],  # cdn_configs (high bandwidth)
            [],  # load_balancers
            []   # edge_deployments
        ]
        
        # Execute
        suggestions = await analytics.get_cost_optimization_suggestions("test-project", "test-user")
        
        # Assert
        assert len(suggestions) > 0
        assert any(s["type"] == "cdn_optimization" for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_cost_alerts_budget_exceeded(self):
        """Test cost alert generation when budget is exceeded"""
        # Setup
        mock_db = Mock(spec=Session)
        analytics = InfrastructureCostAnalytics(mock_db)
        
        # Mock expensive infrastructure
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            [],  # domains
            [],  # ssl_certs
            [],  # cdn_configs
            [],  # load_balancers
            [Mock(  # edge_deployments with high cost
                edge_location_count=10,
                memory_limit=2048,
                requests_per_minute=1000,
                bandwidth_usage={"total_gb": 1000}
            )]
        ]
        
        with patch.object(analytics, 'get_project_cost_summary') as mock_summary:
            mock_summary.return_value = {
                "monthly_projection": 150.0,
                "total_cost": 150.0,
                "components": {
                    "domains": {"total_cost": 0},
                    "ssl_certificates": {"total_cost": 0},
                    "cdn_configurations": {"total_cost": 0},
                    "load_balancers": {"total_cost": 0},
                    "edge_deployments": {"total_cost": 150.0}
                }
            }
            
            # Execute
            alerts = await analytics.get_cost_alerts("test-project", "test-user", budget_limit=100.0)
            
            # Assert
            assert len(alerts) > 0
            assert any(a["type"] == "budget_exceeded" for a in alerts)


if __name__ == "__main__":
    pytest.main([__file__])