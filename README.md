# propertyguru-mcp

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-compatible-brightgreen)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/tests-9%20passed-brightgreen)]()

> **Unofficial** MCP ([Model Context Protocol](https://modelcontextprotocol.io)) server that exposes **PropertyGuru Singapore & Malaysia** listing search as MCP tools. No API key. No subscription. One HTTP request per query.

---

## ⚠️ Disclaimer

This project is **not affiliated with, endorsed by, or connected to PropertyGuru Group** in any way. It is an **unofficial, community-maintained tool** built for personal research and educational purposes.

- PropertyGuru® and the PropertyGuru logo are trademarks of PropertyGuru Group.
- This tool **scrapes publicly available HTML** that PropertyGuru renders server-side. Use of this tool **may violate PropertyGuru's Terms of Service**. Use at your own risk.
- No warranty. The authors are not responsible for any consequences of using this tool.
- If you are PropertyGuru and want this taken down, please open an issue and I will respond promptly.

---

## What data does it provide?

Each `search_listings` call returns up to **25 listings** (one page) with the **complete 48-field `listingData`** as rendered by PropertyGuru itself. Highlights:

| Category | Fields |
|---|---|
| **Price** | `price.value`, `price.pretty` ("S$ 3,499,999"), `price.type.text` (Negotiable / Offers Welcome) |
| **Area** | `area.localeStringValue` ("1,873 sqft"), `floorArea` |
| **PSF** | `pricePerArea.localeStringValue` ("S$ 1,868.66 psf") |
| **Layout** | `bedrooms`, `bathrooms`, `property.subTypeText` (Condominium / HDB / Apartment / Landed / Commercial) |
| **Tenure / Age** | Freehold vs 99-year Leasehold; "Built: 2010" |
| **Address** | `fullAddress` ("29 Angullia Park"), `shortAddress` ("Orchard / River Valley, D09-10") |
| **Public transit** | `mrt.nearbyText` ("7 min (570 m) from NS22 Orchard MRT Station") |
| **Photos** | `mediaCarousel.previewMedia.images.items[]` (15-30 hi-res URLs per listing), `floorPlans.items[]` |
| **Agent** | `agent.name`, `agent.license` (e.g. `R057754I`), `agent.profileUrl`, `agent.description`, `agency.name` |
| **Status** | `isVerified`, `isOfficialListing`, `isDeveloperListing`, `isPrioritized` |
| **Posted** | `postedOn.text`, `postedOn.unix` |
| **Highlights** | `highlights.items` (project selling points) |
| **URL** | Direct link to the listing detail page |

> **No field pruning.** Server returns the raw `listingData` structure — the example below is the exact JSON a caller receives.

---

## Demo

Real output of `search_listings(region="sg", listing_type="rent", freetext="Orchard", bedrooms_min=3, price_min=3000000, price_max=5000000)`:

```json
{
  "count": 25,
  "listings": [
    {
      "id": 25472440,
      "price": { "value": 3499999, "pretty": "S$ 3,499,999", "type": { "text": "Negotiable" } },
      "pricePerArea": { "localeStringValue": "S$ 1,868.66 psf" },
      "area": { "localeStringValue": "1,873 sqft" },
      "bedrooms": 3, "bathrooms": 3,
      "localizedTitle": "Orchard Scotts",
      "fullAddress": "251 Orchard Road",
      "shortAddress": "Orchard / River Valley (D09-10)",
      "mrt": { "nearbyText": "10 min (840 m) from NS21 Newton MRT Station" },
      "mediaItems": [{ "icon": "images", "text": "18", "mediaType": "images" }],
      "agent": { "name": "Edwin Phua", "license": "R057754I" },
      "agency": { "name": "HUTTONS ASIA PTE. LTD." },
      "url": "https://www.propertyguru.com.sg/listing/for-sale-orchard-scotts-25472440",
      "postedOn": { "text": "11 Aug 2026", "unix": 1786419975 }
    },
    ...
  ]
}
```

---

## How it works

PropertyGuru is a **Next.js SSR site**. When you visit a listing-search URL, the server embeds the complete result set as JSON at a well-known DOM id:

```html
<script id="__NEXT_DATA__" type="application/json">{
  "props": { "pageProps": { "pageData": { "data": {
    "listingsData": [ { "listingData": { ... }, ... }, ... ]
  } } } }
}</script>
```

This MCP server:
1. Builds a filter URL using the same `minPrice`/`maxPrice`/`bedrooms[]`/`freetext` param spelling PropertyGuru's own frontend uses.
2. Fetches the HTML page with a plain browser User-Agent.
3. Parses `__NEXT_DATA__` (regex → `json.loads`).
4. Returns the raw `listingData` array as JSON to the caller.

**Why no third-party API key**: because we're not using PropertyGuru's paid partner APIs — we're reading the same HTML your browser would receive.

---

## Tools

### `search_listings`

The primary tool. Returns a page of full listings.

| Param | Type | Required | Default | Description |
|---|---|---|---|---|
| `region` | `sg` \| `my` | ✅ | `sg` | Singapore or Malaysia |
| `listing_type` | `sale` \| `rent` | ✅ | `sale` | — |
| `freetext` | string | — | — | Free text: `"Orchard"`, `"Mont Kiara"`, `"Tampines"`, `"Orchard Scotts"` (specific condo) |
| `property_type` | string | — | — | `CONDO`, `HDB`, `LANDED`, `APARTMENT`, `COMMERCIAL` |
| `bedrooms_min` | int | — | — | When `bedrooms_min == bedrooms_max`, treated as exact match |
| `bedrooms_max` | int | — | — | Studio = `0` |
| `price_min` | int | — | — | Local currency (SGD or MYR) |
| `price_max` | int | — | — | |
| `sort` | enum | — | — | `price_asc`, `price_desc`, `date`, `psf` |
| `limit` | int ≤ 40 | — | 25 | Single page cap |

### `get_listing_count`

Cheap probe returning only the count for a search (use to size a query before fetching).

---

## Installation

```bash
# Clone and install
git clone https://github.com/kkukoo/propertyguru-mcp.git
cd propertyguru-mcp

# Option A: uv (recommended)
uv venv && uv pip install -e .

# Option B: plain pip
python -m venv .venv && ./.venv/bin/pip install -e .

# Run tests
python -m pytest tests/ -v
```

After install, the MCP server is available three ways (all equivalent):

```bash
# 1. Console script
.venv/bin/propertyguru-mcp

# 2. Module invocation
.venv/bin/python -m propertyguru_mcp

# 3. Direct path (no install needed if you prefer running from source)
python src/propertyguru_mcp/server.py
```

The server talks MCP over **stdio** (the default transport for MCP clients). It does not listen on any network port.

---

## Hooking up to your MCP client

Below are working config snippets. Replace `/path/to/propertyguru-mcp` and the python interpreter with whatever you used in the install step.

### Hermes Agent — `~/.hermes/config.yaml`

```yaml
mcp_servers:
  propertyguru:
    command: /path/to/propertyguru-mcp/.venv/bin/propertyguru-mcp
    args: []
    timeout: 60
    connect_timeout: 30
```

Reload via `hermes gateway restart` (from a shell outside Hermes) or `/restart` from inside the gateway chat.

### Claude Desktop — `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "propertyguru": {
      "command": "/path/to/propertyguru-mcp/.venv/bin/propertyguru-mcp",
      "args": []
    }
  }
}
```

Restart Claude Desktop after editing.

### Cursor — `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "propertyguru": {
      "command": "/path/to/propertyguru-mcp/.venv/bin/propertyguru-mcp",
      "args": []
    }
  }
}
```

### Cline (VS Code extension)

In Cline Settings → MCP, add:

```json
{
  "propertyguru": {
    "command": "/path/to/propertyguru-mcp/.venv/bin/propertyguru-mcp",
    "args": []
  }
}
```

### Continue.dev

Edit `~/.continue/config.json`:

```json
{
  "experimental": {
    "modelContextProtocolServers": [{
      "name": "propertyguru",
      "transport": {
        "type": "stdio",
        "command": "/path/to/propertyguru-mcp/.venv/bin/propertyguru-mcp",
        "args": []
      }
    }]
  }
}
```

### Any OpenAI Agents SDK-compatible client

The standard MCP stdio pattern works:

```python
from agents.mcp import MCPServerStdio

async with MCPServerStdio(
    name="propertyguru",
    params={
        "command": "/path/to/propertyguru-mcp/.venv/bin/propertyguru-mcp",
        "args": [],
    },
) as server:
    tools = await server.list_tools()
```

---

## Known limitations

- **Single-page responses (25 listings)**. PropertyGuru's `&page=N` query-string is unreliable from non-browser User-Agents (Cloudflare blocks intermittently). Path-style `/{region}/property-for-sale/2` works but is untested in the server. If you need > 25 listings, run multiple freetexts / districts and merge client-side.
- **Cloudflare**. If PropertyGuru starts challenging this server's User-Agent or your IP, you'll get `HTTP 403` errors. Workarounds: slow down request rate; route via a residential proxy; switch to a browser-based toolset (e.g. Hermes `browser_exec`).
- **Field drift**. PropertyGuru can reshape `__NEXT_DATA__` any time. When it does, `search_propertyguru` will raise and you'll need to re-trace the path (look at the live page's `__NEXT_DATA__` in browser DevTools).
- **Singapore + Malaysia only**. PropertyGuru has other regional sites (`propertyguru.co.id`, `.co.th`) — PRs welcome.
- **No autocomplete endpoint**. There's a separate RapidAPI endpoint that does location autocomplete; if you want that here, it's a clean addition (file an issue or open a PR).
- **No detail endpoint**. To get full listing descriptions / floor plans, you need one extra fetch per listing — not implemented yet.

---

## Roadmap

- [ ] Stable multi-page support (handle Cloudflare + path-style `/{n}` pagination)
- [ ] `autocomplete_locations(query)` — return `objectId` / district / MRT proximity
- [ ] `get_listing_detail(listing_url)` — full description, all photos, floor plans
- [ ] Built-in rate limiter (configurable requests/min) to stay polite to PropertyGuru
- [ ] Optional thin server-side projection (e.g. `fields=summary`) to save caller tokens
- [ ] Indonesia / Thailand region support

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome — especially for:

- New regions (Indonesia/Thailand)
- New endpoints (autocomplete, detail, project pages)
- Tests for additional URL parameter combinations
- Better Cloudflare resilience
- Example usage for other MCP clients (Windsurf, Codex, OpenClaw, etc.)

---

## License

MIT — see [LICENSE](LICENSE).

---

## Acknowledgements

Built with [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk). Inspired by the wider community's shared frustration that **real-estate data is artificially locked down** by a handful of aggregators.
