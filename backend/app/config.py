"""
ANCHOR Configuration Settings
Environment-based configuration with secrets management
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "ANCHOR"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://anchor:anchor@localhost:5432/anchor",
        description="PostgreSQL connection string with asyncpg driver"
    )
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # Security
    secret_key: str = Field(
        default="CHANGE-THIS-IN-PRODUCTION-USE-SECRETS-MANAGER",
        description="Secret key for JWT and encryption operations"
    )
    
    # Argon2id parameters for key derivation
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536  # 64MB
    argon2_parallelism: int = 4
    argon2_hash_len: int = 32
    argon2_salt_len: int = 16
    
    # Recovery settings
    inactivity_watch_days: int = 90  # Days before "Watch Mode"
    succession_cooling_off_days: int = 60  # Delay before full transfer
    
    # Blob storage (S3-compatible)
    blob_storage_endpoint: str = ""
    blob_storage_bucket: str = "anchor-vault"
    blob_storage_access_key: str = ""
    blob_storage_secret_key: str = ""
    
    # WebAuthn / FIDO2
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "ANCHOR"
    webauthn_origin: str = "http://localhost:3000"
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

