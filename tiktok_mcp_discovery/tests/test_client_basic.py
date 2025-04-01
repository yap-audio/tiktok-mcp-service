import pytest
import logging
import json
from tiktok_mcp_discovery.tiktok_client import TikTokClient

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_client_init():
    """Test that we can create and initialize a TikTokClient instance."""
    client = TikTokClient()
    try:
        await client._init_api()
        assert client.api is not None, "API should be initialized"
    finally:
        await client.close()

@pytest.mark.asyncio
async def test_hashtag_search_basic():
    """Test basic hashtag search functionality with a simple query."""
    client = TikTokClient()
    try:
        await client._init_api()
        # Use a common hashtag that's likely to have results
        hashtag_name = "python"
        result = await client.get_hashtag(hashtag_name)
        
        # Print full result for debugging
        logger.info(f"Raw hashtag result: {json.dumps(result, indent=2)}")
        
        assert result is not None, "Should get a result for hashtag search"
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "id" in result, "Result should contain an id"
        assert result["id"], "Hashtag ID should not be empty"
        
        # Verify we're getting actual video counts (not bot detection response)
        assert "stats" in result, "Result should contain stats"
        assert result["stats"]["video_count"] > 0, "Python hashtag should have videos (if 0, likely bot detection)"
        assert result["stats"]["view_count"] > 0, "Python hashtag should have views (if 0, likely bot detection)"
        
        logger.info(f"Found hashtag info: {result}")
    finally:
        await client.close() 