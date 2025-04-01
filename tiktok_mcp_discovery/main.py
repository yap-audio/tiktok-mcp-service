from mcp.server.fastmcp import FastMCP
import logging
from typing import Dict, Any, List, Tuple, Optional
from tiktok_mcp_discovery.tiktok_client import TikTokClient
from tiktok_mcp_discovery.models import User, Video, Hashtag
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
    return f"""I'll help you find TikTok videos related to: {query}

IMPORTANT: This service ONLY supports single-word hashtag searches (e.g. #cooking, #snowboarding, #fitness).
Multi-word searches or regular keywords are NOT supported.

Examples of valid searches:
- #cooking
- #recipe 
- #chef
- #snowboard
- #workout

Examples of searches that will NOT work:
- cooking videos
- snowboarding influencer
- professional chef
- workout routine

Would you like me to:
1. Search for videos with specific hashtags (must be single words starting with #)
2. Look for trending videos in this category

Please specify which single-word hashtags you'd like to explore!"""

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
                # Transform and validate the search term
                original_term = term
                
                # Process multi-word keywords into individual hashtags
                if ' ' in term:
                    # Split and clean each word, adding # prefix
                    hashtags = [f"#{word.strip().lower()}" for word in term.split() if word.strip()]
                    logger.info(f"Split multi-word search '{term}' into hashtags: {', '.join(hashtags)}")
                    transformations[original_term] = hashtags
                    
                    # Search for each hashtag
                    all_videos = []
                    for hashtag in hashtags:
                        try:
                            tiktok_videos = await tiktok_client.search_videos(hashtag, count=count)
                            
                            # Convert TikTokApi videos to our Video model using from_tiktok_video
                            for tiktok_video in tiktok_videos:
                                video = await Video.from_tiktok_video(
                                    video=tiktok_video,
                                    get_cached_user=get_cached_user,
                                    cache_user=cache_user,
                                    get_cached_hashtag=get_cached_hashtag,
                                    cache_hashtag=cache_hashtag
                                )
                                all_videos.append(video)
                                
                        except Exception as e:
                            logger.error(f"Error searching for hashtag '{hashtag}': {str(e)}")
                            logger.error(f"Error type: {type(e)}")
                            continue
                    
                    # Deduplicate videos
                    seen_ids = set()
                    processed_videos = []
                    
                    for video in all_videos:
                        if video.id not in seen_ids:
                            seen_ids.add(video.id)
                            processed_videos.append(video.to_dict())
                    
                    results[original_term] = processed_videos
                    logger.info(f"Found {len(processed_videos)} unique videos for term '{term}'")
                    logger.info(f"Cached {len(user_cache)} unique users and {len(hashtag_cache)} unique hashtags during this search")
                    
                else:
                    # Handle single word terms similarly
                    all_videos = []
                    try:
                        tiktok_videos = await tiktok_client.search_videos(term, count=count)
                        
                        for tiktok_video in tiktok_videos:
                            video = await Video.from_tiktok_video(
                                video=tiktok_video,
                                get_cached_user=get_cached_user,
                                cache_user=cache_user,
                                get_cached_hashtag=get_cached_hashtag,
                                cache_hashtag=cache_hashtag
                            )
                            all_videos.append(video)
                            
                        # Deduplicate videos
                        seen_ids = set()
                        processed_videos = []
                        
                        for video in all_videos:
                            if video.id not in seen_ids:
                                seen_ids.add(video.id)
                                processed_videos.append(video.to_dict())
                        
                        results[original_term] = processed_videos
                        logger.info(f"Found {len(processed_videos)} videos for term '{term}'")
                        logger.info(f"Cached {len(user_cache)} unique users and {len(hashtag_cache)} unique hashtags during this search")
                        
                    except Exception as e:
                        logger.error(f"Error searching for term '{term}': {str(e)}")
                        logger.error(f"Error type: {type(e)}")
                        results[original_term] = []
                        errors[original_term] = {
                            'error': str(e),
                            'type': str(type(e).__name__)
                        }
                
            except Exception as e:
                logger.error(f"Error searching for term '{term}': {str(e)}")
                logger.error(f"Error type: {type(e)}")
                results[original_term] = []
                errors[original_term] = {
                    'error': str(e),
                    'type': str(type(e).__name__)
                }
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