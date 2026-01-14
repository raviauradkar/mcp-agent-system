"""
MCP Server - FastAPI server that provides tool discovery and invocation endpoints.

This server exposes tools via HTTP endpoints in OpenAI/Ollama function calling format.
"""

from fastapi import FastAPI, HTTPException
from mcp.server.fastmcp import FastMCP
import uvicorn
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config

# Initialize configuration
config = get_config()

# Initialize MCP server
mcp = FastMCP("my-data-connector")


# Register tool
@mcp.tool(
    name="lookup_user_data",
    description="Fetch user-specific data including car details, orders, profile information, etc."
)
async def lookup_user_data(msisdn: str, query: str) -> dict:
    """
    Args:
        msisdn: The phone number of the user (e.g., +919916103095)
        query: The type of data to retrieve (e.g., 'car_details', 'recent_orders', 'profile')
    """
    print(f"Looking up data for MSISDN: {msisdn}, Query: {query}")

    # Simulate data lookup
    mock_data = {
        "car_details": {
            "make": "Mazda",
            "model": "MX-5 Grand Touring",
            "year": 2021,
            "color": "Gray Metallic",
            "registration": "PA-01-AB-1234"
        },
        "recent_orders": [
            {"order_id": "12345", "item": "Product A", "date": "2026-01-01"},
            {"order_id": "12346", "item": "Product B", "date": "2026-01-03"}
        ],
        "profile": {
            "name": "John Doe",
            "email": "john@example.com",
            "address": "123 Main St"
        }
    }

    return {
        "msisdn": msisdn,
        "query": query,
        "result": mock_data.get(query, f"No data found for query: {query}")
    }


app = FastAPI()


# ---- TOOL DISCOVERY (HTTP) ----
@app.get("/tools")
async def list_tools():
    """Return tools in OpenAI/Ollama function calling format"""
    tools_list = await mcp.list_tools()

    result = []

    for tool in tools_list:
        # Get the full JSON schema from the tool
        schema = tool.inputSchema if hasattr(tool, 'inputSchema') else {}

        # Convert to OpenAI function calling format
        tool_def = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or f"Tool: {tool.name}",
                "parameters": {
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", [])
                }
            }
        }

        result.append(tool_def)

    return result


# ---- SIMPLIFIED SCHEMA ENDPOINT (optional) ----
@app.get("/tools/simple")
async def list_tools_simple():
    """Return tools in simplified format"""
    tools_list = await mcp.list_tools()

    result = []

    for tool in tools_list:
        schema = tool.inputSchema if hasattr(tool, 'inputSchema') else {}
        properties = schema.get("properties", {})

        input_schema = {
            name: {
                "type": prop.get("type", "string"),
                "description": prop.get("description", "")
            }
            for name, prop in properties.items()
        }

        result.append({
            "name": tool.name,
            "description": tool.description,
            "input_schema": input_schema
        })

    return result


# ---- TOOL INVOCATION (HTTP) ----
@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, payload: dict):
    """Invoke a tool with given parameters"""
    try:
        result = await mcp.call_tool(tool_name, payload)
        return result
    except AttributeError:
        # Fallback if call_tool doesn't exist
        try:
            # Try using the tool directly
            tool_func = getattr(mcp, tool_name, None)
            if tool_func:
                return await tool_func(**payload)
            else:
                raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---- HEALTH CHECK ----
@app.get("/")
async def health():
    return {"status": "ok", "server": "my-data-connector"}


def main():
    """Entry point for the MCP server"""
    port = config.MCP_SERVER_PORT

    print(f"Starting MCP server on http://0.0.0.0:{port}")
    print(f"Tools endpoint: http://0.0.0.0:{port}/tools")

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
