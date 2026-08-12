# Contributing to propertyguru-mcp

Thanks for considering a contribution!  This project is intentionally small and focused — we want to keep it useful, not feature-bloated.

## What we're looking for

- Bug fixes (with a way to reproduce)
- New region support (Indonesia, Thailand regional PropertyGuru sites)
- New endpoints that match what the site already serves (autocomplete, listing detail, project pages)
- Better Cloudflare resilience that doesn't pessimize the happy path
- Documentation / examples for MCP clients we haven't covered yet

## What we're NOT looking for

- Features that require a real backend / database / login
- Re-architecting to use a real browser (the entire point is "no browser, no API key")
- A paid tier / monetization (this is a community tool)
- PropertyGuru trademark usage beyond bare factual references

## How to submit a PR

1. Fork the repo, create a branch like `feat/kuala-lumpur-region` or `fix/cloudflare-403-propagation`.
2. Make your change.  Add a test if you changed URL-building or parsing logic.
3. Run the tests:
   ```bash
   PYTHONPATH=src python -m pytest tests/ -v
   ```
4. Update the README's "Roadmap" section if you closed something.
5. Open a PR with a summary of what changed and **why**.  Include a sample command we can run to verify (e.g. a specific search_listings call that now works that didn't before).

## Style

- Python 3.10+ type hints.
- No new runtime dependencies unless absolutely necessary.
- Keep `search_propertyguru` synchronous (MCP stdio handles it).
- Don't add logging at INFO-level by default — the server should be silent unless `MCP_LOG_LEVEL` is set.

## Code of Conduct

Be nice.  Legitimate disagreement is fine.  Don't use issues to promote for-profit PropertyGuru API services or unauthorized commercial scraping pipelines.
