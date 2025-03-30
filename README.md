# TikTok MCP Service

A Model Context Protocol service for TikTok video discovery and metadata extraction. This service provides a robust interface for searching TikTok videos by hashtags and retrieving trending content, with built-in anti-detection measures and error handling.

## Features

- Search videos by hashtags
- Configurable video count per search (default: 30)
- Anti-bot detection measures
- Proxy support
- Automatic API session management
- Rate limiting and error handling
- Health status monitoring

## Configuration

The service uses environment variables for configuration. Create a `.env` file with:

```env
ms_token=your_tiktok_ms_token  # Optional but recommended to avoid bot detection
TIKTOK_PROXY=your_proxy_url    # Optional proxy configuration
```

## Installation and Setup

```bash
# Install dependencies
poetry install

# Install browser automation dependencies
poetry run python -m playwright install

# Start the service
poetry run python -m tiktok_mcp_service.main
```

## API Endpoints

### Health Check
- `GET /health` - Check service health and API initialization status
  ```json
  {
    "status": "running",
    "api_initialized": true,
    "service": {
      "name": "TikTok MCP Service",
      "version": "0.1.0",
      "description": "A Model Context Protocol service for searching TikTok videos"
    }
  }
  ```

### Search Videos
- `POST /search` - Search for videos with hashtags
  ```json
  {
    "search_terms": ["python", "coding"],
    "count": 30  // Optional, defaults to 30
  }
  ```
  Response includes video URLs, descriptions, and engagement statistics (views, likes, shares, comments).

### Resource Management
- `POST /cleanup` - Clean up resources and API sessions

## Error Handling

The service includes comprehensive error handling for:
- API initialization failures
- Bot detection issues
- Network errors
- Rate limiting
- Invalid search terms

## Development

Built with:
- TikTokApi
- FastMCP
- Poetry for dependency management
- Playwright for browser automation

## License

MIT
