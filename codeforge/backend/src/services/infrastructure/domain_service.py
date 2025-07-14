"""
Domain Service for custom domain management
"""
import asyncio
import socket
import ssl
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import dns.resolver
import dns.query
import dns.zone
from sqlalchemy.orm import Session
import aiohttp
import logging

from ...models.infrastructure import Domain, DomainStatus
from ...config.settings import settings
from ..credits_service import CreditsService


logger = logging.getLogger(__name__)


class DNSProvider:
    """Base DNS provider interface"""
    
    async def create_record(self, domain: str, record_type: str, name: str, value: str, ttl: int = 300) -> bool:
        raise NotImplementedError
    
    async def delete_record(self, domain: str, record_id: str) -> bool:
        raise NotImplementedError
    
    async def list_records(self, domain: str) -> List[Dict[str, Any]]:
        raise NotImplementedError
    
    async def update_nameservers(self, domain: str, nameservers: List[str]) -> bool:
        raise NotImplementedError


class CloudflareDNSProvider(DNSProvider):
    """Cloudflare DNS provider implementation"""
    
    def __init__(self, api_token: str, zone_id: Optional[str] = None):
        self.api_token = api_token
        self.zone_id = zone_id
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to Cloudflare API"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}{endpoint}"
            async with session.request(method, url, headers=self.headers, json=data) as response:
                result = await response.json()
                if not result.get("success", False):
                    errors = result.get("errors", [])
                    raise Exception(f"Cloudflare API error: {errors}")
                return result.get("result", {})
    
    async def get_zone_id(self, domain: str) -> Optional[str]:
        """Get zone ID for domain"""
        if self.zone_id:
            return self.zone_id
        
        try:
            result = await self._make_request("GET", f"/zones?name={domain}")
            if result and len(result) > 0:
                return result[0]["id"]
        except Exception as e:
            logger.error(f"Error getting zone ID for {domain}: {e}")
        return None
    
    async def create_record(self, domain: str, record_type: str, name: str, value: str, ttl: int = 300) -> bool:
        """Create DNS record"""
        try:
            zone_id = await self.get_zone_id(domain)
            if not zone_id:
                return False
            
            data = {
                "type": record_type.upper(),
                "name": name,
                "content": value,
                "ttl": ttl
            }
            
            await self._make_request("POST", f"/zones/{zone_id}/dns_records", data)
            return True
        except Exception as e:
            logger.error(f"Error creating DNS record: {e}")
            return False
    
    async def delete_record(self, domain: str, record_id: str) -> bool:
        """Delete DNS record"""
        try:
            zone_id = await self.get_zone_id(domain)
            if not zone_id:
                return False
            
            await self._make_request("DELETE", f"/zones/{zone_id}/dns_records/{record_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting DNS record: {e}")
            return False
    
    async def list_records(self, domain: str) -> List[Dict[str, Any]]:
        """List DNS records"""
        try:
            zone_id = await self.get_zone_id(domain)
            if not zone_id:
                return []
            
            result = await self._make_request("GET", f"/zones/{zone_id}/dns_records")
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Error listing DNS records: {e}")
            return []
    
    async def update_nameservers(self, domain: str, nameservers: List[str]) -> bool:
        """Update nameservers (this requires domain registrar API, not Cloudflare)"""
        # This would typically be done through the domain registrar's API
        logger.info(f"Nameserver update requested for {domain}: {nameservers}")
        return True


class DomainService:
    """
    Service for managing custom domains, DNS configuration, and verification
    """
    
    def __init__(self, db: Session, credits_service: Optional[CreditsService] = None):
        self.db = db
        self.credits_service = credits_service or CreditsService(db)
        self.dns_providers = self._initialize_dns_providers()
    
    def _initialize_dns_providers(self) -> Dict[str, DNSProvider]:
        """Initialize DNS providers"""
        providers = {}
        
        # Cloudflare provider
        if hasattr(settings, 'CLOUDFLARE_API_TOKEN'):
            providers['cloudflare'] = CloudflareDNSProvider(settings.CLOUDFLARE_API_TOKEN)
        
        return providers
    
    async def add_domain(
        self,
        project_id: str,
        user_id: str,
        domain_name: str,
        dns_provider: str = "cloudflare"
    ) -> Domain:
        """
        Add a new custom domain to a project
        """
        # Validate domain format
        if not self._is_valid_domain(domain_name):
            raise ValueError(f"Invalid domain format: {domain_name}")
        
        # Check if domain already exists
        existing = self.db.query(Domain).filter(Domain.domain_name == domain_name).first()
        if existing:
            raise ValueError(f"Domain {domain_name} is already registered")
        
        # Parse domain components
        subdomain, root_domain = self._parse_domain(domain_name)
        
        # Create domain record
        domain = Domain(
            project_id=project_id,
            user_id=user_id,
            domain_name=domain_name,
            subdomain=subdomain,
            root_domain=root_domain,
            dns_provider=dns_provider,
            status=DomainStatus.PENDING,
            verification_token=self._generate_verification_token()
        )
        
        self.db.add(domain)
        self.db.commit()
        
        # Start verification process
        asyncio.create_task(self._start_verification_process(domain.id))
        
        return domain
    
    async def verify_domain(self, domain_id: str) -> bool:
        """
        Verify domain ownership and configure DNS
        """
        domain = self.db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            raise ValueError("Domain not found")
        
        try:
            # Check DNS propagation
            propagation_status = await self._check_dns_propagation(domain)
            domain.propagation_status = propagation_status
            
            # Verify TXT record for domain ownership
            ownership_verified = await self._verify_domain_ownership(domain)
            
            if ownership_verified and propagation_status.get("all_propagated", False):
                domain.status = DomainStatus.ACTIVE
                domain.verified_at = datetime.utcnow()
                
                # Configure DNS records
                await self._configure_dns_records(domain)
                
                self.db.commit()
                return True
            
            self.db.commit()
            return False
            
        except Exception as e:
            logger.error(f"Domain verification failed for {domain.domain_name}: {e}")
            domain.status = DomainStatus.FAILED
            self.db.commit()
            return False
    
    async def remove_domain(self, domain_id: str, user_id: str) -> bool:
        """
        Remove a domain and clean up DNS records
        """
        domain = self.db.query(Domain).filter(
            Domain.id == domain_id,
            Domain.user_id == user_id
        ).first()
        
        if not domain:
            raise ValueError("Domain not found")
        
        try:
            # Clean up DNS records
            await self._cleanup_dns_records(domain)
            
            # Delete domain from database
            self.db.delete(domain)
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove domain {domain.domain_name}: {e}")
            return False
    
    async def update_dns_records(self, domain_id: str, records: List[Dict[str, Any]]) -> bool:
        """
        Update DNS records for a domain
        """
        domain = self.db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            raise ValueError("Domain not found")
        
        if domain.status != DomainStatus.ACTIVE:
            raise ValueError("Domain must be active to update DNS records")
        
        dns_provider = self.dns_providers.get(domain.dns_provider)
        if not dns_provider:
            raise ValueError(f"DNS provider {domain.dns_provider} not configured")
        
        try:
            updated_records = []
            
            for record in records:
                success = await dns_provider.create_record(
                    domain.root_domain,
                    record["type"],
                    record["name"],
                    record["value"],
                    record.get("ttl", 300)
                )
                
                if success:
                    updated_records.append(record)
            
            # Update domain DNS records
            domain.dns_records = {
                "records": updated_records,
                "last_updated": datetime.utcnow().isoformat()
            }
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update DNS records for {domain.domain_name}: {e}")
            return False
    
    async def get_domain_status(self, domain_id: str) -> Dict[str, Any]:
        """
        Get comprehensive domain status and health information
        """
        domain = self.db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            raise ValueError("Domain not found")
        
        # Get DNS status
        dns_status = await self._check_dns_propagation(domain)
        
        # Get SSL status
        ssl_status = await self._check_ssl_status(domain.domain_name)
        
        # Get performance metrics
        performance = await self._get_domain_performance(domain.domain_name)
        
        return {
            "domain": {
                "id": domain.id,
                "name": domain.domain_name,
                "status": domain.status.value,
                "verified": domain.is_verified,
                "created_at": domain.created_at.isoformat(),
                "verified_at": domain.verified_at.isoformat() if domain.verified_at else None
            },
            "dns": dns_status,
            "ssl": ssl_status,
            "performance": performance,
            "configuration": {
                "redirect_https": domain.redirect_to_https,
                "www_redirect": domain.www_redirect,
                "custom_headers": domain.custom_headers
            }
        }
    
    async def list_domains(self, project_id: str, user_id: str) -> List[Dict[str, Any]]:
        """
        List all domains for a project
        """
        domains = self.db.query(Domain).filter(
            Domain.project_id == project_id,
            Domain.user_id == user_id
        ).all()
        
        domain_list = []
        for domain in domains:
            status = await self.get_domain_status(domain.id)
            domain_list.append(status)
        
        return domain_list
    
    # Private helper methods
    
    def _is_valid_domain(self, domain: str) -> bool:
        """Validate domain format"""
        if not domain or len(domain) > 253:
            return False
        
        parts = domain.split('.')
        if len(parts) < 2:
            return False
        
        for part in parts:
            if not part or len(part) > 63:
                return False
            if not part.replace('-', '').replace('_', '').isalnum():
                return False
        
        return True
    
    def _parse_domain(self, domain: str) -> Tuple[Optional[str], str]:
        """Parse domain into subdomain and root domain"""
        parts = domain.split('.')
        
        if len(parts) == 2:
            return None, domain
        elif len(parts) > 2:
            subdomain = '.'.join(parts[:-2])
            root_domain = '.'.join(parts[-2:])
            return subdomain, root_domain
        
        return None, domain
    
    def _generate_verification_token(self) -> str:
        """Generate domain verification token"""
        import secrets
        return f"codeforge-verify-{secrets.token_urlsafe(32)}"
    
    async def _start_verification_process(self, domain_id: str):
        """Start background verification process"""
        # Wait a bit for DNS propagation
        await asyncio.sleep(10)
        
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            try:
                verified = await self.verify_domain(domain_id)
                if verified:
                    logger.info(f"Domain {domain_id} verified successfully")
                    break
                
                # Wait before next attempt
                await asyncio.sleep(60)  # Check every minute
                attempt += 1
                
            except Exception as e:
                logger.error(f"Verification attempt {attempt} failed for domain {domain_id}: {e}")
                attempt += 1
                await asyncio.sleep(60)
        
        if attempt >= max_attempts:
            # Mark as failed after max attempts
            domain = self.db.query(Domain).filter(Domain.id == domain_id).first()
            if domain:
                domain.status = DomainStatus.FAILED
                self.db.commit()
    
    async def _check_dns_propagation(self, domain: Domain) -> Dict[str, Any]:
        """Check DNS propagation status"""
        try:
            # Check different DNS servers
            dns_servers = [
                "8.8.8.8",  # Google
                "1.1.1.1",  # Cloudflare
                "208.67.222.222",  # OpenDNS
                "8.26.56.26"  # Comodo
            ]
            
            propagation_results = {}
            
            for dns_server in dns_servers:
                try:
                    resolver = dns.resolver.Resolver()
                    resolver.nameservers = [dns_server]
                    
                    # Check A record
                    answers = resolver.resolve(domain.domain_name, 'A')
                    propagation_results[dns_server] = {
                        "resolved": True,
                        "records": [str(answer) for answer in answers]
                    }
                except Exception:
                    propagation_results[dns_server] = {
                        "resolved": False,
                        "records": []
                    }
            
            # Calculate propagation percentage
            resolved_count = sum(1 for result in propagation_results.values() if result["resolved"])
            propagation_percentage = (resolved_count / len(dns_servers)) * 100
            
            return {
                "propagation_percentage": propagation_percentage,
                "all_propagated": propagation_percentage == 100,
                "dns_servers": propagation_results,
                "last_checked": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"DNS propagation check failed: {e}")
            return {
                "propagation_percentage": 0,
                "all_propagated": False,
                "error": str(e),
                "last_checked": datetime.utcnow().isoformat()
            }
    
    async def _verify_domain_ownership(self, domain: Domain) -> bool:
        """Verify domain ownership via TXT record"""
        try:
            resolver = dns.resolver.Resolver()
            txt_name = f"_codeforge-challenge.{domain.domain_name}"
            
            answers = resolver.resolve(txt_name, 'TXT')
            for answer in answers:
                txt_value = str(answer).strip('"')
                if txt_value == domain.verification_token:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Domain ownership verification failed: {e}")
            return False
    
    async def _configure_dns_records(self, domain: Domain):
        """Configure default DNS records for domain"""
        dns_provider = self.dns_providers.get(domain.dns_provider)
        if not dns_provider:
            return
        
        try:
            # Default A record pointing to CodeForge infrastructure
            await dns_provider.create_record(
                domain.root_domain,
                "A",
                domain.domain_name,
                settings.INFRASTRUCTURE_IP,  # Configure this in settings
                300
            )
            
            # CNAME for www subdomain
            if not domain.subdomain:  # Only for root domains
                await dns_provider.create_record(
                    domain.root_domain,
                    "CNAME",
                    f"www.{domain.domain_name}",
                    domain.domain_name,
                    300
                )
            
        except Exception as e:
            logger.error(f"Failed to configure DNS records: {e}")
    
    async def _cleanup_dns_records(self, domain: Domain):
        """Clean up DNS records when removing domain"""
        dns_provider = self.dns_providers.get(domain.dns_provider)
        if not dns_provider:
            return
        
        try:
            # Get all records for the domain
            records = await dns_provider.list_records(domain.root_domain)
            
            # Delete records related to this domain
            for record in records:
                if record.get("name") == domain.domain_name or \
                   record.get("name", "").endswith(f".{domain.domain_name}"):
                    await dns_provider.delete_record(domain.root_domain, record["id"])
            
        except Exception as e:
            logger.error(f"Failed to cleanup DNS records: {e}")
    
    async def _check_ssl_status(self, domain_name: str) -> Dict[str, Any]:
        """Check SSL certificate status"""
        try:
            # Check SSL certificate
            context = ssl.create_default_context()
            
            with socket.create_connection((domain_name, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain_name) as ssock:
                    cert = ssock.getpeercert()
                    
                    return {
                        "has_ssl": True,
                        "issuer": dict(x[0] for x in cert.get('issuer', [])),
                        "subject": dict(x[0] for x in cert.get('subject', [])),
                        "expires": cert.get('notAfter'),
                        "san": cert.get('subjectAltName', [])
                    }
        except Exception as e:
            return {
                "has_ssl": False,
                "error": str(e)
            }
    
    async def _get_domain_performance(self, domain_name: str) -> Dict[str, Any]:
        """Get domain performance metrics"""
        try:
            # Simple performance check
            start_time = datetime.utcnow()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://{domain_name}", timeout=30) as response:
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds() * 1000
                    
                    return {
                        "response_time_ms": response_time,
                        "status_code": response.status,
                        "available": response.status < 500,
                        "last_checked": end_time.isoformat()
                    }
        except Exception as e:
            return {
                "response_time_ms": None,
                "status_code": None,
                "available": False,
                "error": str(e),
                "last_checked": datetime.utcnow().isoformat()
            }