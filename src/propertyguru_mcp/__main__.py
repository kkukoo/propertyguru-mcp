"""Entry point for `python -m propertyguru_mcp` and the `propertyguru-mcp` script."""

from __future__ import annotations

import asyncio

from propertyguru_mcp.server import main as _main


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
