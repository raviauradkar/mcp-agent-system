"""Configuration for MCP Agent"""

from dataclasses import dataclass, field
from typing import Optional, List
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path to import central config
sys.path.insert(0, str(Path(__file__).parent.parent))

from .llogger import setup_logger

def print_color(msg, color="yellow", bold=True):
    colors = {"red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m", "blue": "\033[94m",
        "magenta": "\033[95m", "cyan": "\033[96m", "white": "\033[97m", "reset": "\033[0m" }
    
    color_code = colors.get(color.lower(), colors["yellow"])
    bold_code = "\033[1m" if bold else ""
    reset = colors["reset"]
    
    print(f"{bold_code}{color_code}{msg}{reset}")

def print_logfile_name(logger):
    """Finds the first FileHandler in the logger and prints its base filename."""
    found = False
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            print_color(f"LOGGING TO FILE: {handler.baseFilename}", "blue")
            found = True
            break
            
    if not found:
        print_color("WARNING: No FileHandler found. Logging to console only.", "yellow")

logger = setup_logger(__name__)
print_logfile_name(logger)

@dataclass
class AgentConfig:
    """Configuration for MCP Agent"""

    # MCP Server settings
    mcp_server_url: str = field(default_factory=lambda: os.getenv("MCP_SERVER_URL", "http://localhost:3333"))

    # LLM settings
    provider: str = "anthropic"  # "anthropic", "ollama", or "openai"
    model: Optional[str] = None
    api_key: Optional[str] = None

    # Ollama specific
    ollama_url: str = field(default_factory=lambda: os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat"))
    
    # Agent behavior
    max_iterations: int = 5
    max_tokens: int = 1024
    timeout: int = 300
    
    # Tool calling behavior (NEW)
    use_direct_tool_calls: bool = True  # Default to direct calls
    force_proxy_tools: List[str] = field(default_factory=list)  # Tools that must use proxy
    
    # System prompt
    system_prompt: str = """You are a helpful assistant with access to user data tools.

When users ask about car-related issues (diagnostics, maintenance, problems, check lights, etc.), 
use the lookup_user_data tool with query='car_details'.

When users ask about orders or purchases, use query='recent_orders'.
When users ask about account or profile info, use query='profile'.

After retrieving data, provide helpful analysis and recommendations based on the data."""