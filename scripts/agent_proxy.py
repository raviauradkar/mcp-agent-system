"""
Agent Proxy - HTTP wrapper for the MCP Agent.

This service provides a REST API interface to the MCP Agent with support for
multiple LLM providers (Ollama, Anthropic, OpenAI).
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config
from mcp_agent import MCPAgent, AgentConfig, LLMProvider
from mcp_agent.llogger import set_terminal_title

# Initialize configuration
config = get_config()

# Initialize FastAPI app
app = FastAPI(title="MCPAgent HTTP Wrapper")

# LLM Provider mapping: 0=Ollama, 1=Anthropic (default), 2=OpenAI
LLM_MAP = {
    0: (LLMProvider.OLLAMA, "OLLAMA_API_KEY", "mistral:latest"),
    1: (LLMProvider.ANTHROPIC, "ANTHROPIC_API_KEY", "claude-sonnet-4-20250514"),
    2: (LLMProvider.OPENAI, "OPENAI_API_KEY", "gpt-4o")
}

llm_selected = config.DEFAULT_LLM_PROVIDER

# Global agent dictionary to cache agents per LLM type
agents = {}


def print_color(msg, color="yellow", bold=True):
    """Print colored console output"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }

    color_code = colors.get(color.lower(), colors["yellow"])
    bold_code = "\033[1m" if bold else ""
    reset = colors["reset"]

    print(f"{bold_code}{color_code}{msg}{reset}")


def get_agent(llm: int = 1) -> MCPAgent:
    """
    Get or create an agent for the specified LLM provider.

    Args:
        llm: 0=Ollama, 1=Anthropic (default), 2=OpenAI

    Returns:
        MCPAgent instance
    """
    if llm not in LLM_MAP:
        raise ValueError(
            f"Invalid LLM value: {llm}. Must be 0 (Ollama), 1 (Anthropic), or 2 (OpenAI)"
        )

    # Return cached agent if exists
    if llm in agents:
        return agents[llm]

    # Create new agent
    provider, api_key_env, default_model = LLM_MAP[llm]

    # Get API key from environment (not needed for Ollama)
    api_key = None
    if provider != LLMProvider.OLLAMA:
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(f"{api_key_env} environment variable not set")

    agent_config = AgentConfig(
        mcp_server_url=config.MCP_SERVER_URL,
        provider=provider,
        model=default_model,
        api_key=api_key
    )

    agent = MCPAgent(agent_config)
    agents[llm] = agent  # Cache it

    print(f"✅ Initialized {provider} agent with model {default_model}")
    return agent


# Define the request structure for the /generate endpoint
class GenerateRequest(BaseModel):
    id: str
    message: str
    llm: int = 1  # 0=Ollama, 1=Anthropic (default), 2=OpenAI


@app.get("/health")
async def health():
    """Simple health check endpoint"""
    return {"status": "ok"}


@app.post("/generate")
async def generate(request: GenerateRequest):
    """
    Calls agent.run(id, message) and returns the result.

    Request body:
    {
        "id": "user123",
        "message": "engine check light flash",
        "llm": 1  // Optional: 0=Ollama, 1=Anthropic (default), 2=OpenAI
    }
    """
    try:
        # Get the appropriate agent
        agent = get_agent(llm=llm_selected)

        # Run the agent
        result = await agent.run(request.id, request.message, verbose=False)

        # Return the result
        return {"result": result, "llm_used": llm_selected}

    except ValueError as e:
        # Invalid LLM value or missing API key
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the error and return a 500 status code if the agent fails
        print(f"❌ Agent Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/llm-info")
async def llm_info():
    """Get information about available LLM providers"""
    return {
        "providers": {
            0: "Ollama (mistral:latest)",
            1: "Anthropic (claude-sonnet-4-20250514) - DEFAULT",
            2: "OpenAI (gpt-4o)"
        },
        "usage": "Set 'llm' field in request body to 0, 1, or 2",
        "environment_variables_needed": {
            "ollama": "None (runs locally)",
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY"
        }
    }


def main():
    """Entry point for Agent Proxy service"""
    global llm_selected

    if len(sys.argv) > 1:
        try:
            llm_selected = int(sys.argv[1])
            if llm_selected not in LLM_MAP:
                print_color(
                    "Invalid LLM argument. Must be 0 (Ollama), 1 (Anthropic), or 2 (OpenAI). "
                    "Defaulting to 1 (Anthropic)",
                    "red"
                )
                llm_selected = 1
        except ValueError:
            print_color(
                "Invalid LLM argument. Must be 0 (Ollama), 1 (Anthropic), or 2 (OpenAI). "
                "Defaulting to 1 (Anthropic)",
                "red"
            )
            llm_selected = 1

    port = config.AGENT_PROXY_PORT

    print(f"Starting MCPAgent HTTP Wrapper with LLM = {LLM_MAP[llm_selected]}...")
    print("📋 Available LLM providers: 0 = Ollama, 1 = Anthropic [DEFAULT], 2 = OpenAI")
    print("🔑 Required environment variables: ANTHROPIC_API_KEY, OPENAI_API_KEY")
    print(f"🌐 Server running on http://0.0.0.0:{port}")
    print(f"📖 Docs available at http://0.0.0.0:{port}/docs\n")

    set_terminal_title(f"MCPAgent Proxy port {port} - LLM: {LLM_MAP[llm_selected][0]}")

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
