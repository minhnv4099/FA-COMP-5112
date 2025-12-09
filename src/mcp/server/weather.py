#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import httpx
import logging

from typing import Any, Literal, AsyncIterator, Dict
from mcp.server.fastmcp.server import FastMCP, Context
from contextlib import asynccontextmanager

from src.telemetry.telemetry_decorator import telemetry_mcp_tool, telemetry_prompt, telemetry_resource
from src.telemetry.telemetry import record_startup, record_shutdown

logger = logging.getLogger(__name__)


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Life spand for the server"""
    # Setting something here
    try:
        record_startup()
        yield {}
    finally:
        global mcp_server
        logger.info(f"MCP Server {mcp_server.name} shut down.")
        record_shutdown()


mcp_server = FastMCP(
    name="Weather",
    instructions="The MCP server define tools get weather information",
    lifespan=server_lifespan
)

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"


async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""


@mcp_server.tool()
@telemetry_mcp_tool("get_alerts")
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)


@mcp_server.tool()
@telemetry_mcp_tool("get_forecast")
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location (recommended: up to 4 decimal places)
        longitude: Longitude of the location (recommended: up to 4 decimal places)
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)


@mcp_server.prompt()
@telemetry_prompt("general_system_prompt")
def general_system_prompt(ctx: Context):
    return [
        {
            "role": "user",
            "content": f"You are a very helpful assistance."
        }
    ]


def main():
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    logger.info(f'MCP Server Weather is running on transport {transport!r}')
    mcp_server.run(transport=transport)


if __name__ == '__main__':
    main()
