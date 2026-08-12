"""PropertyGuru MCP server package."""

from propertyguru_mcp.server import (
    REGION_HOSTS,
    build_search_url,
    fetch_next_data,
    listing_to_compact,
    search_propertyguru,
    server,
)

__all__ = [
    "REGION_HOSTS",
    "build_search_url",
    "fetch_next_data",
    "listing_to_compact",
    "search_propertyguru",
    "server",
]

__version__ = "0.1.0"
