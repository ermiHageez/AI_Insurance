"""Configuration settings for InsurTech AI Microservice."""
from typing import Optional, Literal

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field, ConfigDict, field_validator
except ImportError:
    try:
        from pydantic import BaseModel as BaseSettings, Field, ConfigDict
    except ImportError:
        class BaseSettings:
            pass
        def Field(default=None, description=""):
            return default
        def ConfigDict(**kwargs):
            return kwargs


class Settings(BaseSettings):
    # Server
    PORT: int = Field(default=5000, description="Port for the AI microservice")
    HOST: str = Field(default="0.0.0.0", description="Host interface")
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    LOG_LEVEL: str = Field(default="INFO", description="Log level")

    # LLM Configuration
    LLM_PROVIDER: Literal["gemini", "openai", "groq", "openai_compatible", "ollama", "mock"] = Field(
        default="mock",
        description="LLM Provider: gemini, openai, groq, openai_compatible, ollama, or mock"
    )

    @field_validator("LLM_PROVIDER", mode="before")
    @classmethod
    def default_empty_provider(cls, v):
        if not v or not isinstance(v, str) or v.strip() == "":
            return "mock"
        return v.strip().lower()
    LLM_API_KEY: Optional[str] = Field(
        default=None,
        description="Optional API Key for external cloud LLM"
    )
    LLM_BASE_URL: str = Field(
        default="http://localhost:11434/v1",
        description="LLM endpoint base URL"
    )
    LLM_MODEL: str = Field(
        default="qwen2.5:3b",
        description="Model identifier"
    )
    LLM_TEMPERATURE: float = Field(
        default=0.1,
        description="Sampling temperature for strict factual grounding"
    )

    # Backing Stores
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/insuretech_ai",
        description="PostgreSQL / pgvector database URL"
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )

    # Security
    JWT_SECRET_KEY: str = Field(
        default="dev-secret-key-for-local-testing-insureflow-32-chars-min",
        description="Secret key for JWT validation in local development"
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT signature algorithm"
    )

    # Platform Integration
    CLAIM_SERVICE_URL: str = Field(
        default="http://localhost:8080/api/v1/claims",
        description="Core platform claim service URL"
    )

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60,
        description="Max requests per minute per IP"
    )

    # Mandatory Legal Disclaimer
    AMHARIC_DISCLAIMER: str = (
        "ይህ መረጃ ለማሳወቂያ ብቻ የቀረበ ነው፤ የመጨረሻ ውሳኔ የሚሰጠው የካሳ ክፍያ ባለሙያው ነው"
    )
    ENGLISH_DISCLAIMER: str = (
        "This information is provided for informational purposes only; "
        "the final decision is made by the claims assessor."
    )

    model_config = ConfigDict(env_file=".env", extra="ignore")


settings = Settings()
