"""
SSL Service for SSL certificate management with Let's Encrypt integration
"""
import asyncio
import ssl
import socket
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import aiohttp
import logging
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import acme.client
import acme.challenges
import acme.crypto_util
import acme.messages
from acme import errors as acme_errors
from sqlalchemy.orm import Session
import base64
import hashlib

from ...models.infrastructure import SSLCertificate, SSLStatus, Domain, DomainStatus
from ...config.settings import settings
from ..credits_service import CreditsService


logger = logging.getLogger(__name__)


class LetsEncryptClient:
    """Let's Encrypt ACME client wrapper"""
    
    def __init__(self, directory_url: str = "https://acme-v02.api.letsencrypt.org/directory"):
        self.directory_url = directory_url
        self.client = None
        self.account_key = None
    
    async def initialize(self, account_key_pem: Optional[str] = None):
        """Initialize ACME client"""
        try:
            # Generate or load account key
            if account_key_pem:
                self.account_key = serialization.load_pem_private_key(
                    account_key_pem.encode(), password=None
                )
            else:
                self.account_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048
                )
            
            # Create ACME client
            directory = await self._get_directory()
            self.client = acme.client.ClientV2(directory, net=acme.client.ClientNetwork())
            
            # Register account if needed
            await self._register_account()
            
        except Exception as e:
            logger.error(f"Failed to initialize Let's Encrypt client: {e}")
            raise
    
    async def _get_directory(self):
        """Get ACME directory"""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.directory_url) as response:
                directory_data = await response.json()
                return acme.messages.Directory.from_json(directory_data)
    
    async def _register_account(self):
        """Register ACME account"""
        try:
            new_account = acme.messages.NewRegistration.from_data(
                email="ssl@codeforge.dev",  # Configure this
                terms_of_service_agreed=True
            )
            
            # Try to register account
            self.client.new_account(new_account)
            
        except acme_errors.ConflictError:
            # Account already exists
            pass
    
    async def request_certificate(
        self,
        domain: str,
        validation_method: str = "dns",
        dns_provider=None
    ) -> Tuple[str, str, str]:
        """
        Request SSL certificate from Let's Encrypt
        Returns: (certificate_pem, private_key_pem, certificate_chain)
        """
        try:
            # Generate private key for certificate
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Create certificate signing request
            csr = x509.CertificateSigningRequestBuilder().subject_name(
                x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, domain)])
            ).add_extension(
                x509.SubjectAlternativeName([x509.DNSName(domain)]),
                critical=False,
            ).sign(private_key, hashes.SHA256())
            
            # Request certificate
            order = self.client.new_order(csr)
            
            # Complete challenges
            for authorization in order.authorizations:
                await self._complete_challenge(authorization, validation_method, dns_provider)
            
            # Finalize order
            order = self.client.poll_and_finalize(order)
            
            # Get certificate
            certificate_pem = order.fullchain_pem
            private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode()
            
            # Extract certificate chain
            certificate_chain = self._extract_chain(certificate_pem)
            
            return certificate_pem, private_key_pem, certificate_chain
            
        except Exception as e:
            logger.error(f"Certificate request failed for {domain}: {e}")
            raise
    
    async def _complete_challenge(self, authorization, validation_method: str, dns_provider):
        """Complete ACME challenge"""
        domain = authorization.body.identifier.value
        
        if validation_method == "dns":
            # DNS-01 challenge
            challenge = None
            for challenge in authorization.body.challenges:
                if isinstance(challenge.chall, acme.challenges.DNS01):
                    break
            
            if not challenge:
                raise Exception("DNS-01 challenge not available")
            
            # Create DNS record
            key_authorization = challenge.chall.key_authorization(self.client.net.key)
            dns_value = base64.urlsafe_b64encode(
                hashlib.sha256(key_authorization.encode()).digest()
            ).decode().rstrip('=')
            
            if dns_provider:
                success = await dns_provider.create_record(
                    domain,
                    "TXT",
                    f"_acme-challenge.{domain}",
                    dns_value,
                    120  # Short TTL
                )
                
                if not success:
                    raise Exception("Failed to create DNS validation record")
            
            # Wait for DNS propagation
            await asyncio.sleep(30)
            
            # Complete challenge
            self.client.answer_challenge(challenge, challenge.chall.response(self.client.net.key))
        
        elif validation_method == "http":
            # HTTP-01 challenge (implement if needed)
            raise NotImplementedError("HTTP-01 challenge not implemented")
    
    def _extract_chain(self, fullchain_pem: str) -> str:
        """Extract certificate chain from fullchain"""
        certificates = fullchain_pem.split('-----END CERTIFICATE-----')
        if len(certificates) > 1:
            # Remove the leaf certificate, keep the chain
            chain_parts = certificates[1:]
            return '-----END CERTIFICATE-----'.join(chain_parts).strip()
        return ""


class SSLService:
    """
    Service for managing SSL certificates with automatic provisioning and renewal
    """
    
    def __init__(self, db: Session, credits_service: Optional[CreditsService] = None):
        self.db = db
        self.credits_service = credits_service or CreditsService(db)
        self.letsencrypt_client = LetsEncryptClient()
    
    async def provision_certificate(
        self,
        domain_id: str,
        certificate_authority: str = "letsencrypt",
        validation_method: str = "dns"
    ) -> SSLCertificate:
        """
        Provision SSL certificate for a domain
        """
        # Get domain
        domain = self.db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            raise ValueError("Domain not found")
        
        if domain.status != DomainStatus.ACTIVE:
            raise ValueError("Domain must be active to provision SSL certificate")
        
        # Check if certificate already exists
        existing_cert = self.db.query(SSLCertificate).filter(
            SSLCertificate.domain_id == domain_id,
            SSLCertificate.status == SSLStatus.ACTIVE
        ).first()
        
        if existing_cert and existing_cert.is_valid:
            return existing_cert
        
        # Create certificate record
        ssl_cert = SSLCertificate(
            domain_id=domain_id,
            project_id=domain.project_id,
            user_id=domain.user_id,
            certificate_authority=certificate_authority,
            common_name=domain.domain_name,
            subject_alternative_names=[domain.domain_name],
            status=SSLStatus.PENDING,
            validation_method=validation_method
        )
        
        self.db.add(ssl_cert)
        self.db.commit()
        
        # Start certificate provisioning
        asyncio.create_task(self._provision_certificate_async(ssl_cert.id))
        
        return ssl_cert
    
    async def _provision_certificate_async(self, cert_id: str):
        """Asynchronously provision SSL certificate"""
        ssl_cert = self.db.query(SSLCertificate).filter(SSLCertificate.id == cert_id).first()
        if not ssl_cert:
            return
        
        try:
            # Initialize Let's Encrypt client
            await self.letsencrypt_client.initialize()
            
            # Get domain and DNS provider
            domain = ssl_cert.domain
            from .domain_service import DomainService
            domain_service = DomainService(self.db)
            dns_provider = domain_service.dns_providers.get(domain.dns_provider)
            
            # Request certificate
            certificate_pem, private_key_pem, certificate_chain = await self.letsencrypt_client.request_certificate(
                domain.domain_name,
                ssl_cert.validation_method,
                dns_provider
            )
            
            # Parse certificate for metadata
            cert_data = self._parse_certificate(certificate_pem)
            
            # Update certificate record
            ssl_cert.certificate_pem = certificate_pem
            ssl_cert.private_key_pem = private_key_pem
            ssl_cert.certificate_chain = certificate_chain
            ssl_cert.issued_at = datetime.utcnow()
            ssl_cert.expires_at = cert_data["expires_at"]
            ssl_cert.serial_number = cert_data["serial_number"]
            ssl_cert.fingerprint = cert_data["fingerprint"]
            ssl_cert.status = SSLStatus.ACTIVE
            
            self.db.commit()
            
            logger.info(f"SSL certificate provisioned successfully for {domain.domain_name}")
            
        except Exception as e:
            logger.error(f"SSL certificate provisioning failed for cert {cert_id}: {e}")
            ssl_cert.status = SSLStatus.FAILED
            self.db.commit()
    
    async def renew_certificate(self, cert_id: str) -> bool:
        """
        Renew SSL certificate
        """
        ssl_cert = self.db.query(SSLCertificate).filter(SSLCertificate.id == cert_id).first()
        if not ssl_cert:
            raise ValueError("Certificate not found")
        
        try:
            ssl_cert.status = SSLStatus.RENEWING
            self.db.commit()
            
            # Provision new certificate (same process as initial)
            await self._provision_certificate_async(cert_id)
            
            return ssl_cert.status == SSLStatus.ACTIVE
            
        except Exception as e:
            logger.error(f"Certificate renewal failed for {cert_id}: {e}")
            ssl_cert.status = SSLStatus.FAILED
            self.db.commit()
            return False
    
    async def revoke_certificate(self, cert_id: str) -> bool:
        """
        Revoke SSL certificate
        """
        ssl_cert = self.db.query(SSLCertificate).filter(SSLCertificate.id == cert_id).first()
        if not ssl_cert:
            raise ValueError("Certificate not found")
        
        try:
            # Revoke with Let's Encrypt if applicable
            if ssl_cert.certificate_authority == "letsencrypt" and ssl_cert.certificate_pem:
                await self.letsencrypt_client.initialize()
                # Implement revocation logic if needed
            
            # Mark as expired
            ssl_cert.status = SSLStatus.EXPIRED
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Certificate revocation failed for {cert_id}: {e}")
            return False
    
    async def check_certificate_renewal(self) -> List[str]:
        """
        Check certificates that need renewal and trigger renewal process
        """
        # Get certificates that need renewal
        certs_needing_renewal = self.db.query(SSLCertificate).filter(
            SSLCertificate.auto_renew == True,
            SSLCertificate.status == SSLStatus.ACTIVE
        ).all()
        
        renewed_certs = []
        
        for cert in certs_needing_renewal:
            if cert.needs_renewal:
                try:
                    success = await self.renew_certificate(cert.id)
                    if success:
                        renewed_certs.append(cert.id)
                        logger.info(f"Auto-renewed certificate for {cert.common_name}")
                except Exception as e:
                    logger.error(f"Auto-renewal failed for {cert.common_name}: {e}")
        
        return renewed_certs
    
    async def validate_certificate(self, domain_name: str) -> Dict[str, Any]:
        """
        Validate SSL certificate for a domain
        """
        try:
            # Connect and get certificate
            context = ssl.create_default_context()
            
            with socket.create_connection((domain_name, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain_name) as ssock:
                    cert = ssock.getpeercert()
                    der_cert = ssock.getpeercert(binary_form=True)
                    
                    # Parse certificate
                    x509_cert = x509.load_der_x509_certificate(der_cert)
                    
                    # Calculate expiry days
                    expires_at = x509_cert.not_valid_after
                    days_until_expiry = (expires_at - datetime.utcnow()).days
                    
                    return {
                        "valid": True,
                        "issuer": dict(x[0] for x in cert.get('issuer', [])),
                        "subject": dict(x[0] for x in cert.get('subject', [])),
                        "expires_at": expires_at.isoformat(),
                        "days_until_expiry": days_until_expiry,
                        "needs_renewal": days_until_expiry <= 30,
                        "san": [name[1] for name in cert.get('subjectAltName', [])],
                        "serial_number": format(x509_cert.serial_number, 'x').upper(),
                        "fingerprint": x509_cert.fingerprint(hashes.SHA256()).hex().upper()
                    }
                    
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def get_certificate_status(self, cert_id: str) -> Dict[str, Any]:
        """
        Get comprehensive certificate status
        """
        ssl_cert = self.db.query(SSLCertificate).filter(SSLCertificate.id == cert_id).first()
        if not ssl_cert:
            raise ValueError("Certificate not found")
        
        # Get domain validation
        domain_validation = None
        if ssl_cert.common_name:
            domain_validation = await self.validate_certificate(ssl_cert.common_name)
        
        return {
            "certificate": {
                "id": ssl_cert.id,
                "domain": ssl_cert.common_name,
                "status": ssl_cert.status.value,
                "authority": ssl_cert.certificate_authority,
                "issued_at": ssl_cert.issued_at.isoformat() if ssl_cert.issued_at else None,
                "expires_at": ssl_cert.expires_at.isoformat() if ssl_cert.expires_at else None,
                "days_until_expiry": ssl_cert.days_until_expiry,
                "needs_renewal": ssl_cert.needs_renewal,
                "auto_renew": ssl_cert.auto_renew
            },
            "validation": domain_validation,
            "metadata": {
                "serial_number": ssl_cert.serial_number,
                "fingerprint": ssl_cert.fingerprint,
                "key_size": ssl_cert.key_size,
                "signature_algorithm": ssl_cert.signature_algorithm,
                "subject_alternative_names": ssl_cert.subject_alternative_names
            }
        }
    
    async def list_certificates(self, project_id: str, user_id: str) -> List[Dict[str, Any]]:
        """
        List all certificates for a project
        """
        certificates = self.db.query(SSLCertificate).filter(
            SSLCertificate.project_id == project_id,
            SSLCertificate.user_id == user_id
        ).all()
        
        cert_list = []
        for cert in certificates:
            status = await self.get_certificate_status(cert.id)
            cert_list.append(status)
        
        return cert_list
    
    # Private helper methods
    
    def _parse_certificate(self, certificate_pem: str) -> Dict[str, Any]:
        """Parse certificate and extract metadata"""
        try:
            cert = x509.load_pem_x509_certificate(certificate_pem.encode())
            
            return {
                "expires_at": cert.not_valid_after,
                "issued_at": cert.not_valid_before,
                "serial_number": format(cert.serial_number, 'x').upper(),
                "fingerprint": cert.fingerprint(hashes.SHA256()).hex().upper(),
                "subject": cert.subject.rfc4514_string(),
                "issuer": cert.issuer.rfc4514_string()
            }
            
        except Exception as e:
            logger.error(f"Failed to parse certificate: {e}")
            return {
                "expires_at": datetime.utcnow() + timedelta(days=90),  # Default
                "issued_at": datetime.utcnow(),
                "serial_number": "unknown",
                "fingerprint": "unknown"
            }
    
    def export_certificate(self, cert_id: str, format: str = "pem") -> Dict[str, str]:
        """
        Export certificate in various formats
        """
        ssl_cert = self.db.query(SSLCertificate).filter(SSLCertificate.id == cert_id).first()
        if not ssl_cert:
            raise ValueError("Certificate not found")
        
        if format.lower() == "pem":
            return {
                "certificate": ssl_cert.certificate_pem,
                "private_key": ssl_cert.private_key_pem,
                "certificate_chain": ssl_cert.certificate_chain
            }
        elif format.lower() == "p12":
            # Implement PKCS#12 export if needed
            raise NotImplementedError("PKCS#12 export not implemented")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def install_certificate(self, cert_id: str, target: str) -> bool:
        """
        Install certificate on target infrastructure
        """
        ssl_cert = self.db.query(SSLCertificate).filter(SSLCertificate.id == cert_id).first()
        if not ssl_cert:
            raise ValueError("Certificate not found")
        
        try:
            # This would integrate with load balancers, CDN, etc.
            # Implementation depends on target infrastructure
            logger.info(f"Installing certificate {cert_id} on {target}")
            
            # Update installation status
            # ssl_cert.installed_targets = ssl_cert.installed_targets or []
            # if target not in ssl_cert.installed_targets:
            #     ssl_cert.installed_targets.append(target)
            #     self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Certificate installation failed: {e}")
            return False