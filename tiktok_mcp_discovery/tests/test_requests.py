"""Tests for TikTok request handling."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

from TikTokApi.exceptions import (
    CaptchaException,
    InvalidResponseException
)

from tiktok_mcp_discovery.requests import (
    TikTokRequests,
    TikTokRequestError,
    TikTokRateLimitError
)

@pytest.mark.asyncio
async def test_requests_init():
    """Test request handler initialization."""
    mock_session = MagicMock()
    requests = TikTokRequests(
        session=mock_session,
        max_retries=3,
        min_delay=2.0,
        max_delay=5.0,
        jitter_range=0.5
    )
    
    assert requests.session == mock_session
    assert requests.max_retries == 3
    assert requests.min_delay == 2.0
    assert requests.max_delay == 5.0
    assert requests.jitter_range == 0.5
    assert requests.last_request_time is None

@pytest.mark.asyncio
async def test_wait_between_requests():
    """Test request delay timing."""
    mock_session = AsyncMock()
    mock_session.should_rotate.return_value = False
    requests = TikTokRequests(session=mock_session)
    
    # First request should have no delay
    mock_request = AsyncMock()
    mock_request.return_value = {"data": "test"}
    await requests.make_request(mock_request)
    
    # Set last request time
    requests.last_request_time = asyncio.get_event_loop().time()
    
    # Mock sleep to track delay
    with patch("asyncio.sleep") as mock_sleep:
        await requests._wait_between_requests()
        
        # Verify sleep was called with a delay between min and max
        mock_sleep.assert_called_once()
        delay = mock_sleep.call_args[0][0]
        assert 1.5 <= delay <= 5.5  # Including jitter range

@pytest.mark.asyncio
async def test_successful_request():
    """Test successful request flow."""
    mock_session = AsyncMock()
    mock_session.should_rotate.return_value = False
    
    requests = TikTokRequests(session=mock_session)
    
    # Mock request function
    mock_request = AsyncMock()
    mock_request.return_value = {"data": "test"}
    
    # Make request
    result = await requests.make_request(mock_request, "arg1", kwarg1="value1")
    
    # Verify request was made with correct args
    mock_request.assert_called_once_with("arg1", kwarg1="value1")
    assert result == {"data": "test"}
    
    # Verify session checks
    mock_session.should_rotate.assert_called_once()
    mock_session.initialize.assert_not_called()

@pytest.mark.asyncio
async def test_session_rotation():
    """Test session rotation on should_rotate."""
    mock_session = AsyncMock()
    mock_session.should_rotate.return_value = True
    
    requests = TikTokRequests(session=mock_session)
    
    # Mock request function
    mock_request = AsyncMock()
    mock_request.return_value = {"data": "test"}
    
    # Make request
    await requests.make_request(mock_request)
    
    # Verify session was rotated
    mock_session.should_rotate.assert_called_once()
    mock_session.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_captcha_retry():
    """Test retry behavior on captcha error."""
    mock_session = AsyncMock()
    requests = TikTokRequests(session=mock_session)
    
    # Mock request function to fail with captcha then succeed
    mock_request = AsyncMock()
    mock_request.side_effect = [
        CaptchaException(None, "Captcha detected"),
        {"data": "test"}
    ]
    
    # Make request
    result = await requests.make_request(mock_request)
    
    # Verify session was closed and request was retried
    mock_session.close.assert_called_once()
    assert mock_request.call_count == 2
    assert result == {"data": "test"}

@pytest.mark.asyncio
async def test_rate_limit_retry():
    """Test retry behavior on rate limit."""
    mock_session = AsyncMock()
    requests = TikTokRequests(session=mock_session)
    
    # Mock request function to fail with rate limit then succeed
    mock_request = AsyncMock()
    mock_request.side_effect = [
        TikTokRateLimitError("Rate limited"),
        {"data": "test"}
    ]
    
    # Mock sleep to avoid actual delays
    with patch("asyncio.sleep") as mock_sleep:
        # Make request
        result = await requests.make_request(mock_request)
        
        # Verify longer delay was added
        assert any(10.0 <= call_args[0][0] <= 20.0 for call_args in mock_sleep.call_args_list)
        
        # Verify request was retried
        assert mock_request.call_count == 2
        assert result == {"data": "test"}

@pytest.mark.asyncio
async def test_bot_detection_retry():
    """Test retry behavior on bot detection."""
    mock_session = AsyncMock()
    requests = TikTokRequests(session=mock_session)
    
    # Mock request function to fail with bot detection then succeed
    mock_request = AsyncMock()
    mock_request.side_effect = [
        InvalidResponseException(None, "Invalid response, likely bot detection"),
        {"data": "test"}
    ]
    
    # Mock sleep to avoid actual delays
    with patch("asyncio.sleep") as mock_sleep:
        # Make request
        result = await requests.make_request(mock_request)
        
        # Verify session was closed and delay was added
        mock_session.close.assert_called_once()
        assert any(5.0 <= call_args[0][0] <= 10.0 for call_args in mock_sleep.call_args_list)
        
        # Verify request was retried
        assert mock_request.call_count == 2
        assert result == {"data": "test"}

@pytest.mark.asyncio
async def test_max_retries_exceeded():
    """Test error when max retries are exceeded."""
    mock_session = AsyncMock()
    requests = TikTokRequests(session=mock_session, max_retries=2)
    
    # Mock request function to always fail with captcha
    mock_request = AsyncMock()
    mock_request.side_effect = CaptchaException(None, "Captcha detected")
    
    # Verify error is raised after max retries
    with pytest.raises(CaptchaException):
        await requests.make_request(mock_request)
    
    # Verify correct number of retries
    assert mock_request.call_count == 3  # Initial + 2 retries

@pytest.mark.asyncio
async def test_unknown_error():
    """Test handling of unknown errors."""
    mock_session = AsyncMock()
    requests = TikTokRequests(session=mock_session)
    
    # Mock request function to fail with unknown error
    mock_request = AsyncMock()
    mock_request.side_effect = ValueError("Unknown error")
    
    # Verify error is converted to TikTokRequestError
    with pytest.raises(TikTokRequestError) as exc_info:
        await requests.make_request(mock_request)
    
    assert "Unknown error" in str(exc_info.value)
    assert mock_request.call_count == 1  # No retry for unknown errors 