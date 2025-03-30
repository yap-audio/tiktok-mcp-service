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

I can search for videos using hashtags or keywords. Would you like me to:
1. Search for specific videos matching your query
2. Look for trending videos in this category
3. Find videos from specific creators

Let me know what you'd like to explore!"""

@mcp.tool()
async def search_videos(search_terms: List[str], count: int = 30) -> Dict[str, Any]:
    """Search for TikTok videos based on search terms"""
    results = {}
    
    for term in search_terms:
        try:
            # Get videos for the term
            videos = await tiktok_client.search_videos(term, count)
            
            # Process video data
            processed_videos = []
            for video in videos:
                processed_videos.append({
                    'url': f"https://www.tiktok.com/@{video.get('author', {}).get('uniqueId', '')}/video/{video.get('id')}",
                    'description': video.get('desc'),
                    'stats': {
                        'views': video.get('stats', {}).get('playCount'),
                        'likes': video.get('stats', {}).get('diggCount'),
                        'shares': video.get('stats', {}).get('shareCount'),
                        'comments': video.get('stats', {}).get('commentCount')
                    }
                })
            
            results[term] = processed_videos
            logger.info(f"Found {len(processed_videos)} videos for term '{term}'")
            
        except Exception as e:
            logger.error(f"Error searching for term '{term}': {str(e)}")
            results[term] = []
    
    return results

@mcp.tool()
async def get_trending_videos(count: int = 30) -> Dict[str, Any]:
    """Get trending TikTok videos"""
    try:
        videos = await tiktok_client.get_trending_videos(count)
        processed_videos = []
        
        for video in videos:
            processed_videos.append({
                'url': f"https://www.tiktok.com/@{video.get('author', {}).get('uniqueId', '')}/video/{video.get('id')}",
                'description': video.get('desc'),
                'stats': {
                    'views': video.get('stats', {}).get('playCount'),
                    'likes': video.get('stats', {}).get('diggCount'),
                    'shares': video.get('stats', {}).get('shareCount'),
                    'comments': video.get('stats', {}).get('commentCount')
                }
            })
        
        logger.info(f"Found {len(processed_videos)} trending videos")
        return {
            "videos": processed_videos
        }
    except Exception as e:
        logger.error(f"Error getting trending videos: {str(e)}")
        return {
            "error": str(e)
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