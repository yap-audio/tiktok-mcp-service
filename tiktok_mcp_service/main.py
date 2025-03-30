from mcp.server.fastmcp import FastMCP
import logging
from typing import Dict, Any, List, Tuple
from tiktok_mcp_service.tiktok_client import TikTokClient
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
                
                # Remove any existing hashtag
                term = term.lstrip('#')
                
                # If it contains spaces, transform it
                if ' ' in term:
                    transformed_term = ''.join(term.split())
                    logger.info(f"Transformed multi-word search '{term}' into hashtag '#{transformed_term}'")
                    transformations[original_term] = f"#{transformed_term}"
                    term = transformed_term
                
                # Ensure it's prefixed with #
                if not term.startswith('#'):
                    term = f"#{term}"
                
                # Get videos for the term
                videos = await tiktok_client.search_videos(term, count)
                
                # Process video data
                processed_videos = []
                for video in videos:
                    # Extract video ID and author from video ID string (format: username_id)
                    video_id = video.get('id', '')
                    author = video.get('author', {}).get('uniqueId', '')
                    if not author and '_' in video_id:
                        author = video_id.split('_')[0]
                    
                    processed_videos.append({
                        'url': f"https://www.tiktok.com/@{author}/video/{video_id}",
                        'description': video.get('desc', ''),
                        'stats': {
                            'views': video.get('stats', {}).get('playCount', 0),
                            'likes': video.get('stats', {}).get('diggCount', 0),
                            'shares': video.get('stats', {}).get('shareCount', 0),
                            'comments': video.get('stats', {}).get('commentCount', 0)
                        }
                    })
                
                # Store results under the original term for consistency
                results[original_term] = processed_videos
                logger.info(f"Found {len(processed_videos)} videos for term '{term}'")
                
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
    
    # Include logs, errors, and transformations in the response
    return {
        "results": results,
        "logs": logs,
        "errors": errors,
        "transformations": transformations  # Show what terms were transformed
    }

@mcp.tool()
async def get_trending_videos(count: int = 30) -> Dict[str, Any]:
    """Get trending TikTok videos"""
    logs = []
    errors = {}
    
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
            await asyncio.sleep(2)  # Wait for API to be fully ready
            
        videos = await tiktok_client.get_trending_videos(count)
        processed_videos = []
        
        for video in videos:
            processed_videos.append({
                'url': f"https://www.tiktok.com/@{video.get('author', {}).get('uniqueId', '')}/video/{video.get('id')}",
                'description': video.get('desc', ''),
                'stats': {
                    'views': video.get('stats', {}).get('playCount', 0),
                    'likes': video.get('stats', {}).get('diggCount', 0),
                    'shares': video.get('stats', {}).get('shareCount', 0),
                    'comments': video.get('stats', {}).get('commentCount', 0)
                }
            })
        
        logger.info(f"Found {len(processed_videos)} trending videos")
        return {
            "videos": processed_videos,
            "logs": logs,
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Error getting trending videos: {str(e)}")
        errors["trending"] = {
            "error": str(e),
            "type": str(type(e).__name__)
        }
        return {
            "videos": [],
            "logs": logs,
            "errors": errors
        }
    finally:
        # Remove our custom handler
        logger.removeHandler(log_capture)

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