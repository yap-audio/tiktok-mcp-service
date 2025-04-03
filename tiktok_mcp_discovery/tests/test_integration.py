"""Integration tests for the TikTok MCP Discovery service."""

import os
import pytest
import logging
from typing import Dict, Any, List
from datetime import datetime

from tiktok_mcp_discovery.tiktok_client import TikTokClient

logger = logging.getLogger(__name__)

def requires_tiktok_auth(func):
    """Decorator to skip tests if TikTok auth is not configured."""
    def wrapper(*args, **kwargs):
        if not os.environ.get("ms_token"):
            pytest.skip("TikTok ms_token not configured")
        return func(*args, **kwargs)
    return wrapper

@pytest.mark.integration
@pytest.mark.asyncio
@requires_tiktok_auth
async def test_hashtag_search_integration():
    """Test hashtag search with real TikTok API."""
    client = TikTokClient()
    
    # Test with a common programming hashtag
    hashtag_name = "python"
    result = await client.get_hashtag(hashtag_name)
    
    # Validate response structure
    assert result is not None
    assert isinstance(result, dict)
    assert "id" in result
    assert "name" in result
    assert "video_count" in result
    assert "view_count" in result
    
    # Validate data types
    assert isinstance(result["id"], str)
    assert isinstance(result["name"], str)
    assert isinstance(result["video_count"], int)
    assert isinstance(result["view_count"], int)
    
    # Log results for manual verification
    logger.info(f"Found hashtag: {result['name']} (ID: {result['id']})")
    logger.info(f"Stats: {result['video_count']} videos, {result['view_count']} views")

@pytest.mark.integration
@pytest.mark.asyncio
@requires_tiktok_auth
async def test_hashtag_videos_integration():
    """Test fetching videos for a hashtag with real TikTok API."""
    client = TikTokClient()
    
    # First get hashtag info
    hashtag_name = "python"
    hashtag = await client.get_hashtag(hashtag_name)
    
    # Then get videos
    videos = await client.get_hashtag_videos(hashtag["id"], count=5)
    
    # Validate response
    assert isinstance(videos, list)
    assert len(videos) > 0
    
    # Validate video structure
    for video in videos:
        assert "id" in video
        assert "desc" in video
        assert "author_id" in video
        assert "author_username" in video
        assert "create_time" in video
        
        # Log video info
        logger.info(
            f"Video {video['id']} by {video['author_username']}: "
            f"{video['desc'][:50]}..."
        )

@pytest.mark.integration
@pytest.mark.asyncio
@requires_tiktok_auth
async def test_search_videos_integration():
    """Test the complete search_videos flow with real TikTok API."""
    client = TikTokClient()
    
    # Test both single and multi-word searches
    search_terms = [
        "python",  # Single word
        "python programming"  # Multi-word
    ]
    
    for term in search_terms:
        # Execute search
        result = await client.search_videos(term=term, count=5)
        
        # Validate response structure
        assert "results" in result
        assert "transformations" in result
        assert "errors" in result
        
        # Check results
        if " " in term:
            # Multi-word search should be transformed
            assert term in result["transformations"]
            transformed = result["transformations"][term]
            logger.info(f"Search term '{term}' was transformed to: {transformed}")
        
        # Validate videos
        videos = result["results"][term]
        assert isinstance(videos, list)
        
        # Log results
        logger.info(f"Found {len(videos)} videos for term '{term}'")
        for video in videos[:3]:  # Log first 3 videos
            logger.info(
                f"Video {video['id']} by {video['author_username']}: "
                f"{video['desc'][:50]}..."
            )

@pytest.mark.integration
@pytest.mark.asyncio
@requires_tiktok_auth
async def test_trending_videos_integration():
    """Test fetching trending videos with real TikTok API."""
    client = TikTokClient()
    
    # Get trending videos
    videos = await client.get_trending_videos(count=5)
    
    # Validate response
    assert isinstance(videos, list)
    assert len(videos) > 0
    
    # Validate video structure
    for video in videos:
        assert "id" in video
        assert "desc" in video
        assert "author_id" in video
        assert "author_username" in video
        assert "create_time" in video
        
        # Log video info
        logger.info(
            f"Trending video {video['id']} by {video['author_username']}: "
            f"{video['desc'][:50]}..."
        )

@pytest.mark.integration
@pytest.mark.asyncio
@requires_tiktok_auth
async def test_session_isolation():
    """Test that sessions are properly isolated between operations."""
    client = TikTokClient()
    
    # Track timing of operations
    start_time = datetime.now()
    
    # Perform multiple operations that should use different sessions
    hashtag = await client.get_hashtag("python")
    videos1 = await client.get_hashtag_videos(hashtag["id"], count=3)
    videos2 = await client.get_hashtag_videos(hashtag["id"], count=3)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Log timing info
    logger.info(f"Completed 3 operations in {duration:.2f} seconds")
    
    # Verify we got results from each operation
    assert hashtag is not None
    assert len(videos1) > 0
    assert len(videos2) > 0
    
    # Verify videos from different sessions are not identical
    # (they might overlap but shouldn't be exactly the same)
    video_ids1 = {v["id"] for v in videos1}
    video_ids2 = {v["id"] for v in videos2}
    assert video_ids1 != video_ids2, "Different sessions should return different videos" 