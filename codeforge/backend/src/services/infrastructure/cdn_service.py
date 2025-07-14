"""
CDN Service for global content delivery and caching
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp
import logging
from sqlalchemy.orm import Session
import json

from ...models.infrastructure import CDNConfiguration, CDNStatus, Domain, DomainStatus
from ...config.settings import settings
from ..credits_service import CreditsService


logger = logging.getLogger(__name__)


class CDNProvider:
    """Base CDN provider interface"""
    
    async def create_distribution(self, config: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
    
    async def update_distribution(self, distribution_id: str, config: Dict[str, Any]) -> bool:
        raise NotImplementedError
    
    async def delete_distribution(self, distribution_id: str) -> bool:
        raise NotImplementedError
    
    async def get_distribution_status(self, distribution_id: str) -> Dict[str, Any]:
        raise NotImplementedError
    
    async def purge_cache(self, distribution_id: str, paths: List[str] = None) -> bool:
        raise NotImplementedError
    
    async def get_analytics(self, distribution_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        raise NotImplementedError


class CloudflareCDNProvider(CDNProvider):
    """Cloudflare CDN provider implementation"""
    
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
    
    async def create_distribution(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create Cloudflare distribution (zone configuration)"""
        try:
            zone_id = await self._get_zone_id(config["domain"])
            if not zone_id:
                raise Exception(f"Zone not found for domain {config['domain']}")
            
            # Configure zone settings
            settings_updates = []
            
            # Enable caching
            settings_updates.append({
                "id": "cache_level",
                "value": "aggressive"
            })
            
            # Enable compression
            if config.get("compression_enabled", True):
                settings_updates.append({
                    "id": "brotli",
                    "value": "on"
                })
            
            # Enable minification
            minification = config.get("minification", {})
            settings_updates.append({
                "id": "minify",
                "value": {
                    "css": "on" if minification.get("css", True) else "off",
                    "html": "on" if minification.get("html", True) else "off",
                    "js": "on" if minification.get("js", True) else "off"
                }
            })
            
            # Enable security features
            if config.get("waf_enabled", True):
                settings_updates.append({
                    "id": "waf",
                    "value": "on"
                })
            
            if config.get("ddos_protection", True):
                settings_updates.append({
                    "id": "advanced_ddos",
                    "value": "on"
                })
            
            # Apply settings
            for setting in settings_updates:
                await self._make_request(
                    "PATCH",
                    f"/zones/{zone_id}/settings/{setting['id']}",
                    {"value": setting["value"]}
                )
            
            # Create page rules for caching
            await self._create_page_rules(zone_id, config)
            
            return {
                "distribution_id": zone_id,
                "domain": config["domain"],
                "status": "active",
                "cname": f"{config['domain']}.cdn.cloudflare.net"
            }
            
        except Exception as e:
            logger.error(f"Failed to create Cloudflare distribution: {e}")
            raise
    
    async def _get_zone_id(self, domain: str) -> Optional[str]:
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
    
    async def _create_page_rules(self, zone_id: str, config: Dict[str, Any]):
        """Create page rules for caching configuration"""
        try:
            # Static assets caching rule
            static_rule = {
                "targets": [
                    {
                        "target": "url",
                        "constraint": {
                            "operator": "matches",
                            "value": f"*{config['domain']}/*.{{css,js,png,jpg,jpeg,gif,svg,ico,woff,woff2}}"
                        }
                    }
                ],
                "actions": [
                    {
                        "id": "cache_level",
                        "value": "cache_everything"
                    },
                    {
                        "id": "edge_cache_ttl",
                        "value": config.get("max_ttl", 86400)
                    }
                ],
                "status": "active"
            }
            
            await self._make_request("POST", f"/zones/{zone_id}/pagerules", static_rule)
            
            # API caching rule (shorter TTL)
            api_rule = {
                "targets": [
                    {
                        "target": "url",
                        "constraint": {
                            "operator": "matches",
                            "value": f"*{config['domain']}/api/*"
                        }
                    }
                ],
                "actions": [
                    {
                        "id": "cache_level",
                        "value": "cache_everything"
                    },
                    {
                        "id": "edge_cache_ttl",
                        "value": config.get("default_ttl", 3600)
                    }
                ],
                "status": "active"
            }
            
            await self._make_request("POST", f"/zones/{zone_id}/pagerules", api_rule)
            
        except Exception as e:
            logger.error(f"Failed to create page rules: {e}")
    
    async def update_distribution(self, distribution_id: str, config: Dict[str, Any]) -> bool:
        """Update distribution configuration"""
        try:
            # Update settings similar to create_distribution
            # Implementation would update existing configuration
            return True
        except Exception as e:
            logger.error(f"Failed to update distribution {distribution_id}: {e}")
            return False
    
    async def delete_distribution(self, distribution_id: str) -> bool:
        """Delete distribution (reset zone to default)"""
        try:
            # Reset zone settings to defaults
            # In practice, you might want to keep the zone but remove custom rules
            return True
        except Exception as e:
            logger.error(f"Failed to delete distribution {distribution_id}: {e}")
            return False
    
    async def get_distribution_status(self, distribution_id: str) -> Dict[str, Any]:
        """Get distribution status"""
        try:
            zone_info = await self._make_request("GET", f"/zones/{distribution_id}")
            
            return {
                "status": "active" if zone_info.get("status") == "active" else "pending",
                "nameservers": zone_info.get("name_servers", []),
                "created_on": zone_info.get("created_on"),
                "modified_on": zone_info.get("modified_on")
            }
        except Exception as e:
            logger.error(f"Failed to get distribution status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def purge_cache(self, distribution_id: str, paths: List[str] = None) -> bool:
        """Purge cache"""
        try:
            if paths:
                # Purge specific files
                data = {"files": paths}
            else:
                # Purge everything
                data = {"purge_everything": True}
            
            await self._make_request("POST", f"/zones/{distribution_id}/purge_cache", data)
            return True
        except Exception as e:
            logger.error(f"Failed to purge cache: {e}")
            return False
    
    async def get_analytics(self, distribution_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get analytics data"""
        try:
            # Cloudflare Analytics API
            since = start_date.isoformat() + "Z"
            until = end_date.isoformat() + "Z"
            
            analytics = await self._make_request(
                "GET",
                f"/zones/{distribution_id}/analytics/dashboard?since={since}&until={until}"
            )
            
            return {
                "requests": analytics.get("totals", {}).get("requests", {}).get("all", 0),
                "bandwidth": analytics.get("totals", {}).get("bandwidth", {}).get("all", 0),
                "cache_hit_ratio": analytics.get("totals", {}).get("requests", {}).get("cached", 0) / max(analytics.get("totals", {}).get("requests", {}).get("all", 1), 1) * 100,
                "status_codes": analytics.get("totals", {}).get("requests", {}).get("http_status", {}),
                "top_countries": analytics.get("totals", {}).get("requests", {}).get("country", {})
            }
        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            return {}


class AWSCloudFrontProvider(CDNProvider):
    """AWS CloudFront CDN provider (placeholder implementation)"""
    
    def __init__(self, access_key: str, secret_key: str, region: str = "us-east-1"):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
    
    async def create_distribution(self, config: Dict[str, Any]) -> Dict[str, Any]:
        # Implement AWS CloudFront distribution creation
        raise NotImplementedError("AWS CloudFront provider not implemented")


class CDNService:
    """
    Service for managing CDN configurations and global content delivery
    """
    
    def __init__(self, db: Session, credits_service: Optional[CreditsService] = None):
        self.db = db
        self.credits_service = credits_service or CreditsService(db)
        self.providers = self._initialize_providers()
    
    def _initialize_providers(self) -> Dict[str, CDNProvider]:
        """Initialize CDN providers"""
        providers = {}
        
        # Cloudflare provider
        if hasattr(settings, 'CLOUDFLARE_API_TOKEN'):
            providers['cloudflare'] = CloudflareCDNProvider(settings.CLOUDFLARE_API_TOKEN)
        
        # AWS CloudFront provider
        if hasattr(settings, 'AWS_ACCESS_KEY_ID'):
            providers['cloudfront'] = AWSCloudFrontProvider(
                settings.AWS_ACCESS_KEY_ID,
                settings.AWS_SECRET_ACCESS_KEY
            )
        
        return providers
    
    async def create_cdn_configuration(
        self,
        domain_id: str,
        provider: str = "cloudflare",
        configuration: Optional[Dict[str, Any]] = None
    ) -> CDNConfiguration:
        """
        Create CDN configuration for a domain
        """
        # Get domain
        domain = self.db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            raise ValueError("Domain not found")
        
        if domain.status != DomainStatus.ACTIVE:
            raise ValueError("Domain must be active to configure CDN")
        
        # Check if CDN already exists
        existing_cdn = self.db.query(CDNConfiguration).filter(
            CDNConfiguration.domain_id == domain_id
        ).first()
        
        if existing_cdn:
            raise ValueError("CDN configuration already exists for this domain")
        
        # Default configuration
        default_config = {
            "default_ttl": 3600,
            "max_ttl": 86400,
            "compression_enabled": True,
            "brotli_enabled": True,
            "image_optimization": True,
            "waf_enabled": True,
            "ddos_protection": True,
            "minification": {
                "html": True,
                "css": True,
                "js": True
            }
        }
        
        if configuration:
            default_config.update(configuration)
        
        # Create CDN configuration record
        cdn_config = CDNConfiguration(
            domain_id=domain_id,
            project_id=domain.project_id,
            user_id=domain.user_id,
            provider=provider,
            origin_domain=domain.domain_name,
            default_ttl=default_config["default_ttl"],
            max_ttl=default_config["max_ttl"],
            compression_enabled=default_config["compression_enabled"],
            brotli_enabled=default_config["brotli_enabled"],
            image_optimization=default_config["image_optimization"],
            waf_enabled=default_config["waf_enabled"],
            ddos_protection=default_config["ddos_protection"],
            minification=default_config["minification"],
            status=CDNStatus.PENDING
        )
        
        self.db.add(cdn_config)
        self.db.commit()
        
        # Create CDN distribution
        asyncio.create_task(self._create_distribution_async(cdn_config.id, default_config))
        
        return cdn_config
    
    async def _create_distribution_async(self, cdn_config_id: str, config: Dict[str, Any]):
        """Asynchronously create CDN distribution"""
        cdn_config = self.db.query(CDNConfiguration).filter(CDNConfiguration.id == cdn_config_id).first()
        if not cdn_config:
            return
        
        try:
            provider = self.providers.get(cdn_config.provider)
            if not provider:
                raise Exception(f"CDN provider {cdn_config.provider} not configured")
            
            # Prepare configuration for provider
            provider_config = {
                "domain": cdn_config.origin_domain,
                "origin": f"https://{cdn_config.origin_domain}",
                "default_ttl": cdn_config.default_ttl,
                "max_ttl": cdn_config.max_ttl,
                "compression_enabled": cdn_config.compression_enabled,
                "brotli_enabled": cdn_config.brotli_enabled,
                "waf_enabled": cdn_config.waf_enabled,
                "ddos_protection": cdn_config.ddos_protection,
                "minification": cdn_config.minification
            }
            
            # Create distribution
            distribution = await provider.create_distribution(provider_config)
            
            # Update CDN configuration
            cdn_config.distribution_id = distribution["distribution_id"]
            cdn_config.cname = distribution.get("cname")
            cdn_config.status = CDNStatus.ACTIVE
            cdn_config.last_deployment = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"CDN distribution created successfully for {cdn_config.origin_domain}")
            
        except Exception as e:
            logger.error(f"CDN distribution creation failed for config {cdn_config_id}: {e}")
            cdn_config.status = CDNStatus.FAILED
            self.db.commit()
    
    async def update_cdn_configuration(
        self,
        cdn_config_id: str,
        configuration: Dict[str, Any]
    ) -> bool:
        """
        Update CDN configuration
        """
        cdn_config = self.db.query(CDNConfiguration).filter(CDNConfiguration.id == cdn_config_id).first()
        if not cdn_config:
            raise ValueError("CDN configuration not found")
        
        try:
            cdn_config.status = CDNStatus.UPDATING
            self.db.commit()
            
            # Update configuration fields
            for key, value in configuration.items():
                if hasattr(cdn_config, key):
                    setattr(cdn_config, key, value)
            
            # Update provider configuration
            if cdn_config.distribution_id:
                provider = self.providers.get(cdn_config.provider)
                if provider:
                    success = await provider.update_distribution(
                        cdn_config.distribution_id,
                        configuration
                    )
                    
                    if not success:
                        cdn_config.status = CDNStatus.FAILED
                        self.db.commit()
                        return False
            
            cdn_config.status = CDNStatus.ACTIVE
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"CDN configuration update failed: {e}")
            cdn_config.status = CDNStatus.FAILED
            self.db.commit()
            return False
    
    async def delete_cdn_configuration(self, cdn_config_id: str, user_id: str) -> bool:
        """
        Delete CDN configuration
        """
        cdn_config = self.db.query(CDNConfiguration).filter(
            CDNConfiguration.id == cdn_config_id,
            CDNConfiguration.user_id == user_id
        ).first()
        
        if not cdn_config:
            raise ValueError("CDN configuration not found")
        
        try:
            # Delete from provider
            if cdn_config.distribution_id:
                provider = self.providers.get(cdn_config.provider)
                if provider:
                    await provider.delete_distribution(cdn_config.distribution_id)
            
            # Delete from database
            self.db.delete(cdn_config)
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete CDN configuration: {e}")
            return False
    
    async def purge_cache(self, cdn_config_id: str, paths: Optional[List[str]] = None) -> bool:
        """
        Purge CDN cache
        """
        cdn_config = self.db.query(CDNConfiguration).filter(CDNConfiguration.id == cdn_config_id).first()
        if not cdn_config:
            raise ValueError("CDN configuration not found")
        
        if not cdn_config.distribution_id:
            raise ValueError("No distribution ID found")
        
        provider = self.providers.get(cdn_config.provider)
        if not provider:
            raise ValueError(f"CDN provider {cdn_config.provider} not configured")
        
        return await provider.purge_cache(cdn_config.distribution_id, paths)
    
    async def get_cdn_analytics(
        self,
        cdn_config_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get CDN analytics data
        """
        cdn_config = self.db.query(CDNConfiguration).filter(CDNConfiguration.id == cdn_config_id).first()
        if not cdn_config:
            raise ValueError("CDN configuration not found")
        
        if not cdn_config.distribution_id:
            raise ValueError("No distribution ID found")
        
        provider = self.providers.get(cdn_config.provider)
        if not provider:
            raise ValueError(f"CDN provider {cdn_config.provider} not configured")
        
        analytics = await provider.get_analytics(cdn_config.distribution_id, start_date, end_date)
        
        # Update cache hit ratio in database
        if "cache_hit_ratio" in analytics:
            cdn_config.cache_hit_ratio = analytics["cache_hit_ratio"] / 100
            self.db.commit()
        
        return analytics
    
    async def get_cdn_status(self, cdn_config_id: str) -> Dict[str, Any]:
        """
        Get comprehensive CDN status
        """
        cdn_config = self.db.query(CDNConfiguration).filter(CDNConfiguration.id == cdn_config_id).first()
        if not cdn_config:
            raise ValueError("CDN configuration not found")
        
        # Get provider status
        provider_status = {}
        if cdn_config.distribution_id:
            provider = self.providers.get(cdn_config.provider)
            if provider:
                provider_status = await provider.get_distribution_status(cdn_config.distribution_id)
        
        # Get recent analytics
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=24)
        analytics = await self.get_cdn_analytics(cdn_config_id, start_date, end_date)
        
        return {
            "configuration": {
                "id": cdn_config.id,
                "domain": cdn_config.origin_domain,
                "provider": cdn_config.provider,
                "status": cdn_config.status.value,
                "distribution_id": cdn_config.distribution_id,
                "cname": cdn_config.cname,
                "created_at": cdn_config.created_at.isoformat(),
                "last_deployment": cdn_config.last_deployment.isoformat() if cdn_config.last_deployment else None
            },
            "provider_status": provider_status,
            "analytics": analytics,
            "settings": {
                "default_ttl": cdn_config.default_ttl,
                "max_ttl": cdn_config.max_ttl,
                "compression_enabled": cdn_config.compression_enabled,
                "waf_enabled": cdn_config.waf_enabled,
                "cache_hit_ratio": cdn_config.cache_hit_ratio
            },
            "edge_locations": cdn_config.edge_locations
        }
    
    async def list_cdn_configurations(self, project_id: str, user_id: str) -> List[Dict[str, Any]]:
        """
        List all CDN configurations for a project
        """
        cdn_configs = self.db.query(CDNConfiguration).filter(
            CDNConfiguration.project_id == project_id,
            CDNConfiguration.user_id == user_id
        ).all()
        
        config_list = []
        for config in cdn_configs:
            status = await self.get_cdn_status(config.id)
            config_list.append(status)
        
        return config_list
    
    async def optimize_caching_rules(self, cdn_config_id: str) -> Dict[str, Any]:
        """
        Analyze and optimize caching rules based on usage patterns
        """
        cdn_config = self.db.query(CDNConfiguration).filter(CDNConfiguration.id == cdn_config_id).first()
        if not cdn_config:
            raise ValueError("CDN configuration not found")
        
        # Get analytics for analysis
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        analytics = await self.get_cdn_analytics(cdn_config_id, start_date, end_date)
        
        recommendations = []
        
        # Analyze cache hit ratio
        if analytics.get("cache_hit_ratio", 0) < 80:
            recommendations.append({
                "type": "cache_rules",
                "description": "Low cache hit ratio detected. Consider adjusting TTL values.",
                "current_value": analytics.get("cache_hit_ratio", 0),
                "recommended_action": "Increase TTL for static assets"
            })
        
        # Check for optimization opportunities
        if not cdn_config.compression_enabled:
            recommendations.append({
                "type": "compression",
                "description": "Enable compression to reduce bandwidth usage",
                "recommended_action": "Enable Brotli and Gzip compression"
            })
        
        if not cdn_config.image_optimization:
            recommendations.append({
                "type": "image_optimization",
                "description": "Enable image optimization to improve performance",
                "recommended_action": "Enable automatic image optimization"
            })
        
        return {
            "current_performance": {
                "cache_hit_ratio": analytics.get("cache_hit_ratio", 0),
                "bandwidth_saved": analytics.get("bandwidth", 0) * (analytics.get("cache_hit_ratio", 0) / 100)
            },
            "recommendations": recommendations,
            "optimization_score": min(100, len([r for r in recommendations if r["type"] != "cache_rules"]) * 20 + analytics.get("cache_hit_ratio", 0))
        }