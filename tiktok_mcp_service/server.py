from fastmcp import FastMCP, Context
import logging
from typing import List, Dict, Any
from tiktok_client import TikTokClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP app
app = FastMCP(
    name="TikTok MCP Service",
    description="A Model Context Protocol service for searching TikTok videos",
    version="0.1.0"
)

# Initialize TikTok client
client = TikTokClient()

@app.tool()
async def search_videos(search_terms: List[str], ctx: Context = None) -> Dict[str, Any]:
    """
    Search for TikTok videos using multiple search terms.
    
    Args:
        search_terms: List of search terms/hashtags to search for
        ctx: Optional FastMCP context for logging and progress tracking
        
    Returns:
        Dictionary containing video information for each search term
    """
    # Initialize API if needed
    if not client.api:
        if ctx:
            await ctx.info("Initializing TikTok API...")
        await client._init_api()
    
    results = {}
    total_terms = len(search_terms)
    
    try:
        # Process each search term
        for i, term in enumerate(search_terms):
            try:
                if ctx:
                    await ctx.info(f"Searching for term: {term}")
                    await ctx.report_progress(i, total_terms)
                
                videos = await client.search_videos(term, count=30)
                
                # Extract relevant video information
                processed_videos = []
                for video in videos:
                    processed_videos.append({
                        'id': video.get('id'),
                        'url': f"https://www.tiktok.com/@{video.get('author', {}).get('uniqueId', '')}/video/{video.get('id')}",
                        'description': video.get('desc'),
                        'stats': {
                            'views': video.get('stats', {}).get('playCount'),
                            'likes': video.get('stats', {}).get('diggCount'),
                            'shares': video.get('stats', {}).get('shareCount'),
                            'comments': video.get('stats', {}).get('commentCount')
                        },
                        'author': {
                            'id': video.get('author', {}).get('id'),
                            'username': video.get('author', {}).get('uniqueId'),
                            'nickname': video.get('author', {}).get('nickname')
                        }
                    })
                
                if ctx:
                    await ctx.info(f"Found {len(processed_videos)} videos for term: {term}")
                results[term] = processed_videos
                
            except Exception as e:
                error_msg = f"Error searching for term '{term}': {str(e)}"
                if ctx:
                    await ctx.error(error_msg)
                results[term] = []
        
        if ctx:
            await ctx.report_progress(total_terms, total_terms)
            
        return results
        
    except Exception as e:
        error_msg = f"Server error: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg)

@app.prompt()
def search_prompt(query: str) -> str:
    """Create a prompt for searching TikTok videos"""
    return f"""I'll help you find TikTok videos related to: {query}

I can search for videos using hashtags or keywords. Would you like me to:
1. Search for specific videos matching your query
2. Look for trending videos in this category
3. Find videos from specific creators

Let me know what you'd like to explore!"""

if __name__ == "__main__":
    app.run() 