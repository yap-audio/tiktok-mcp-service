"""TikTok API request handling with anti-bot measures."""

import asyncio
import logging
import random
from typing import Any, Dict, Optional, TypeVar, Generic, Callable, Awaitable

import backoff
from TikTokApi.exceptions import (
    TikTokException,
    CaptchaException,
    NotFoundException,
    EmptyResponseException,
    InvalidResponseException
)

from .session import TikTokSession

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Type variable for response data

class TikTokRequestError(TikTokException):
    """Base class for request errors, inheriting from TikTokApi's base exception."""
    def __init__(self, message: str, raw: Any = None):
        super().__init__(raw, message)

class TikTokRateLimitError(TikTokRequestError):
    """Raised when rate limited by TikTok."""
    def __init__(self, message: str = "Rate limit exceeded", raw: Any = None):
        super().__init__(message, raw)

class TikTokRetryableError(TikTokRequestError):
    """Base class for errors that can be retried."""
    def __init__(self, message: str, raw: Any = None):
        super().__init__(message, raw)

class TikTokRequests:
    """Handles TikTok API requests with anti-bot measures."""
    
    def __init__(
        self,
        session: TikTokSession,
        max_retries: int = 3,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        jitter_range: float = 0.5
    ):
        """Initialize request handler.
        
        Args:
            session: TikTok session manager
            max_retries: Maximum number of retries for failed requests
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
            jitter_range: Random jitter range (+/-) in seconds
        """
        self.session = session
        self.max_retries = max_retries
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.jitter_range = jitter_range
        self.last_request_time: Optional[float] = None
    
    async def _wait_between_requests(self) -> None:
        """Add random delay between requests to appear more human-like."""
        if self.last_request_time is not None:
            # Calculate base delay
            delay = random.uniform(self.min_delay, self.max_delay)
            
            # Add random jitter
            jitter = random.uniform(-self.jitter_range, self.jitter_range)
            total_delay = max(0, delay + jitter)
            
            logger.debug(f"Waiting {total_delay:.2f}s between requests")
            await asyncio.sleep(total_delay)
    
    def _should_retry(self, exception: Exception) -> bool:
        """Determine if request should be retried based on exception."""
        if isinstance(exception, (CaptchaException, InvalidResponseException)):
            logger.info("Retryable error detected: %s", str(exception))
            return True
            
        if isinstance(exception, TikTokRateLimitError):
            logger.info("Rate limit detected, will retry with longer delay")
            return True
            
        return False
    
    async def _handle_error(self, exception: Exception) -> None:
        """Handle request errors with appropriate actions."""
        if isinstance(exception, (CaptchaException, InvalidResponseException)):
            # Force session rotation on next request
            logger.info("Rotating session due to %s", exception.__class__.__name__)
            await self.session.close()
            
            if isinstance(exception, InvalidResponseException):
                # Add delay for bot detection
                delay = random.uniform(5.0, 10.0)
                logger.info("Adding %.2fs delay for bot detection", delay)
                await asyncio.sleep(delay)
            
        elif isinstance(exception, TikTokRateLimitError):
            # Add longer delay for rate limits
            delay = random.uniform(10.0, 20.0)
            logger.info("Adding %.2fs delay for rate limit", delay)
            await asyncio.sleep(delay)
    
    @backoff.on_exception(
        backoff.expo,
        (CaptchaException, TikTokRateLimitError, InvalidResponseException),
        max_tries=3,
        giveup=lambda e: not isinstance(e, (CaptchaException, TikTokRateLimitError, InvalidResponseException))
    )
    async def make_request(
        self,
        request_func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any
    ) -> T:
        """Make a TikTok API request with anti-bot measures.
        
        Args:
            request_func: Async function that makes the actual API request
            *args: Positional arguments for request_func
            **kwargs: Keyword arguments for request_func
            
        Returns:
            Response data of type T
            
        Raises:
            CaptchaException: When captcha is detected (will retry)
            InvalidResponseException: When response indicates bot detection (will retry)
            TikTokRateLimitError: When rate limited (will retry)
            TikTokRequestError: For other request failures (won't retry)
        """
        try:
            # Check if session needs rotation
            if await self.session.should_rotate():
                logger.info("Rotating session before request")
                await self.session.initialize()
            
            # Add delay between requests
            await self._wait_between_requests()
            
            # Make request
            response = await request_func(*args, **kwargs)
            
            # Update last request time
            self.last_request_time = asyncio.get_event_loop().time()
            
            return response
            
        except Exception as e:
            if isinstance(e, (CaptchaException, InvalidResponseException, TikTokRateLimitError)):
                # Log retryable errors as info since we handle them
                logger.info("Request failed (will retry): %s", str(e))
            else:
                # Log unexpected errors as errors
                logger.error("Request failed (won't retry): %s", str(e))
            
            # Handle error and determine if we should retry
            if self._should_retry(e):
                await self._handle_error(e)
                raise  # Let backoff handle the retry
                
            # Convert unknown errors to TikTokRequestError
            if not isinstance(e, TikTokRequestError):
                raise TikTokRequestError(
                    message=f"Unexpected error during request: {str(e)}",
                    raw=e
                ) from e
            
            raise 