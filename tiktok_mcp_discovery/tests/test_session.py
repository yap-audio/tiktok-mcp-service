"""Tests for TikTok session management."""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from tiktok_mcp_discovery.session import TikTokSession
from tiktok_mcp_discovery.anti_detection import NYC_LOCATIONS, BROWSER_CONFIGS

@pytest.mark.asyncio
async def test_session_init():
    """Test session initialization with basic parameters."""
    with patch("tiktok_mcp_discovery.session.AntiDetectionConfig") as mock_config:
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        
        session = TikTokSession(ms_token="test_token", init_cooldown=300)
        assert session.ms_token == "test_token"
        assert session.init_cooldown == 300
        assert session.last_init_time is None
        assert session.api is None
        assert session.anti_detection is mock_config_instance

@pytest.mark.asyncio
async def test_session_initialize():
    """Test session initialization with mocked TikTokApi."""
    with patch("tiktok_mcp_discovery.session.TikTokApi") as mock_api:
        # Setup mock API
        mock_api_instance = AsyncMock()
        mock_api.return_value = mock_api_instance
        
        # Setup mock anti-detection config
        mock_config = MagicMock()
        mock_config.get_browser_config.return_value = BROWSER_CONFIGS[0]
        mock_config.get_next_location.return_value = NYC_LOCATIONS[0]
        mock_config.get_context_options.return_value = {
            "viewport": BROWSER_CONFIGS[0]["viewport"],
            "user_agent": BROWSER_CONFIGS[0]["user_agent"],
            "geolocation": {
                "latitude": NYC_LOCATIONS[0]["latitude"],
                "longitude": NYC_LOCATIONS[0]["longitude"],
                "accuracy": NYC_LOCATIONS[0]["accuracy"]
            },
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["geolocation"],
            "color_scheme": "light"
        }
        
        with patch("tiktok_mcp_discovery.session.AntiDetectionConfig", return_value=mock_config):
            session = TikTokSession(ms_token="test_token")
            await session.initialize()
            
            # Verify API was created
            mock_api.assert_called_once()
            
            # Verify anti-detection config was used
            mock_config.get_browser_config.assert_called_once()
            mock_config.get_next_location.assert_called_once()
            mock_config.get_context_options.assert_called_once()
            
            # Verify sessions were created with correct parameters
            create_sessions_call = mock_api_instance.create_sessions.call_args[1]
            assert create_sessions_call["browser"] == BROWSER_CONFIGS[0]["browser"]
            assert create_sessions_call["context_options"]["viewport"] == BROWSER_CONFIGS[0]["viewport"]
            assert create_sessions_call["context_options"]["geolocation"]["latitude"] == NYC_LOCATIONS[0]["latitude"]
            
            # Verify state was updated
            assert session.last_init_time is not None

@pytest.mark.asyncio
async def test_session_rotation():
    """Test session rotation logic."""
    with patch("tiktok_mcp_discovery.session.AntiDetectionConfig") as mock_config:
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        
        session = TikTokSession(init_cooldown=5)  # Short cooldown for testing
        
        # New session should rotate
        assert await session.should_rotate() is True
        
        # Set up an active session
        session.last_init_time = time.time()
        
        # Recent session should not rotate (ignoring random chance)
        with patch("random.random", return_value=0.5):  # Above 0.1 threshold
            assert await session.should_rotate() is False
        
        # Old session should rotate
        session.last_init_time = time.time() - 10  # Older than cooldown
        assert await session.should_rotate() is True
        
        # Test random rotation (10% chance)
        session.last_init_time = time.time()  # Reset to recent
        with patch("random.random", return_value=0.05):  # Below 0.1 threshold
            assert await session.should_rotate() is True

@pytest.mark.asyncio
async def test_session_close():
    """Test session cleanup."""
    with patch("tiktok_mcp_discovery.session.TikTokApi") as mock_api, \
         patch("tiktok_mcp_discovery.session.AntiDetectionConfig") as mock_config:
        # Setup mocks
        mock_api_instance = AsyncMock()
        mock_api.return_value = mock_api_instance
        
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        
        session = TikTokSession()
        session.api = mock_api_instance
        session.last_init_time = time.time()
        
        await session.close()
        
        # Verify cleanup
        mock_api_instance.close_sessions.assert_called_once()
        assert session.api is None
        assert session.last_init_time is None

@pytest.mark.asyncio
async def test_session_error_handling():
    """Test error handling during session operations."""
    with patch("tiktok_mcp_discovery.session.TikTokApi") as mock_api, \
         patch("tiktok_mcp_discovery.session.AntiDetectionConfig") as mock_config:
        # Setup mocks
        mock_api_instance = AsyncMock()
        mock_api_instance.create_sessions.side_effect = Exception("API Error")
        mock_api.return_value = mock_api_instance
        
        # Setup mock config with proper dictionary behavior
        mock_browser_config = {
            "browser": "test-browser",
            "viewport": {"width": 1280, "height": 720},
            "user_agent": "test-user-agent"
        }
        
        mock_location = {
            "name": "test-location",
            "latitude": 40.7075,
            "longitude": -74.0021,
            "accuracy": 20
        }
        
        mock_config_instance = MagicMock()
        mock_config_instance.get_browser_config.return_value = mock_browser_config
        mock_config_instance.get_next_location.return_value = mock_location
        mock_config_instance.get_context_options.return_value = {
            "viewport": mock_browser_config["viewport"],
            "user_agent": mock_browser_config["user_agent"],
            "geolocation": {
                "latitude": mock_location["latitude"],
                "longitude": mock_location["longitude"],
                "accuracy": mock_location["accuracy"]
            }
        }
        mock_config.return_value = mock_config_instance
        
        session = TikTokSession()
        
        # Verify error is propagated
        with pytest.raises(Exception) as exc_info:
            await session.initialize()
        assert str(exc_info.value) == "API Error"
        
        # Verify cleanup was attempted
        mock_api_instance.close_sessions.assert_called_once() 