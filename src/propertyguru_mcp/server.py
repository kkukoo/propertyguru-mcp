"""Unofficial PropertyGuru MCP server.

Data source: PropertyGuru Next.js `__NEXT_DATA__` JSON rendered server-side.
- Listings live at `pageData.data.listingsData[i].listingData` (48 fields).
- Filters use the *frontend* URL params: minPrice/maxPrice/bedrooms[]/sort etc.
- Pagination is path-style `/property-for-sale/2` (works) or unreliable `&page=2`.

Tools:
  - search_listings(...)  → one page of full listingData entries
  - get_listing_count(...) → quick probe returning count only

NOTE (per user request): no server-side field pruning — every listing is
returned with its full 48-key `listingData` as-received.  Callers must budget
context when consuming large pages.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import urllib.parse
import urllib.request
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Log level: MCP_LOG_LEVEL env controls output; default WARNING = silent
_LOG_LEVEL = os.environ.get("MCP_LOG_LEVEL", "WARNING").upper()
logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.WARNING),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("propertyguru_mcp")

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S
)

REGION_HOSTS = {
    "sg": "https://www.propertyguru.com.sg",
    "my": "https://www.propertyguru.com.my",
}


def fetch_next_data(url: str, timeout: float = 25.0) -> dict[str, Any]:
    """GET url and parse __NEXT_DATA__ JSON.  Raises on missing/invalid."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-SG,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise RuntimeError(
                f"Cloudflare blocked the request (HTTP 403).  "
                f"PropertyGuru may be requiring JavaScript challenge solving "
                f"from this IP.  URL: {url}"
            ) from e
        raise RuntimeError(f"HTTP {e.code} from PropertyGuru: {url}") from e
    m = NEXT_DATA_RE.search(html)
    if not m:
        raise RuntimeError(
            f"__NEXT_DATA__ not found — PropertyGuru changed its page structure "
            f"or returned a different layout (Cloudflare/bot-check?).  URL: {url}"
        )
    return json.loads(m.group(1))


def build_search_url(
    region: str,
    listing_type: str,
    freetext: str | None,
    property_type: str | None,
    bedrooms: list[int] | None,
    price_min: int | None,
    price_max: int | None,
    sort: str | None,
) -> str:
    """Builds the URL using PropertyGuru's frontend param spelling.

    Verified working 2026-08-12:
      minPrice / maxPrice / bedrooms[] / sort (camelCase)
      &search=true is NOT required and triggers 301→403 on param combos.
    """
    region = (region or "sg").lower()
    if region not in REGION_HOSTS:
        raise ValueError(f"unsupported region {region!r}; expect one of {list(REGION_HOSTS)}")
    host = REGION_HOSTS[region]

    lt = (listing_type or "sale").lower()
    path_type = {"sale": "sale", "rent": "rent"}.get(lt)
    if not path_type:
        raise ValueError(f"unsupported listing_type {listing_type!r}; expect sale|rent")

    params: list[tuple[str, str]] = []
    if freetext:
        params.append(("freetext", freetext))
    params.append(("isCommercial", "false"))
    if price_min is not None:
        params.append(("minPrice", str(price_min)))
    if price_max is not None:
        params.append(("maxPrice", str(price_max)))
    if bedrooms:
        for b in bedrooms:
            params.append(("bedrooms[]", str(int(b))))
    if property_type:
        params.append(("property_type_code[]", property_type))
    if sort:
        params.append(("sort", sort))
    params.append(("listingType", lt))
    params.append(("locale", "en"))

    return f"{host}/property-for-{path_type}?" + urllib.parse.urlencode(params)


def listing_to_compact(listing: dict) -> dict:
    """Return a compact dict for the `get_listing_count` test (kept for compat)."""
    return {
        "id": listing.get("id"),
        "price": listing.get("price"),
        "propertyName": listing.get("propertyName"),
        "url": listing.get("url"),
    }


def search_propertyguru(
    region: str,
    listing_type: str,
    freetext: str | None,
    property_type: str | None,
    bedrooms_min: int | None,
    bedrooms_max: int | None,
    price_min: int | None,
    price_max: int | None,
    sort: str | None,
    limit: int,
) -> dict[str, Any]:
    """Fetch one page of listings.  Returns the raw listingData list."""
    # bedrooms filter — treat bedrooms_min == bedrooms_max as a single exact match
    bedrooms_list: list[int] | None = None
    if bedrooms_min is not None and bedrooms_max is not None and bedrooms_min == bedrooms_max:
        bedrooms_list = [bedrooms_min]
    elif bedrooms_min is not None:
        bedrooms_list = [bedrooms_min]

    url = build_search_url(
        region, listing_type, freetext, property_type,
        bedrooms_list, price_min, price_max, sort,
    )
    log.info("fetching %s", url)
    data = fetch_next_data(url)
    page_data = (
        data.get("props", {})
        .get("pageProps", {})
        .get("pageData", {})
        .get("data", {})
    )

    listings_raw: list[dict] = []
    for entry in page_data.get("listingsData", []):
        ld = entry.get("listingData") if isinstance(entry, dict) else None
        if ld:
            listings_raw.append(ld)
        if len(listings_raw) >= limit:
            break

    return {
        "url": url,
        "region": region,
        "listing_type": listing_type,
        "count": len(listings_raw),
        "listings": listings_raw,
    }


# ---------------- MCP plumbing ----------------

server = Server("propertyguru")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_listings",
            description=(
                "Search PropertyGuru SG / MY listings.  Returns up to `limit` "
                "listings with the FULL 48-field listingData (price, psf, "
                "address, mrt, tenure, buildYear, photos, agent, etc).  "
                "No server-side pruning — caller must budget context."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "enum": ["sg", "my"],
                        "default": "sg",
                    },
                    "listing_type": {
                        "type": "string",
                        "enum": ["sale", "rent"],
                        "default": "sale",
                    },
                    "freetext": {
                        "type": "string",
                        "description": "Search text: area / condo / district / MRT (e.g. 'Orchard', 'Tampines', 'Mont Kiara')",
                    },
                    "property_type": {
                        "type": "string",
                        "description": "PropertyGuru type code, e.g. CONDO, HDB, LANDED, APARTMENT, COMMERCIAL",
                    },
                    "bedrooms_min": {"type": "integer"},
                    "bedrooms_max": {"type": "integer"},
                    "price_min": {"type": "integer"},
                    "price_max": {"type": "integer"},
                    "sort": {
                        "type": "string",
                        "enum": ["price_asc", "price_desc", "date", "psf"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max listings to return from the single fetched page (default 25, cap 40)",
                        "default": 25,
                    },
                },
                "required": ["region", "listing_type"],
            },
        ),
        Tool(
            name="get_listing_count",
            description=(
                "Cheap probe — returns the count PropertyGuru produced for "
                "a given search, without returning listing contents."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {"type": "string", "enum": ["sg", "my"], "default": "sg"},
                    "listing_type": {"type": "string", "enum": ["sale", "rent"], "default": "sale"},
                    "freetext": {"type": "string"},
                },
                "required": ["region", "listing_type"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "search_listings":
            limit = min(int(arguments.get("limit") or 25), 40)
            result = search_propertyguru(
                region=arguments.get("region") or "sg",
                listing_type=arguments.get("listing_type") or "sale",
                freetext=arguments.get("freetext"),
                property_type=arguments.get("property_type"),
                bedrooms_min=arguments.get("bedrooms_min"),
                bedrooms_max=arguments.get("bedrooms_max"),
                price_min=arguments.get("price_min"),
                price_max=arguments.get("price_max"),
                sort=arguments.get("sort"),
                limit=limit,
            )
            return [TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2, default=str),
            )]

        if name == "get_listing_count":
            result = search_propertyguru(
                region=arguments.get("region") or "sg",
                listing_type=arguments.get("listing_type") or "sale",
                freetext=arguments.get("freetext"),
                property_type=None,
                bedrooms_min=None, bedrooms_max=None,
                price_min=None, price_max=None,
                sort=None,
                limit=1,
            )
            return [TextContent(
                type="text",
                text=json.dumps({
                    "region": result["region"],
                    "listing_type": result["listing_type"],
                    "count_in_page": result["count"],
                    "url": result["url"],
                }, ensure_ascii=False),
            )]

        return [TextContent(type="text", text=f"unknown tool {name!r}")]
    except Exception as e:
        log.error("tool %s failed: %s", name, e)
        return [TextContent(
            type="text",
            text=f"error: {type(e).__name__}: {e}",
        )]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )
