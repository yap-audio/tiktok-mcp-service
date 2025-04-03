"""TikTok session management with anti-bot measures."""

import asyncio
import logging
import random
import time
from typing import Optional, Dict, Any

from TikTokApi import TikTokApi
from .anti_detection import AntiDetectionConfig

logger = logging.getLogger(__name__)

class TikTokSession:
    """Manages TikTok API sessions with anti-bot measures."""
    
    def __init__(self, ms_token: Optional[str] = None, init_cooldown: int = 300):
        """Initialize a new session manager.
        
        Args:
            ms_token: Optional TikTok ms_token for authentication
            init_cooldown: Minimum time (seconds) between session reinitializations
        """
        self.ms_token = ms_token
        self.init_cooldown = init_cooldown
        self.last_init_time: Optional[float] = None
        self.anti_detection = AntiDetectionConfig()
        self.api: Optional[TikTokApi] = None
    
    async def initialize(self, proxy: Optional[str] = None) -> None:
        """Initialize or reinitialize the session with anti-bot measures.
        
        Args:
            proxy: Optional proxy to use for the session
        """
        try:
            if self.api:
                await self.api.__aexit__(None, None, None)
            
            # Random initial delay to appear more human-like
            await asyncio.sleep(random.uniform(3.0, 6.0))
            
            logger.info("Creating new TikTokApi instance...")
            self.api = TikTokApi()
            
            # Get next browser and location from anti-detection config
            browser_config = self.anti_detection.get_browser_config()
            location = self.anti_detection.get_next_location(None if not self.last_init_time else self.anti_detection.locations[0])
            
            # Get context options from anti-detection config
            context_options = self.anti_detection.get_context_options(browser_config, location)
            
            # Create sessions with enhanced anti-bot parameters
            session_params = {
                "ms_tokens": [self.ms_token] if self.ms_token else None,
                "num_sessions": 1,  # Start with just one session for simplicity
                "browser": browser_config["browser"],
                "context_options": context_options,
                "suppress_resource_load_types": [
                    "image", "media", "font", "other"  # Suppress non-essential resources
                ],
                "sleep_after": random.uniform(2.0, 4.0),  # Random delay after session creation
                "starting_url": "https://www.tiktok.com/explore",  # Start from explore page
            }
            if proxy:
                session_params["proxies"] = [proxy]
            
            logger.info(f"Creating TikTok session with browser {browser_config['browser']} at location {location['name']}...")
            await self.api.create_sessions(**session_params)
            
            # Add random delay after session creation
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            # Store initialization time
            self.last_init_time = time.time()
            
        except Exception as e:
            logger.error(f"Error initializing session: {str(e)}")
            if self.api:
                try:
                    await self.api.close_sessions()
                except Exception as close_error:
                    logger.error(f"Error closing session: {str(close_error)}")
            raise
    
    async def should_rotate(self) -> bool:
        """Determine if the session should be rotated based on age and random chance.
        
        Returns:
            bool: True if session should be rotated, False otherwise
        """
        if not self.last_init_time:
            return True
            
        current_time = time.time()
        session_age = current_time - self.last_init_time
        
        # Always rotate if session is too old
        if session_age >= self.init_cooldown:
            logger.info("Rotating session due to age")
            return True
            
        # 10% chance of random rotation
        if random.random() < 0.1:
            logger.info("Rotating session randomly")
            return True
            
        return False
    
    async def close(self) -> None:
        """Close the session and clean up resources."""
        if self.api:
            try:
                await self.api.close_sessions()
                self.api = None
                self.last_init_time = None
            except Exception as e:
                logger.error(f"Error closing session: {str(e)}")
                raise 