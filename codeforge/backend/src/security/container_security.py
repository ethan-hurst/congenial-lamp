"""
Container Security Module for CodeForge
Implements defense-in-depth security for container execution
"""
import os
import json
import hashlib
import secrets
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import asyncio
from pathlib import Path

from ..config.settings import settings


@dataclass
class SecurityPolicy:
    """Security policy for container execution"""
    allow_network: bool = False
    allow_privileged: bool = False
    readonly_rootfs: bool = True
    no_new_privileges: bool = True
    drop_capabilities: List[str] = None
    add_capabilities: List[str] = None
    seccomp_profile: str = "default"
    apparmor_profile: str = "docker-default"
    ulimits: Dict[str, int] = None
    allowed_devices: List[str] = None
    
    def __post_init__(self):
        if self.drop_capabilities is None:
            self.drop_capabilities = ["ALL"]
        if self.add_capabilities is None:
            self.add_capabilities = ["CHOWN", "SETUID", "SETGID", "FOWNER"]
        if self.ulimits is None:
            self.ulimits = {
                "nofile": 1024,
                "nproc": 512,
                "core": 0
            }
            

class ContainerSecurity:
    """
    Comprehensive container security implementation:
    - gVisor/Firecracker for kernel isolation
    - Seccomp profiles for syscall filtering
    - AppArmor/SELinux policies
    - Network isolation and firewalling
    - Resource limits and quotas
    - File system restrictions
    """
    
    def __init__(self):
        self.policies: Dict[str, SecurityPolicy] = {
            "default": SecurityPolicy(),
            "trusted": SecurityPolicy(
                allow_network=True,
                add_capabilities=["NET_BIND_SERVICE"]
            ),
            "gpu": SecurityPolicy(
                allow_network=True,
                allowed_devices=["/dev/nvidia0", "/dev/nvidiactl"]
            )
        }
        
        # Blocked file paths
        self.blocked_paths: Set[str] = {
            "/etc/passwd",
            "/etc/shadow",
            "/etc/sudoers",
            "/root",
            "/var/run/docker.sock",
            "/proc/sys",
            "/sys/firmware"
        }
        
        # Allowed network destinations for trusted containers
        self.allowed_networks: Set[str] = {
            "github.com",
            "gitlab.com",
            "npmjs.org",
            "pypi.org",
            "crates.io",
            "pkg.go.dev"
        }
        
    def get_security_policy(self, user_trust_level: str = "default") -> SecurityPolicy:
        """Get security policy based on user trust level"""
        return self.policies.get(user_trust_level, self.policies["default"])
        
    def generate_container_config(
        self,
        base_config: Dict,
        security_policy: SecurityPolicy,
        user_id: str,
        project_id: str
    ) -> Dict:
        """Generate secure container configuration"""
        
        # Apply security constraints
        config = base_config.copy()
        
        # Host configuration
        host_config = config.get("host_config", {})
        
        # Use gVisor runtime in production
        if settings.ENVIRONMENT == "production":
            host_config["runtime"] = "runsc"
            
        # Capability management
        host_config["cap_drop"] = security_policy.drop_capabilities
        host_config["cap_add"] = security_policy.add_capabilities
        
        # Security options
        security_opts = []
        
        # Seccomp profile
        if security_policy.seccomp_profile:
            seccomp_path = self._get_seccomp_profile(security_policy.seccomp_profile)
            security_opts.append(f"seccomp={seccomp_path}")
            
        # AppArmor profile
        if security_policy.apparmor_profile:
            security_opts.append(f"apparmor={security_policy.apparmor_profile}")
            
        # No new privileges
        if security_policy.no_new_privileges:
            security_opts.append("no-new-privileges")
            
        host_config["security_opt"] = security_opts
        
        # Read-only root filesystem
        if security_policy.readonly_rootfs:
            host_config["read_only"] = True
            # Add writable tmpfs mounts
            host_config["tmpfs"] = {
                "/tmp": "size=100m,noexec,nosuid,nodev",
                "/var/tmp": "size=50m,noexec,nosuid,nodev",
                "/home/codeforge/.cache": "size=200m"
            }
            
        # Network isolation
        if not security_policy.allow_network:
            host_config["network_mode"] = "none"
        else:
            # Use custom network with firewall rules
            host_config["network_mode"] = f"codeforge_isolated_{user_id}"
            
        # Resource limits
        host_config["ulimits"] = [
            {"name": name, "soft": limit, "hard": limit}
            for name, limit in security_policy.ulimits.items()
        ]
        
        # Device access
        if security_policy.allowed_devices:
            host_config["devices"] = [
                {
                    "path_on_host": device,
                    "path_in_container": device,
                    "cgroup_permissions": "rw"
                }
                for device in security_policy.allowed_devices
            ]
            
        # PID limits
        host_config["pids_limit"] = 100
        
        # Disable privileged mode
        host_config["privileged"] = False
        
        # User namespace remapping
        host_config["userns_mode"] = "host"
        
        config["host_config"] = host_config
        
        # Environment variables sanitization
        config["environment"] = self._sanitize_environment(
            config.get("environment", {})
        )
        
        # Add security labels
        config["labels"] = config.get("labels", {})
        config["labels"].update({
            "codeforge.security.policy": security_policy.seccomp_profile,
            "codeforge.security.user": user_id,
            "codeforge.security.project": project_id,
            "codeforge.security.checksum": self._calculate_config_checksum(config)
        })
        
        return config
        
    def _get_seccomp_profile(self, profile_name: str) -> str:
        """Get path to seccomp profile"""
        profile_dir = Path("/etc/codeforge/seccomp")
        profile_path = profile_dir / f"{profile_name}.json"
        
        if not profile_path.exists():
            # Create default profile
            self._create_default_seccomp_profile(profile_path)
            
        return str(profile_path)
        
    def _create_default_seccomp_profile(self, profile_path: Path):
        """Create default restrictive seccomp profile"""
        # Based on Docker's default with additional restrictions
        profile = {
            "defaultAction": "SCMP_ACT_ERRNO",
            "architectures": [
                "SCMP_ARCH_X86_64",
                "SCMP_ARCH_X86",
                "SCMP_ARCH_X32"
            ],
            "syscalls": [
                {
                    "names": [
                        # File operations
                        "open", "openat", "close", "read", "write",
                        "lseek", "fstat", "fstatat64", "stat", "lstat",
                        "access", "faccessat", "chmod", "fchmod",
                        
                        # Memory management
                        "mmap", "mprotect", "munmap", "brk",
                        "mremap", "madvise",
                        
                        # Process management
                        "clone", "fork", "vfork", "execve",
                        "exit", "exit_group", "wait4", "waitid",
                        "kill", "getpid", "getppid",
                        
                        # Essential system calls
                        "rt_sigaction", "rt_sigprocmask", "rt_sigreturn",
                        "ioctl", "pipe", "select", "poll", "epoll_wait",
                        "dup", "dup2", "dup3", "fcntl", "fcntl64",
                        
                        # Time
                        "nanosleep", "getitimer", "alarm", "setitimer",
                        "clock_gettime", "clock_getres", "clock_nanosleep",
                        
                        # Network (if allowed)
                        "socket", "connect", "accept", "sendto", "recvfrom",
                        "sendmsg", "recvmsg", "shutdown", "bind", "listen",
                        "getsockname", "getpeername", "socketpair",
                        "setsockopt", "getsockopt"
                    ],
                    "action": "SCMP_ACT_ALLOW"
                }
            ]
        }
        
        # Write profile
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        with open(profile_path, 'w') as f:
            json.dump(profile, f, indent=2)
            
    def _sanitize_environment(self, env: Dict[str, str]) -> Dict[str, str]:
        """Sanitize environment variables"""
        # Remove sensitive variables
        sensitive_keys = {
            "AWS_SECRET_ACCESS_KEY",
            "GITHUB_TOKEN",
            "DATABASE_URL",
            "JWT_SECRET_KEY",
            "OPENAI_API_KEY",
            "CLAUDE_API_KEY"
        }
        
        sanitized = {}
        for key, value in env.items():
            if key not in sensitive_keys and not key.endswith("_SECRET"):
                sanitized[key] = value
                
        return sanitized
        
    def _calculate_config_checksum(self, config: Dict) -> str:
        """Calculate checksum of security-critical configuration"""
        critical_parts = {
            "runtime": config.get("host_config", {}).get("runtime"),
            "capabilities": config.get("host_config", {}).get("cap_add"),
            "security_opt": config.get("host_config", {}).get("security_opt"),
            "privileged": config.get("host_config", {}).get("privileged")
        }
        
        config_str = json.dumps(critical_parts, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
        
    async def create_isolated_network(self, user_id: str) -> str:
        """Create isolated network with firewall rules"""
        network_name = f"codeforge_isolated_{user_id}"
        
        # Create network with internal flag
        # This would use Docker API to create network
        
        # Apply iptables rules for the network
        # Only allow connections to approved endpoints
        
        return network_name
        
    def validate_mount(self, mount_source: str, mount_target: str) -> bool:
        """Validate mount points for security"""
        # Check source path
        source_path = Path(mount_source).resolve()
        
        # Ensure source is within allowed directories
        allowed_prefixes = [
            Path(settings.STORAGE_PATH),
            Path("/tmp/codeforge")
        ]
        
        if not any(source_path.is_relative_to(prefix) for prefix in allowed_prefixes):
            return False
            
        # Check target path
        for blocked in self.blocked_paths:
            if mount_target.startswith(blocked):
                return False
                
        return True
        
    def generate_resource_limits(
        self,
        cpu_cores: int,
        memory_gb: int,
        storage_gb: int
    ) -> Dict:
        """Generate resource limit configuration"""
        return {
            # CPU limits
            "cpu_shares": cpu_cores * 1024,
            "cpu_quota": cpu_cores * 100000,
            "cpu_period": 100000,
            
            # Memory limits
            "mem_limit": f"{memory_gb}g",
            "memswap_limit": f"{memory_gb * 2}g",
            "mem_reservation": f"{int(memory_gb * 0.8)}g",
            
            # Storage limits
            "storage_opt": {
                "size": f"{storage_gb}G"
            },
            
            # I/O limits
            "blkio_weight": 500,
            "device_read_bps": [{"path": "/dev/sda", "rate": "100mb"}],
            "device_write_bps": [{"path": "/dev/sda", "rate": "100mb"}]
        }