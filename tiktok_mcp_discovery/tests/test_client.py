import asyncio
import logging
from tiktok_mcp_discovery.tiktok_client import TikTokClient

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

async def main():
    """Run all client tests"""
    logger.info("Starting client tests...")
    
    try:
        await test_client()
        logger.info("\nAll client tests completed successfully!")
    except Exception as e:
        logger.error(f"\nClient tests failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 