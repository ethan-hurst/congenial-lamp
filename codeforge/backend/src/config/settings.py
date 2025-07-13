"""
CodeForge configuration settings
"""
from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "CodeForge"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # Server
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    WORKERS: int = Field(default=4, env="WORKERS")
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql://codeforge:password@localhost:5432/codeforge",
        env="DATABASE_URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=40, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    
    # Security
    JWT_SECRET_KEY: str = Field(
        default="your-secret-key-here-change-in-production",
        env="JWT_SECRET_KEY"
    )
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="CORS_ORIGINS"
    )
    
    # AI Configuration
    CLAUDE_API_KEY: Optional[str] = Field(default=None, env="CLAUDE_API_KEY")
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    QWEN_MODEL_PATH: Optional[str] = Field(default="/models/qwen2.5-coder", env="QWEN_MODEL_PATH")
    AI_RATE_LIMIT: int = Field(default=100, env="AI_RATE_LIMIT")
    AI_DEFAULT_MODEL: str = Field(default="claude-3-sonnet", env="AI_DEFAULT_MODEL")
    
    # Cloud Providers
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = Field(default="us-east-1", env="AWS_REGION")
    
    GCP_SERVICE_ACCOUNT_KEY: Optional[str] = Field(default=None, env="GCP_SERVICE_ACCOUNT_KEY")
    GCP_PROJECT_ID: Optional[str] = Field(default=None, env="GCP_PROJECT_ID")
    
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = Field(default=None, env="AZURE_STORAGE_CONNECTION_STRING")
    
    # Docker
    DOCKER_HOST: str = Field(default="unix:///var/run/docker.sock", env="DOCKER_HOST")
    GVISOR_RUNTIME: str = Field(default="runsc", env="GVISOR_RUNTIME")
    CONTAINER_NETWORK: str = Field(default="codeforge_network", env="CONTAINER_NETWORK")
    CONTAINER_REGISTRY: str = Field(default="codeforge", env="CONTAINER_REGISTRY")
    
    # Credits System
    MONTHLY_FREE_CREDITS: int = Field(default=100, env="MONTHLY_FREE_CREDITS")
    CREDIT_PRICE_USD: float = Field(default=0.01, env="CREDIT_PRICE_USD")
    CREDITS_PER_CPU_HOUR: int = Field(default=10, env="CREDITS_PER_CPU_HOUR")
    CREDITS_PER_GB_RAM_HOUR: int = Field(default=5, env="CREDITS_PER_GB_RAM_HOUR")
    CREDITS_PER_GB_STORAGE_MONTH: int = Field(default=1, env="CREDITS_PER_GB_STORAGE_MONTH")
    CREDITS_PER_GB_BANDWIDTH: int = Field(default=1, env="CREDITS_PER_GB_BANDWIDTH")
    MAX_ROLLOVER_CREDITS: int = Field(default=500, env="MAX_ROLLOVER_CREDITS")
    
    # Resource Limits
    MAX_CPU_CORES: int = Field(default=64, env="MAX_CPU_CORES")
    MAX_MEMORY_GB: int = Field(default=256, env="MAX_MEMORY_GB")
    MAX_STORAGE_GB: int = Field(default=1000, env="MAX_STORAGE_GB")
    MAX_CONTAINERS_PER_USER: int = Field(default=50, env="MAX_CONTAINERS_PER_USER")
    
    # Monitoring
    PROMETHEUS_PORT: int = Field(default=9090, env="PROMETHEUS_PORT")
    GRAFANA_PORT: int = Field(default=3000, env="GRAFANA_PORT")
    METRICS_ENABLED: bool = Field(default=True, env="METRICS_ENABLED")
    
    # External Services
    GITHUB_CLIENT_ID: Optional[str] = Field(default=None, env="GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: Optional[str] = Field(default=None, env="GITHUB_CLIENT_SECRET")
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_SECRET")
    
    # Storage
    STORAGE_TYPE: str = Field(default="local", env="STORAGE_TYPE")  # local, s3, gcs, azure
    STORAGE_PATH: str = Field(default="/data/codeforge", env="STORAGE_PATH")
    FILE_STORAGE_PATH: str = Field(default="/data/codeforge/files", env="FILE_STORAGE_PATH")
    S3_BUCKET: Optional[str] = Field(default=None, env="S3_BUCKET")
    GCS_BUCKET: Optional[str] = Field(default=None, env="GCS_BUCKET")
    
    # Feature Flags
    ENABLE_GPU_COMPUTING: bool = Field(default=True, env="ENABLE_GPU_COMPUTING")
    ENABLE_TIME_TRAVEL_DEBUG: bool = Field(default=True, env="ENABLE_TIME_TRAVEL_DEBUG")
    ENABLE_INSTANT_CLONING: bool = Field(default=True, env="ENABLE_INSTANT_CLONING")
    ENABLE_MULTI_AGENT_AI: bool = Field(default=True, env="ENABLE_MULTI_AGENT_AI")
    ENABLE_EDGE_COMPUTING: bool = Field(default=False, env="ENABLE_EDGE_COMPUTING")
    
    # Email
    SMTP_HOST: Optional[str] = Field(default=None, env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USERNAME: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    EMAIL_FROM: str = Field(default="noreply@codeforge.dev", env="EMAIL_FROM")
    
    # Webhooks
    WEBHOOK_SECRET: str = Field(default="webhook-secret", env="WEBHOOK_SECRET")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    
    # Collaboration
    WEBSOCKET_URL: str = Field(default="ws://localhost:8000", env="WEBSOCKET_URL")
    YJS_PORT: int = Field(default=1234, env="YJS_PORT")
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STATIC_DIR: Path = BASE_DIR / "static"
    TEMPLATES_DIR: Path = BASE_DIR / "templates"
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
        
    @property
    def database_url_async(self) -> str:
        """Convert database URL to async version"""
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        return self.DATABASE_URL
        
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"
        
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"
        
    def get_gpu_types(self) -> Dict[str, Dict[str, Any]]:
        """Get available GPU types and their specifications"""
        return {
            "tesla-t4": {
                "name": "Tesla T4",
                "memory_gb": 16,
                "credits_multiplier": 5.0,
                "available": self.ENABLE_GPU_COMPUTING
            },
            "tesla-v100": {
                "name": "Tesla V100",
                "memory_gb": 32,
                "credits_multiplier": 10.0,
                "available": self.ENABLE_GPU_COMPUTING
            },
            "a100": {
                "name": "A100",
                "memory_gb": 40,
                "credits_multiplier": 15.0,
                "available": self.ENABLE_GPU_COMPUTING
            },
            "h100": {
                "name": "H100",
                "memory_gb": 80,
                "credits_multiplier": 25.0,
                "available": self.ENABLE_GPU_COMPUTING and self.is_production
            }
        }


# Create singleton instance
settings = Settings()