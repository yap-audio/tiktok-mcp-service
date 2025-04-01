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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize TikTok client
tiktok_client = TikTokClient()

@asynccontextmanager
async def lifespan(server: Server) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle."""
    try:
        # Initialize API on startup
        await tiktok_client._init_api()
        logger.info("TikTok API initialized")
        
        # Add a delay to ensure the API is fully ready
        await asyncio.sleep(4)
        
        yield {"tiktok_client": tiktok_client}
    finally:
        # Clean up on shutdown
        await tiktok_client.close()
        logger.info("TikTok API shutdown complete")

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
    """Search for TikTok videos based on search terms"""
    results = {}
    logs = []
    errors = {}
    transformations = {}
    
    # Create caches for this search session only
    user_cache: Dict[str, User] = {}
    hashtag_cache: Dict[str, Hashtag] = {}
    
    def get_cached_user(user_id: str) -> Optional[User]:
        return user_cache.get(user_id)
        
    def cache_user(user_id: str, user: User):
        user_cache[user_id] = user
        logger.info(f"Cached user info for {user_id}")

    def get_cached_hashtag(tag_id: str) -> Optional[Hashtag]:
        return hashtag_cache.get(tag_id)
        
    def cache_hashtag(tag_id: str, hashtag: Hashtag):
        hashtag_cache[tag_id] = hashtag
        logger.info(f"Cached hashtag info for {tag_id}")
    
    # Create a custom log handler to capture logs
    class LogCapture(logging.Handler):
        def emit(self, record):
            logs.append(self.format(record))
    
    # Add our custom handler
    log_capture = LogCapture()
    log_capture.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(log_capture)
    
    try:
        # Ensure API is initialized
        if not tiktok_client.api:
            await tiktok_client._init_api()
        
        for term in search_terms:
            try:
                # Search for videos using the improved client
                search_result = await tiktok_client.search_videos(term, count=count)
                
                # Process each video through our models
                processed_videos = []
                for original_term, videos in search_result["results"].items():
                    for tiktok_video in videos:
                        video = await Video.from_tiktok_video(
                            video=tiktok_video,
                            get_cached_user=get_cached_user,
                            cache_user=cache_user,
                            get_cached_hashtag=get_cached_hashtag,
                            cache_hashtag=cache_hashtag
                        )
                        processed_videos.append(video.to_dict())
                
                # Store results and any transformations
                results[term] = processed_videos
                if search_result["transformations"]:
                    transformations.update(search_result["transformations"])
                if search_result["errors"]:
                    errors.update(search_result["errors"])
                
                logger.info(f"Processed {len(processed_videos)} videos for term '{term}'")
                logger.info(f"Cached {len(user_cache)} unique users and {len(hashtag_cache)} unique hashtags during this search")
                
            except Exception as e:
                logger.error(f"Error processing term '{term}': {str(e)}")
                results[term] = []
                errors[term] = str(e)
                
    finally:
        # Remove our custom handler
        logger.removeHandler(log_capture)
        # Clear the caches
        user_cache.clear()
        hashtag_cache.clear()
    
    # Include logs, errors, and transformations in the response
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