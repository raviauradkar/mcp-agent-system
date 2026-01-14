"""
User Details Service - FastAPI service that provides user data lookup endpoints.

This service can be called directly or via the MCP server proxy.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config

# Initialize configuration
config = get_config()

app = FastAPI()


# Define request model for JSON body
class LookupUserDataRequest(BaseModel):
    msisdn: str
    query: str


@app.post("/api/lookup_user_data")
async def lookup_user_data(request: LookupUserDataRequest):
    """
    Fetch user-specific data including car details, orders, profile information, etc.

    Args:
        request: Request containing msisdn and query fields
    """
    msisdn = request.msisdn
    query = request.query

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
        "result": mock_data.get(query, f"No data found for query: {query}"),
        "service": "user_details"
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "user_details"}


def main():
    """Entry point for the User Details Service"""
    port = config.USER_DETAILS_PORT

    print(f"Starting User Details Service on http://0.0.0.0:{port}")
    print(f"API endpoint: http://0.0.0.0:{port}/api/lookup_user_data")

    try:
        # Try to set terminal title if llogger is available
        from mcp_agent.llogger import set_terminal_title
        set_terminal_title(f"User Details Service - Port {port}")
    except ImportError:
        pass

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
