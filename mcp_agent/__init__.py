# ==============================================================================
# FILE: mcp_agent/__init__.py
# ==============================================================================
"""MCP Agent Library - Tool-calling agent for Anthropic and Ollama"""

from .agent import MCPAgent
from .providers import LLMProvider
from .config import AgentConfig

__version__ = "0.1.0"
__all__ = ["MCPAgent", "LLMProvider", "AgentConfig"]

