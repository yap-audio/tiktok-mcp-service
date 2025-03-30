from TikTokApi import TikTokApi
import asyncio
import os
from dotenv import load_dotenv
import logging
import json
from typing import Optional, List, Dict, Any
import aiohttp
import backoff
from functools import lru_cache
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TikTokClient:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Get configuration from environment
        self.ms_token = os.environ.get("ms_token")
        self.proxy = os.environ.get("TIKTOK_PROXY")
        
        # Initialize API instance
        self.api = None
        self.last_init_time = 0
        self.init_cooldown = 60  # Seconds to wait before reinitializing API
        
        if not self.ms_token:
            logger.warning("No ms_token found in environment. This may cause bot detection issues.")

    async def _init_api(self) -> None:
        """Initialize or reinitialize the API with proper error handling"""
        current_time = time.time()
        
        # Don't reinitialize too frequently
        if self.api and (current_time - self.last_init_time) < self.init_cooldown:
            return
            
        try:
            if self.api:
                await self.api.__aexit__(None, None, None)
            
            self.api = TikTokApi()
            await self.api.__aenter__()
            
            # Create sessions with proxy if available
            session_params = {
                "ms_tokens": [self.ms_token] if self.ms_token else None,
                "num_sessions": 1,
                "sleep_after": 3,
                "browser": "webkit",
                "headless": False,
                "timeout": 60000,  # Increase timeout to 60 seconds
                "context_options": {
                    "viewport": {
                        "width": 1920,
                        "height": 1080
                    }
                },
                "suppress_resource_load_types": [
                    "image",
                    "media",
                    "font",
                    "other"
                ]  # Speed up page load by suppressing non-essential resources
            }
            
            if self.proxy:
                # Use proxy through playwright's proxy configuration
                logger.info(f"Using proxy: {self.proxy}")
                session_params["proxies"] = [self.proxy]
            
            # Create the session
            await self.api.create_sessions(**session_params)
            
            # Add anti-detection scripts to each session
            for session in self.api.sessions:
                await session.page.add_init_script("""
                    // Remove webdriver
                    delete Object.getPrototypeOf(navigator).webdriver;
                    
                    // Update navigator properties
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                    });
                    
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => false,
                    });
                    
                    // Add Chrome Runtime
                    window.chrome = {
                        runtime: {},
                    };
                    
                    // Modify WebGL vendor and renderer
                    const getParameter = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function(parameter) {
                        if (parameter === 37445) {
                            return 'Intel Inc.';
                        }
                        if (parameter === 37446) {
                            return 'Intel Iris OpenGL Engine';
                        }
                        return getParameter.apply(this, arguments);
                    };
                """)
            
            self.last_init_time = current_time
            logger.info("TikTok API initialized successfully with anti-detection configuration")
            
            # Wait a moment for the session to be fully ready
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Failed to initialize TikTok API: {e}")
            if self.api:
                try:
                    await self.api.__aexit__(None, None, None)
                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup after failed initialization: {cleanup_error}")
            self.api = None
            raise

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=3,
        max_time=30
    )
    async def _make_request(self, func, *args, **kwargs):
        """Make an API request with retry logic"""
        if not self.api:
            await self._init_api()
            if not self.api:
                raise RuntimeError("Failed to initialize TikTok API")
        
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"API request failed: {e}")
            # Force reinitialization on next request
            self.last_init_time = 0
            raise

    @lru_cache(maxsize=100)
    async def get_trending_videos(self, count: int = 30) -> List[Dict[str, Any]]:
        """Get trending videos with caching"""
        videos = []
        try:
            # Initialize API if needed
            if not self.api:
                await self._init_api()
                if not self.api:
                    raise RuntimeError("Failed to initialize TikTok API")
            
            # Get trending videos
            async for video in self.api.trending.videos(count=count):
                videos.append(video.as_dict)
                
        except Exception as e:
            logger.error(f"Failed to get trending videos: {e}")
            raise
        return videos

    async def search_videos(self, query: str, count: int = 30) -> List[Dict[str, Any]]:
        """Search for videos by hashtag or keyword"""
        videos = []
        try:
            # Initialize API if needed
            if not self.api:
                await self._init_api()
                if not self.api:
                    raise RuntimeError("Failed to initialize TikTok API")
            
            # Remove # if present
            query = query.lstrip('#')
            logger.info(f"Searching for term: {query}")
            
            try:
                # Get hashtag info first
                logger.info(f"Getting hashtag info for #{query}...")
                hashtag = await self.api.hashtag(name=query).info()
                logger.info(f"Hashtag info received: {json.dumps(hashtag, indent=2)}")
                
                # Add a small delay between getting info and videos
                await asyncio.sleep(2)
                
                # Get videos for the hashtag
                logger.info(f"Fetching videos for hashtag #{query}...")
                video_count = 0
                
                # Create video iterator
                video_iterator = self.api.hashtag(name=query).videos(count=count)
                logger.info("Created video iterator")
                
                try:
                    async for video in video_iterator:
                        video_count += 1
                        logger.info(f"Retrieved video {video_count}/{count}")
                        logger.debug(f"Video data: {json.dumps(video.as_dict, indent=2)}")
                        videos.append(video.as_dict)
                        
                        # Add a small delay between video fetches
                        await asyncio.sleep(0.5)
                        
                        # Break if we've reached the desired count
                        if video_count >= count:
                            break
                except Exception as e:
                    logger.error(f"Error during video iteration: {e}")
                    logger.error(f"Error type: {type(e)}")
                    raise
                
                logger.info(f"Successfully retrieved {len(videos)} videos for #{query}")
                return videos
                
            except Exception as e:
                logger.error(f"Error fetching videos for #{query}: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Failed to search for videos: {e}")
            raise

    async def get_user_info(self, username: str) -> Dict[str, Any]:
        """Get user information"""
        try:
            # Initialize API if needed
            if not self.api:
                await self._init_api()
                if not self.api:
                    raise RuntimeError("Failed to initialize TikTok API")
            
            # Get user info
            user = await self.api.user(username).info()
            if isinstance(user, dict):
                return user
            return user.as_dict
            
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            raise

    async def close(self):
        """Cleanup resources"""
        if self.api:
            try:
                await self.api.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing API: {e}")
            self.api = None 