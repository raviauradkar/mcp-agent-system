"""
Basic Agent Example

This example demonstrates how to use the MCP Agent programmatically.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_agent import MCPAgent, AgentConfig, LLMProvider
from config import get_config

# Initialize configuration
config = get_config()


async def main():
    """Run a basic agent query"""

    # Create agent configuration
    agent_config = AgentConfig(
        mcp_server_url=config.MCP_SERVER_URL,
        provider=LLMProvider.ANTHROPIC,
        model="claude-sonnet-4-20250514",
        api_key=config.ANTHROPIC_API_KEY
    )

    # Initialize agent
    agent = MCPAgent(agent_config)

    # Discover available tools
    print("Discovering tools...")
    await agent.discover_tools()

    print("\nAvailable tools:")
    for tool_name, description in agent.get_available_tools().items():
        print(f"  - {tool_name}: {description}")

    # Run a query
    user_id = "+919916103095"
    query = "Get car details for +919916103095"

    print(f"\n{'=' * 60}")
    print(f"Running query: {query}")
    print(f"{'=' * 60}\n")

    result = await agent.run(user_id, query, verbose=True)

    print(f"\n{'=' * 60}")
    print(f"Result: {result}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    asyncio.run(main())
