# TikTok MCP Service

A Model Context Protocol service for TikTok video discovery and metadata extraction.

## Running the Service

```bash
poetry install
poetry run python -m playwright install
poetry run python -m tiktok_mcp_service.main
```

## API Endpoints

- `GET /health` - Check service health
- `POST /search` - Search for videos with keywords
  ```json
  {
    "keywords": ["search", "terms"]
  }
  ```
- `POST /cleanup` - Clean up resources 