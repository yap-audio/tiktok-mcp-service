import pytest
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_hashtag_search(tiktok_client):
    """Test direct hashtag search functionality"""
    hashtag = "python"
    videos = await tiktok_client.search_videos(hashtag, count=5)
    
    assert "results" in videos
    assert hashtag in videos["results"]
    assert len(videos["results"][hashtag]) > 0
    
    # Test video structure
    video = videos["results"][hashtag][0]
    assert video.id is not None
    assert hasattr(video, "description")
    assert hasattr(video, "author")
    assert hasattr(video, "stats")

@pytest.mark.asyncio
async def test_multi_word_search(tiktok_client):
    """Test multi-word search transformation"""
    search_term = "python programming"
    result = await tiktok_client.search_videos(search_term, count=5)
    
    assert "results" in result
    assert search_term in result["results"]
    assert "transformations" in result
    assert search_term in result["transformations"]
    
    # Verify transformations
    transformed_hashtags = result["transformations"][search_term]
    assert len(transformed_hashtags) == 2
    assert "#python" in transformed_hashtags
    assert "#programming" in transformed_hashtags

@pytest.mark.asyncio
async def test_hashtag_info(tiktok_client):
    """Test getting hashtag information"""
    hashtag_name = "python"
    hashtag = await tiktok_client.get_hashtag(hashtag_name)
    
    assert hashtag is not None
    assert hashtag.name == hashtag_name
    assert hashtag.id is not None

@pytest.mark.asyncio
async def test_error_handling(tiktok_client):
    """Test error handling for invalid searches"""
    invalid_term = "!@#$%^"
    result = await tiktok_client.search_videos(invalid_term, count=5)
    
    assert "errors" in result
    assert invalid_term in result["errors"] 