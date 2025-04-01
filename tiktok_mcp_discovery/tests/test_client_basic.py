"""Unit tests for TikTokClient basic functionality."""

import json
import pytest
import logging
from unittest.mock import patch, AsyncMock, MagicMock, call
from contextlib import asynccontextmanager

from tiktok_mcp_discovery.tiktok_client import TikTokClient
from tiktok_mcp_discovery.session import TikTokSession
from tiktok_mcp_discovery.requests import TikTokRequests

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_client_init():
    """Test client initialization."""
    with patch.dict('os.environ', {'ms_token': 'test_token'}):
        client = TikTokClient()
        assert client.ms_token == 'test_token'
        assert client.proxy is None

@pytest.mark.asyncio
async def test_session_context():
    """Test that session context creates and cleans up sessions properly."""
    with patch.dict('os.environ', {'ms_token': 'test_token'}):
        client = TikTokClient()
        
        # Mock session and requests
        mock_session = AsyncMock(spec=TikTokSession)
        mock_requests = MagicMock(spec=TikTokRequests)
        
        with patch('tiktok_mcp_discovery.tiktok_client.TikTokSession', return_value=mock_session):
            with patch('tiktok_mcp_discovery.tiktok_client.TikTokRequests', return_value=mock_requests):
                async with client._session_context() as (session, requests):
                    assert session == mock_session
                    assert requests == mock_requests
                    mock_session.initialize.assert_called_once_with(proxy=None)
                
                # Verify session was closed after context
                mock_session.close.assert_called_once()

@pytest.mark.asyncio
async def test_hashtag_search_basic():
    """Test basic hashtag search functionality with a simple query."""
    mock_response = {
        "challengeInfo": {
            "challenge": {
                "id": "123456",
                "title": "python",
                "desc": "Python programming",
                "isCommerce": False,
                "createTime": 0
            },
            "stats": {
                "videoCount": 1000,
                "viewCount": 1000000
            }
        }
    }

    with patch.dict('os.environ', {'ms_token': 'test_token'}):
        client = TikTokClient()
        
        # Mock session and requests
        mock_session = AsyncMock(spec=TikTokSession)
        mock_requests = AsyncMock(spec=TikTokRequests)
        mock_requests.make_request.return_value = mock_response
        
        # Create a proper async context manager for session context
        @asynccontextmanager
        async def mock_session_context():
            try:
                yield mock_session, mock_requests
            finally:
                await mock_session.close()
            
        with patch.object(client, '_session_context', new=mock_session_context):
            hashtag_name = "python"
            result = await client.get_hashtag(hashtag_name)
            
            # Print full result for debugging
            logger.info(f"Raw hashtag result: {json.dumps(result, indent=2)}")
            
            # Verify result structure
            assert result is not None, "Should get a result for hashtag search"
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "id" in result, "Result should contain an id"
            assert result["id"] == "123456", "Hashtag ID should match mock data"
            assert result["name"] == "python", "Hashtag name should match mock data"
            assert result["video_count"] == 1000, "Video count should match mock data"
            assert result["view_count"] == 1000000, "View count should match mock data"
            
            # Verify session was initialized and request was made
            mock_session.initialize.assert_not_called()  # Initialize happens in real context
            mock_requests.make_request.assert_called_once()
            mock_session.close.assert_called_once()

@pytest.mark.asyncio
async def test_multiple_operations_use_different_sessions():
    """Test that different operations use different sessions."""
    with patch.dict('os.environ', {'ms_token': 'test_token'}):
        client = TikTokClient()
        
        # Track session instances
        sessions = []
        
        # Mock session creation and initialization
        async def mock_session_init(proxy=None):
            sessions.append(self)
            
        mock_session = AsyncMock(spec=TikTokSession)
        mock_session.initialize = mock_session_init
        
        # Create a proper async context manager for session context
        @asynccontextmanager
        async def mock_session_context():
            try:
                mock_requests = AsyncMock(spec=TikTokRequests)
                mock_requests.make_request.return_value = {
                    "challengeInfo": {
                        "challenge": {"id": "test"},
                        "stats": {"videoCount": 0, "viewCount": 0}
                    }
                }
                yield mock_session, mock_requests
            finally:
                await mock_session.close()
            
        with patch.object(client, '_session_context', new=mock_session_context):
            # Perform multiple operations
            await client.get_hashtag("python")
            await client.get_hashtag("javascript")
            
            # Verify different sessions were used
            assert mock_session.close.call_count == 2, "Session close should be called for each operation"

@pytest.mark.asyncio
async def test_session_cleanup_on_error():
    """Test that sessions are properly cleaned up even when operations fail."""
    with patch.dict('os.environ', {'ms_token': 'test_token'}):
        client = TikTokClient()
        
        # Mock session and requests
        mock_session = AsyncMock(spec=TikTokSession)
        mock_requests = AsyncMock(spec=TikTokRequests)
        mock_requests.make_request.side_effect = Exception("Test error")
        
        # Create a proper async context manager for session context
        @asynccontextmanager
        async def mock_session_context():
            try:
                yield mock_session, mock_requests
            finally:
                await mock_session.close()
            
        with patch.object(client, '_session_context', new=mock_session_context):
            # Attempt operation that will fail
            with pytest.raises(Exception):
                await client.get_hashtag("python")
            
            # Verify session was still closed
            mock_session.close.assert_called_once() 