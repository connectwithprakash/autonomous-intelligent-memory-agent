"""Application settings and configuration."""

from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "Memory Agent"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # API Server
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = "/api/v1"
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )
    
    # WebSocket
    ws_heartbeat_interval: int = 30  # seconds
    ws_max_connections: int = 100
    
    # LLM Configuration
    llm_provider: str = Field(
        default="ollama", 
        env="LLM_PROVIDER",
        description="LLM provider to use (ollama, openai, anthropic)"
    )
    llm_model: Optional[str] = Field(
        default=None, 
        env="LLM_MODEL",
        description="Model to use (provider-specific, e.g., llama3.2, gpt-4o-mini)"
    )
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2000, env="LLM_MAX_TOKENS")
    
    # Ollama settings
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        env="OLLAMA_BASE_URL",
        description="Ollama API base URL"
    )
    
    # OpenAI settings
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_organization: Optional[str] = Field(default=None, env="OPENAI_ORG")
    openai_base_url: Optional[str] = Field(
        default=None,
        env="OPENAI_BASE_URL",
        description="Custom OpenAI API base URL (for Azure or proxies)"
    )
    
    # Anthropic settings
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_base_url: Optional[str] = Field(
        default=None,
        env="ANTHROPIC_BASE_URL",
        description="Custom Anthropic API base URL"
    )
    
    # Memory Configuration
    max_message_history: int = 1000
    relevance_threshold: float = 0.7
    compression_threshold_hours: int = 6
    archive_threshold_hours: int = 24
    
    # Storage
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    postgres_url: str = Field(
        default="postgresql://user:pass@localhost/memory_agent",
        env="DATABASE_URL"
    )
    s3_bucket: Optional[str] = Field(default=None, env="S3_BUCKET")
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    # Security
    api_key_header: str = "X-API-Key"
    require_api_key: bool = False
    api_keys: List[str] = Field(default_factory=list, env="API_KEYS")
    
    class Config:
        """Pydantic config."""
        
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()