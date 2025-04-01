"""TikTok MCP Discovery Service main module."""

from mcp.server.fastmcp import FastMCP
import logging
from typing import Dict, Any, List, Tuple, Optional
from tiktok_mcp_discovery.tiktok_client import TikTokClient
from tiktok_mcp_discovery.models import User, Video, Hashtag
from tiktok_mcp_discovery.prompts import get_search_prompt
import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from mcp.server import Server
import json
import mcp.server.stdio
from mcp.server.models import InitializationOptions
from TikTokApi.exceptions import (
    InvalidResponseException,
    CaptchaException,
    TikTokException
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize TikTok client
tiktok_client = TikTokClient()

@asynccontextmanager
async def lifespan(server: Server) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle."""
    try:
        # Initialize client (which handles session and anti-detection setup)
        await tiktok_client._init_api()
        logger.info("TikTok client initialized with all components")
        
        yield {"tiktok_client": tiktok_client}
    finally:
        # Clean up client (which handles all component cleanup)
        await tiktok_client.close()
        logger.info("TikTok client and components shutdown complete")

# Initialize FastMCP app with lifespan
mcp = FastMCP(
    name="TikTok MCP Service",
    description="A Model Context Protocol service for searching TikTok videos",
    version="0.1.0",
    lifespan=lifespan
)

@mcp.resource("status://health")
async def get_health_status() -> Tuple[str, str]:
    """Get the current health status of the service"""
    status = {
        "status": "running",
        "api_initialized": tiktok_client.api is not None,
        "service": {
            "name": "TikTok MCP Service",
            "version": "0.1.0",
            "description": "A Model Context Protocol service for searching TikTok videos"
        }
    }
    return json.dumps(status, indent=2), "application/json"

@mcp.prompt()
def search_prompt(query: str) -> str:
    """Create a prompt for searching TikTok videos"""
    return get_search_prompt(query)

@mcp.tool()
async def search_videos(search_terms: List[str], count: int = 30) -> Dict[str, Any]:
    """Search for TikTok videos based on search terms.
    
    Args:
        search_terms: List of search terms to query
        count: Number of videos to return per term (default: 30)
        
    Returns:
        Dictionary containing:
        - results: Processed video results for each search term
        - logs: Captured log messages during processing
        - errors: Any errors encountered during processing
        - transformations: Search term transformations applied
    """
    results = {}
    logs = []
    errors = {}
    transformations = {}
    
    # Create a custom log handler to capture logs
    class LogCapture(logging.Handler):
        def emit(self, record):
            logs.append(self.format(record))
    
    # Add our custom handler
    log_capture = LogCapture()
    log_capture.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(log_capture)
    
    try:
        for term in search_terms:
            try:
                # Validate search term
                if not term or not term.strip():
                    raise ValueError("Empty search term")
                if len(term) > 100:
                    raise ValueError("Search term too long")
                
                # Use TikTokClient for search (it handles session management, retries, etc.)
                search_result = await tiktok_client.search_videos(
                    term=term,
                    count=count
                )
                
                # Store results and metadata
                results[term] = search_result["results"].get(term, [])
                if search_result.get("transformations"):
                    transformations[term] = search_result["transformations"].get(term)
                if search_result.get("errors"):
                    errors[term] = search_result["errors"].get(term)
                
                logger.info(
                    f"Processed {len(results[term])} videos for term '{term}'"
                )
                
            except ValueError as e:
                logger.error(f"Invalid search term '{term}': {str(e)}")
                errors[term] = str(e)
                results[term] = []
                
            except (InvalidResponseException, CaptchaException) as e:
                logger.error(f"API error for term '{term}': {str(e)}")
                errors[term] = str(e)
                results[term] = []
                
            except TikTokException as e:
                logger.error(f"TikTok error for term '{term}': {str(e)}")
                errors[term] = str(e)
                results[term] = []
                
            except Exception as e:
                logger.error(f"Unexpected error processing term '{term}': {str(e)}")
                errors[term] = str(e)
                results[term] = []
                
    finally:
        # Remove our custom handler
        logger.removeHandler(log_capture)
    
    return {
        "results": results,
        "logs": logs,
        "errors": errors,
        "transformations": transformations
    }

def main():
    """Start the MCP server"""
    logger.info("Starting TikTok MCP Service (press Ctrl+C to stop)")
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Shutting down TikTok MCP Service")
    except Exception as e:
        logger.error(f"Error running MCP server: {str(e)}")
        raise

if __name__ == "__main__":
    main() 