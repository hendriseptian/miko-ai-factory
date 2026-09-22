# Miko AI Factory Worker

Cloudflare Worker control/orchestration layer.

## Current scope
- Health endpoint
- Foundation API response
- No provider API keys hard-coded
- Ready for later provider adapters

## Planned modules
- story provider
- image provider
- video provider
- voice provider
- quota manager
- Google Drive archive adapter
- project/version metadata
- QC API

Provider credentials should be stored as Cloudflare secrets, not committed to GitHub.
