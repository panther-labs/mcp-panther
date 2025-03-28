import logging
import os
import datetime
from typing import List, Dict, Any
import aiohttp
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Server name
MCP_SERVER_NAME = "panther-mcp"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(MCP_SERVER_NAME)

# Load environment variables from .env file if it exists
load_dotenv()

# Server dependencies
deps = [
    "python-dotenv",
    "aiohttp",
    "uvicorn",
]

# Create the MCP server
mcp = FastMCP(MCP_SERVER_NAME, dependencies=deps)

# GraphQL endpoint for Panther
PANTHER_API_URL = os.getenv("PANTHER_API_URL", "https://api.runpanther.com/public/graphql")

# Get Panther API key from environment variable
def get_panther_api_key() -> str:
    api_key = os.getenv("PANTHER_API_KEY")
    if not api_key:
        raise ValueError("PANTHER_API_KEY environment variable is not set")
    return api_key

# GraphQL query to get today's alerts
GET_TODAYS_ALERTS_QUERY = """
query GetTodaysAlerts {
  alerts(
    input: {
      pageSize: 100
      sortBy: { field: createdAt, direction: descending }
      timeRange: { type: relative, value: { unit: day, value: 1 } }
    }
  ) {
    alertSummaries {
      alertId
      title
      severity
      status
      createdAt
      ruleId
      updateTime
    }
    paging {
      totalItems
      totalPages
    }
  }
}
"""

@mcp.tool()
async def authenticate_with_panther() -> Dict[str, Any]:
    """Test authentication with Panther using the API key"""
    logger.info("Testing authentication with Panther")
    try:
        # Simple GraphQL query to test authentication
        query = """
        query TestAuth {
          alerts(input: { pageSize: 1 }) {
            paging {
              totalItems
            }
          }
        }
        """
        api_key = get_panther_api_key()
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json"
            }
            async with session.post(
                PANTHER_API_URL,
                json={"query": query},
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully authenticated with Panther")
                    return {"success": True, "message": "Authentication successful"}
                else:
                    error_text = await response.text()
                    logger.error(f"Authentication failed: HTTP {response.status}, {error_text}")
                    return {"success": False, "message": f"Authentication failed: HTTP {response.status}, {error_text}"}
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        return {"success": False, "message": f"Authentication failed: {str(e)}"}

@mcp.tool()
async def get_todays_alerts() -> Dict[str, Any]:
    """Get alerts from Panther for the current day"""
    logger.info("Fetching today's alerts from Panther")
    try:
        api_key = get_panther_api_key()
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json"
            }
            async with session.post(
                PANTHER_API_URL,
                json={"query": GET_TODAYS_ALERTS_QUERY},
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if "errors" in data:
                        logger.error(f"GraphQL errors: {data['errors']}")
                        return {"success": False, "message": f"GraphQL errors: {data['errors']}"}
                    
                    results = data.get("data", {}).get("alerts", {})
                    alert_summaries = results.get("alertSummaries", [])
                    paging_info = results.get("paging", {})
                    
                    logger.info(f"Successfully retrieved {len(alert_summaries)} alerts out of {paging_info.get('totalItems', 0)} total")
                    
                    # Format the response
                    return {
                        "success": True,
                        "alerts": alert_summaries,
                        "total_alerts": paging_info.get("totalItems", 0),
                        "total_pages": paging_info.get("totalPages", 0)
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to fetch alerts: HTTP {response.status}, {error_text}")
                    return {"success": False, "message": f"Failed to fetch alerts: HTTP {response.status}, {error_text}"}
    except Exception as e:
        logger.error(f"Failed to fetch alerts: {str(e)}")
        return {"success": False, "message": f"Failed to fetch alerts: {str(e)}"}

@mcp.resource("config://panther")
def get_panther_config() -> Dict[str, Any]:
    """Get the Panther API configuration"""
    return {
        "api_url": PANTHER_API_URL,
        "authenticated": bool(os.getenv("PANTHER_API_KEY")),
        "server_name": MCP_SERVER_NAME,
    }

# Export the app instance for Uvicorn
app = mcp.app

if __name__ == "__main__":
    # For local testing (not needed when using 'mcp dev' or 'mcp install')
    import uvicorn
    uvicorn.run("panther_mcp_server:app", host="127.0.0.1", port=8000) 
