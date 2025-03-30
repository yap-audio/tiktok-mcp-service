import asyncio
import logging
from server import app
from tiktok_client import TikTokClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_client():
    """Test the TikTok client directly"""
    client = TikTokClient()
    
    try:
        # Test initialization
        await client._init_api()
        logger.info("Client initialization successful")
        
        # Test hashtag search
        hashtag = "python"
        logger.info(f"\nTesting hashtag search for #{hashtag}")
        videos = await client.search_videos(hashtag, count=5)
        logger.info(f"Found {len(videos)} videos")
        
        # Show sample results
        for i, video in enumerate(videos[:2], 1):
            logger.info(f"\nVideo {i}:")
            logger.info(f"Description: {video.get('desc', 'N/A')[:100]}...")
            logger.info(f"Stats: {video.get('stats', {})}")
            
    except Exception as e:
        logger.error(f"Client test failed: {str(e)}")
        raise
    finally:
        await client.close()

async def test_server():
    """Test the FastMCP server endpoints"""
    # Test search terms
    search_terms = ["python", "coding"]
    
    try:
        # Test search endpoint
        logger.info("\nTesting search endpoint")
        response = await app.simulate_request(
            "POST",
            "/search",
            json=search_terms
        )
        
        # Check response
        logger.info(f"Response status: {response.get('status')}")
        results = response.get("results", {})
        
        for term, videos in results.items():
            logger.info(f"\nResults for '{term}':")
            logger.info(f"Found {len(videos)} videos")
            
            # Show sample results
            for i, video in enumerate(videos[:2], 1):
                logger.info(f"\nVideo {i}:")
                logger.info(f"URL: {video['url']}")
                logger.info(f"Description: {video['description'][:100]}...")
                logger.info(f"Views: {video['stats']['views']}")
                logger.info(f"Likes: {video['stats']['likes']}")
                
    except Exception as e:
        logger.error(f"Server test failed: {str(e)}")
        raise

async def main():
    """Run all tests"""
    logger.info("Starting tests...")
    
    try:
        await test_client()
        await test_server()
        logger.info("\nAll tests completed successfully!")
    except Exception as e:
        logger.error(f"\nTests failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 