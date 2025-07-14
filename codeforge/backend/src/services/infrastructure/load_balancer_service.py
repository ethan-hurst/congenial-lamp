"""
Load Balancer Service for intelligent traffic distribution and health checking
"""
import asyncio
import aiohttp
import socket
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
import statistics
import random

from ...models.infrastructure import LoadBalancer, LoadBalancerStatus, Domain, DomainStatus, HealthCheckType
from ...config.settings import settings
from ..credits_service import CreditsService


logger = logging.getLogger(__name__)


class HealthChecker:
    """Health checker for backend servers"""
    
    def __init__(self):
        self.check_results = {}
    
    async def check_health(
        self,
        server: Dict[str, Any],
        check_type: HealthCheckType,
        path: str = "/health",
        timeout: int = 5,
        expected_status: int = 200
    ) -> Dict[str, Any]:
        """
        Perform health check on a backend server
        """
        try:
            start_time = datetime.utcnow()
            
            if check_type == HealthCheckType.HTTP:
                result = await self._http_health_check(server, path, timeout, expected_status, False)
            elif check_type == HealthCheckType.HTTPS:
                result = await self._http_health_check(server, path, timeout, expected_status, True)
            elif check_type == HealthCheckType.TCP:
                result = await self._tcp_health_check(server, timeout)
            elif check_type == HealthCheckType.UDP:
                result = await self._udp_health_check(server, timeout)
            else:
                raise ValueError(f"Unsupported health check type: {check_type}")
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            return {
                "healthy": result["healthy"],
                "response_time_ms": response_time,
                "status_code": result.get("status_code"),
                "error": result.get("error"),
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "response_time_ms": None,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _http_health_check(
        self,
        server: Dict[str, Any],
        path: str,
        timeout: int,
        expected_status: int,
        use_ssl: bool
    ) -> Dict[str, Any]:
        """Perform HTTP/HTTPS health check"""
        protocol = "https" if use_ssl else "http"
        url = f"{protocol}://{server['host']}:{server['port']}{path}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout) as response:
                    if response.status == expected_status:
                        return {"healthy": True, "status_code": response.status}
                    else:
                        return {
                            "healthy": False,
                            "status_code": response.status,
                            "error": f"Unexpected status code: {response.status}"
                        }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    async def _tcp_health_check(self, server: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Perform TCP health check"""
        try:
            future = asyncio.open_connection(server["host"], server["port"])
            reader, writer = await asyncio.wait_for(future, timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return {"healthy": True}
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    async def _udp_health_check(self, server: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Perform UDP health check"""
        try:
            # Simple UDP socket test
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            sock.connect((server["host"], server["port"]))
            sock.close()
            return {"healthy": True}
        except Exception as e:
            return {"healthy": False, "error": str(e)}


class LoadBalancingAlgorithm:
    """Load balancing algorithms"""
    
    @staticmethod
    def round_robin(servers: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
        """Round robin algorithm"""
        if not servers:
            return None
        
        current_index = state.get("round_robin_index", 0)
        selected_server = servers[current_index]
        state["round_robin_index"] = (current_index + 1) % len(servers)
        
        return selected_server
    
    @staticmethod
    def least_connections(servers: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
        """Least connections algorithm"""
        if not servers:
            return None
        
        # Find server with least active connections
        min_connections = min(server.get("active_connections", 0) for server in servers)
        candidates = [s for s in servers if s.get("active_connections", 0) == min_connections]
        
        return random.choice(candidates)
    
    @staticmethod
    def weighted_round_robin(servers: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
        """Weighted round robin algorithm"""
        if not servers:
            return None
        
        # Simple weighted selection based on server weight
        total_weight = sum(server.get("weight", 1) for server in servers)
        if total_weight == 0:
            return random.choice(servers)
        
        r = random.uniform(0, total_weight)
        current_weight = 0
        
        for server in servers:
            current_weight += server.get("weight", 1)
            if r <= current_weight:
                return server
        
        return servers[-1]
    
    @staticmethod
    def ip_hash(servers: List[Dict[str, Any]], client_ip: str) -> Dict[str, Any]:
        """IP hash algorithm for session affinity"""
        if not servers:
            return None
        
        # Simple hash of client IP to select server
        hash_value = hash(client_ip)
        server_index = hash_value % len(servers)
        
        return servers[server_index]


class LoadBalancerService:
    """
    Service for managing load balancers and traffic distribution
    """
    
    def __init__(self, db: Session, credits_service: Optional[CreditsService] = None):
        self.db = db
        self.credits_service = credits_service or CreditsService(db)
        self.health_checker = HealthChecker()
        self.lb_algorithms = {
            "round_robin": LoadBalancingAlgorithm.round_robin,
            "least_connections": LoadBalancingAlgorithm.least_connections,
            "weighted_round_robin": LoadBalancingAlgorithm.weighted_round_robin,
            "ip_hash": LoadBalancingAlgorithm.ip_hash
        }
        self.lb_state = {}  # Store load balancer state
    
    async def create_load_balancer(
        self,
        domain_id: str,
        name: str,
        backend_servers: List[Dict[str, Any]],
        algorithm: str = "round_robin",
        health_check_config: Optional[Dict[str, Any]] = None
    ) -> LoadBalancer:
        """
        Create a new load balancer
        """
        # Get domain
        domain = self.db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            raise ValueError("Domain not found")
        
        if domain.status != DomainStatus.ACTIVE:
            raise ValueError("Domain must be active to create load balancer")
        
        # Validate backend servers
        if not backend_servers:
            raise ValueError("At least one backend server is required")
        
        for server in backend_servers:
            if not all(key in server for key in ["host", "port"]):
                raise ValueError("Each backend server must have 'host' and 'port'")
        
        # Default health check configuration
        default_health_check = {
            "enabled": True,
            "type": HealthCheckType.HTTP.value,
            "path": "/health",
            "interval": 30,
            "timeout": 5,
            "retries": 3
        }
        
        if health_check_config:
            default_health_check.update(health_check_config)
        
        # Create load balancer record
        load_balancer = LoadBalancer(
            domain_id=domain_id,
            project_id=domain.project_id,
            user_id=domain.user_id,
            name=name,
            backend_servers=backend_servers,
            algorithm=algorithm,
            health_check_enabled=default_health_check["enabled"],
            health_check_type=HealthCheckType(default_health_check["type"]),
            health_check_path=default_health_check["path"],
            health_check_interval=default_health_check["interval"],
            health_check_timeout=default_health_check["timeout"],
            health_check_retries=default_health_check["retries"],
            status=LoadBalancerStatus.PENDING
        )
        
        self.db.add(load_balancer)
        self.db.commit()
        
        # Initialize load balancer
        asyncio.create_task(self._initialize_load_balancer(load_balancer.id))
        
        return load_balancer
    
    async def _initialize_load_balancer(self, lb_id: str):
        """Initialize load balancer asynchronously"""
        load_balancer = self.db.query(LoadBalancer).filter(LoadBalancer.id == lb_id).first()
        if not load_balancer:
            return
        
        try:
            # Initialize state
            self.lb_state[lb_id] = {
                "round_robin_index": 0,
                "healthy_servers": [],
                "last_health_check": None
            }
            
            # Perform initial health checks
            await self._perform_health_checks(load_balancer)
            
            # Start health checking loop
            asyncio.create_task(self._health_check_loop(lb_id))
            
            # Simulate load balancer provisioning
            await asyncio.sleep(5)
            
            # Generate external IP (simulation)
            load_balancer.external_ip = f"203.0.113.{random.randint(1, 254)}"
            load_balancer.dns_name = f"lb-{lb_id[:8]}.codeforge.net"
            load_balancer.status = LoadBalancerStatus.ACTIVE
            
            self.db.commit()
            
            logger.info(f"Load balancer {lb_id} initialized successfully")
            
        except Exception as e:
            logger.error(f"Load balancer initialization failed for {lb_id}: {e}")
            load_balancer.status = LoadBalancerStatus.FAILED
            self.db.commit()
    
    async def _health_check_loop(self, lb_id: str):
        """Continuous health checking loop"""
        while True:
            try:
                load_balancer = self.db.query(LoadBalancer).filter(LoadBalancer.id == lb_id).first()
                if not load_balancer or load_balancer.status != LoadBalancerStatus.ACTIVE:
                    break
                
                if load_balancer.health_check_enabled:
                    await self._perform_health_checks(load_balancer)
                
                await asyncio.sleep(load_balancer.health_check_interval)
                
            except Exception as e:
                logger.error(f"Health check loop error for LB {lb_id}: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _perform_health_checks(self, load_balancer: LoadBalancer):
        """Perform health checks on all backend servers"""
        healthy_servers = []
        check_tasks = []
        
        for server in load_balancer.backend_servers:
            task = self.health_checker.check_health(
                server,
                load_balancer.health_check_type,
                load_balancer.health_check_path,
                load_balancer.health_check_timeout
            )
            check_tasks.append((server, task))
        
        # Execute health checks concurrently
        for server, task in check_tasks:
            try:
                result = await task
                server["health_status"] = result
                
                if result["healthy"]:
                    healthy_servers.append(server)
                    
            except Exception as e:
                logger.error(f"Health check failed for server {server}: {e}")
                server["health_status"] = {
                    "healthy": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        # Update state
        self.lb_state[load_balancer.id]["healthy_servers"] = healthy_servers
        self.lb_state[load_balancer.id]["last_health_check"] = datetime.utcnow()
        
        # Update database
        load_balancer.backend_servers = load_balancer.backend_servers  # Trigger update
        self.db.commit()
    
    async def route_request(self, lb_id: str, client_ip: str = None) -> Optional[Dict[str, Any]]:
        """
        Route request to backend server using load balancing algorithm
        """
        load_balancer = self.db.query(LoadBalancer).filter(LoadBalancer.id == lb_id).first()
        if not load_balancer:
            raise ValueError("Load balancer not found")
        
        if load_balancer.status != LoadBalancerStatus.ACTIVE:
            raise ValueError("Load balancer is not active")
        
        # Get healthy servers
        healthy_servers = self.lb_state.get(lb_id, {}).get("healthy_servers", [])
        
        if not healthy_servers:
            logger.warning(f"No healthy servers available for load balancer {lb_id}")
            return None
        
        # Apply load balancing algorithm
        algorithm = self.lb_algorithms.get(load_balancer.algorithm)
        if not algorithm:
            raise ValueError(f"Unknown load balancing algorithm: {load_balancer.algorithm}")
        
        if load_balancer.algorithm == "ip_hash" and client_ip:
            selected_server = algorithm(healthy_servers, client_ip)
        else:
            selected_server = algorithm(healthy_servers, self.lb_state[lb_id])
        
        if selected_server:
            # Update connection count
            selected_server["active_connections"] = selected_server.get("active_connections", 0) + 1
            
            # Update metrics
            load_balancer.active_connections = load_balancer.active_connections + 1
            load_balancer.requests_per_second = load_balancer.requests_per_second + 1  # Simplified
            
            self.db.commit()
        
        return selected_server
    
    async def update_load_balancer(
        self,
        lb_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update load balancer configuration
        """
        load_balancer = self.db.query(LoadBalancer).filter(LoadBalancer.id == lb_id).first()
        if not load_balancer:
            raise ValueError("Load balancer not found")
        
        try:
            load_balancer.status = LoadBalancerStatus.UPDATING
            self.db.commit()
            
            # Update configuration
            for key, value in updates.items():
                if hasattr(load_balancer, key):
                    setattr(load_balancer, key, value)
            
            # Restart health checks if configuration changed
            if any(key.startswith("health_check") for key in updates.keys()):
                await self._perform_health_checks(load_balancer)
            
            load_balancer.status = LoadBalancerStatus.ACTIVE
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Load balancer update failed: {e}")
            load_balancer.status = LoadBalancerStatus.FAILED
            self.db.commit()
            return False
    
    async def delete_load_balancer(self, lb_id: str, user_id: str) -> bool:
        """
        Delete load balancer
        """
        load_balancer = self.db.query(LoadBalancer).filter(
            LoadBalancer.id == lb_id,
            LoadBalancer.user_id == user_id
        ).first()
        
        if not load_balancer:
            raise ValueError("Load balancer not found")
        
        try:
            # Clean up state
            if lb_id in self.lb_state:
                del self.lb_state[lb_id]
            
            # Delete from database
            self.db.delete(load_balancer)
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete load balancer: {e}")
            return False
    
    async def get_load_balancer_status(self, lb_id: str) -> Dict[str, Any]:
        """
        Get comprehensive load balancer status
        """
        load_balancer = self.db.query(LoadBalancer).filter(LoadBalancer.id == lb_id).first()
        if not load_balancer:
            raise ValueError("Load balancer not found")
        
        # Get current state
        state = self.lb_state.get(lb_id, {})
        healthy_servers = state.get("healthy_servers", [])
        
        # Calculate health statistics
        total_servers = len(load_balancer.backend_servers)
        healthy_count = len(healthy_servers)
        health_percentage = (healthy_count / total_servers * 100) if total_servers > 0 else 0
        
        # Get response times
        response_times = []
        for server in load_balancer.backend_servers:
            health_status = server.get("health_status", {})
            if health_status.get("response_time_ms"):
                response_times.append(health_status["response_time_ms"])
        
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        return {
            "load_balancer": {
                "id": load_balancer.id,
                "name": load_balancer.name,
                "status": load_balancer.status.value,
                "algorithm": load_balancer.algorithm,
                "external_ip": load_balancer.external_ip,
                "dns_name": load_balancer.dns_name,
                "created_at": load_balancer.created_at.isoformat()
            },
            "health": {
                "total_servers": total_servers,
                "healthy_servers": healthy_count,
                "health_percentage": health_percentage,
                "last_check": state.get("last_health_check"),
                "avg_response_time_ms": avg_response_time
            },
            "traffic": {
                "active_connections": load_balancer.active_connections,
                "requests_per_second": load_balancer.requests_per_second,
                "response_time_p95": load_balancer.response_time_p95,
                "error_rate": load_balancer.error_rate
            },
            "backend_servers": load_balancer.backend_servers,
            "configuration": {
                "health_check_enabled": load_balancer.health_check_enabled,
                "health_check_interval": load_balancer.health_check_interval,
                "ssl_termination": load_balancer.ssl_termination,
                "session_affinity": load_balancer.session_affinity
            }
        }
    
    async def list_load_balancers(self, project_id: str, user_id: str) -> List[Dict[str, Any]]:
        """
        List all load balancers for a project
        """
        load_balancers = self.db.query(LoadBalancer).filter(
            LoadBalancer.project_id == project_id,
            LoadBalancer.user_id == user_id
        ).all()
        
        lb_list = []
        for lb in load_balancers:
            status = await self.get_load_balancer_status(lb.id)
            lb_list.append(status)
        
        return lb_list
    
    async def add_backend_server(self, lb_id: str, server: Dict[str, Any]) -> bool:
        """
        Add backend server to load balancer
        """
        load_balancer = self.db.query(LoadBalancer).filter(LoadBalancer.id == lb_id).first()
        if not load_balancer:
            raise ValueError("Load balancer not found")
        
        # Validate server configuration
        if not all(key in server for key in ["host", "port"]):
            raise ValueError("Server must have 'host' and 'port'")
        
        # Add server
        load_balancer.backend_servers.append(server)
        self.db.commit()
        
        # Perform health check on new server
        if load_balancer.health_check_enabled:
            await self._perform_health_checks(load_balancer)
        
        return True
    
    async def remove_backend_server(self, lb_id: str, server_index: int) -> bool:
        """
        Remove backend server from load balancer
        """
        load_balancer = self.db.query(LoadBalancer).filter(LoadBalancer.id == lb_id).first()
        if not load_balancer:
            raise ValueError("Load balancer not found")
        
        if server_index < 0 or server_index >= len(load_balancer.backend_servers):
            raise ValueError("Invalid server index")
        
        # Remove server
        del load_balancer.backend_servers[server_index]
        self.db.commit()
        
        # Update healthy servers list
        if lb_id in self.lb_state:
            healthy_servers = self.lb_state[lb_id].get("healthy_servers", [])
            # Filter out the removed server (simplified check)
            self.lb_state[lb_id]["healthy_servers"] = [
                s for i, s in enumerate(healthy_servers) if i != server_index
            ]
        
        return True
    
    async def get_load_balancer_metrics(
        self,
        lb_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get load balancer metrics for a time period
        """
        load_balancer = self.db.query(LoadBalancer).filter(LoadBalancer.id == lb_id).first()
        if not load_balancer:
            raise ValueError("Load balancer not found")
        
        # In a real implementation, this would query a metrics database
        # For now, return current metrics
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "traffic": {
                "total_requests": load_balancer.requests_per_second * 3600,  # Simplified
                "avg_response_time": load_balancer.response_time_p95,
                "error_rate": load_balancer.error_rate,
                "peak_connections": load_balancer.active_connections
            },
            "backend_health": {
                "availability": 99.9,  # Placeholder
                "avg_response_time": 150,
                "health_check_failures": 0
            },
            "distribution": {
                "algorithm": load_balancer.algorithm,
                "server_utilization": [
                    {"server": f"server-{i}", "requests": 100 + i * 10}
                    for i in range(len(load_balancer.backend_servers))
                ]
            }
        }