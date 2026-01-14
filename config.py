"""
Centralized configuration for all services in the MCP Agent system.

This file defines ports, URLs, and other settings that can be overridden
via environment variables.
"""

import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load from .env file in the project root
    env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    # python-dotenv not installed, skip
    pass


@dataclass
class ServiceConfig:
    """Centralized configuration for all services"""

    # Service Ports
    MCP_SERVER_PORT: int = int(os.getenv("MCP_SERVER_PORT", "3333"))
    USER_DETAILS_PORT: int = int(os.getenv("USER_DETAILS_PORT", "8001"))
    WHATSAPP_BOT_PORT: int = int(os.getenv("WHATSAPP_BOT_PORT", "5000"))
    AGENT_PROXY_PORT: int = int(os.getenv("AGENT_PROXY_PORT", "8000"))

    # Service URLs (constructed from ports)
    @property
    def MCP_SERVER_URL(self) -> str:
        return f"http://localhost:{self.MCP_SERVER_PORT}"

    @property
    def USER_DETAILS_URL(self) -> str:
        return f"http://localhost:{self.USER_DETAILS_PORT}"

    @property
    def AGENT_PROXY_URL(self) -> str:
        return f"http://localhost:{self.AGENT_PROXY_PORT}"

    # Ollama Configuration
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "localhost")
    OLLAMA_PORT: int = int(os.getenv("OLLAMA_PORT", "11434"))

    @property
    def OLLAMA_URL(self) -> str:
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}/api/chat"

    # Twilio Configuration (loaded from environment)
    TWILIO_ACCOUNT_SID: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_WHATSAPP_NUMBER: str = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
    TWILIO_SANDBOX_CODE: str = os.getenv("TWILIO_SANDBOX_CODE", "join learn-is")

    # LLM API Keys
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    # Default LLM Provider (0=Ollama, 1=Anthropic, 2=OpenAI)
    DEFAULT_LLM_PROVIDER: int = int(os.getenv("DEFAULT_LLM_PROVIDER", "1"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")


# Global config instance
config = ServiceConfig()


def get_config() -> ServiceConfig:
    """Get the global configuration instance"""
    return config


def reload_config() -> ServiceConfig:
    """Reload configuration from environment variables"""
    global config
    config = ServiceConfig()
    return config
