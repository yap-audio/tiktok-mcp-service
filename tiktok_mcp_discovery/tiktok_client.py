from TikTokApi import TikTokApi
from TikTokApi.api.video import Video as TikTokVideo
from TikTokApi.api.user import User as TikTokUser
from TikTokApi.api.hashtag import Hashtag as TikTokHashtag
import asyncio
import os
from dotenv import load_dotenv
import logging
import json
from typing import Optional, List, Dict, Any, Union
import aiohttp
import backoff
from functools import lru_cache
import time
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NYC Locations for rotation - All within ~2-3 blocks in Financial District
NYC_LOCATIONS = [
    # Base location - 23 Wall Street
    {"latitude": 40.7075, "longitude": -74.0021, "accuracy": 20, "name": "Wall & Broad"},
    # Around the corner - Federal Hall
    {"latitude": 40.7073, "longitude": -74.0102, "accuracy": 20, "name": "Nassau Street"},
    # Down the block - Near NYSE
    {"latitude": 40.7069, "longitude": -74.0113, "accuracy": 20, "name": "NYSE Area"},
    # Slight variation - Near Chase Plaza
    {"latitude": 40.7077, "longitude": -74.0107, "accuracy": 20, "name": "Chase Plaza"},
    # Small movement - Near Trinity Church
    {"latitude": 40.7081, "longitude": -74.0119, "accuracy": 20, "name": "Trinity Church"}
]

# Track last used location for realistic movement
_last_location_index = 0

# Browser configurations for rotation
BROWSER_CONFIGS = [
    {
        "browser": "firefox",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
        "viewport": {"width": 1920, "height": 1080}
    },
    {
        "browser": "webkit",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
        "viewport": {"width": 2560, "height": 1440}
    },
    {
        "browser": "chromium",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "viewport": {"width": 1680, "height": 1050}
    }
]

class TikTokClient:
    """Client for interacting with TikTok API"""
    
    def __init__(self):
        # Load environment variables
        self.ms_token = os.environ.get("ms_token")
        self.proxy = os.environ.get("TIKTOK_PROXY")
        
        self.api: Optional[TikTokApi] = None
        self.last_init_time = 0
        self.init_cooldown = 60  # Minimum seconds between reinitializations
        self.last_location = None  # Track last used location for realistic movement
        
        if not self.ms_token:
            raise ValueError("ms_token environment variable is required")

    def _get_random_location(self) -> Dict[str, Any]:
        """Get a location near the last used location for realistic movement patterns"""
        global _last_location_index
        
        if self.last_location is None:
            # First request - start at base location
            self.last_location = NYC_LOCATIONS[0]
            _last_location_index = 0
            return self.last_location
            
        # Get indices of nearby locations (within 1-2 positions in the list)
        current_idx = _last_location_index
        possible_indices = [
            i for i in range(len(NYC_LOCATIONS))
            if abs(i - current_idx) <= 1  # Only move to adjacent locations
        ]
        
        # Select a nearby location
        new_idx = random.choice(possible_indices)
        _last_location_index = new_idx
        self.last_location = NYC_LOCATIONS[new_idx]
        
        logger.info(f"Moving to nearby location: {self.last_location['name']}")
        return self.last_location

    def _get_random_browser_config(self) -> Dict[str, Any]:
        """Get a random browser configuration"""
        config = random.choice(BROWSER_CONFIGS)
        logger.info(f"Selected browser: {config['browser']}")
        return config

    async def _init_api(self) -> None:
        """Initialize or reinitialize the API with proper error handling"""
        current_time = time.time()
        
        # Don't reinitialize too frequently
        if self.api and (current_time - self.last_init_time) < self.init_cooldown:
            return
        
        try:
            if self.api:
                await self.api.__aexit__(None, None, None)
            
            # Random initial delay to appear more human-like
            await asyncio.sleep(random.uniform(3.0, 6.0))
            
            # Get random configurations
            browser_config = self._get_random_browser_config()
            location = self._get_random_location()
            
            logger.info("Creating new TikTokApi instance...")
            self.api = TikTokApi()
            
            # Create sessions with enhanced anti-bot parameters
            session_params = {
                "ms_tokens": [self.ms_token],
                "num_sessions": 1,  # Start with just one session for simplicity
                "browser": browser_config["browser"],
                "headless": True,
                "context_options": {
                    "viewport": browser_config["viewport"],
                    "user_agent": browser_config["user_agent"],
                    "geolocation": {
                        "latitude": location["latitude"],
                        "longitude": location["longitude"],
                        "accuracy": location["accuracy"]
                    },
                    "locale": "en-US",
                    "timezone_id": "America/New_York",
                    "permissions": ["geolocation"],
                    "color_scheme": "light"
                },
                "suppress_resource_load_types": [
                    "image", "media", "font", "other"  # Suppress non-essential resources
                ],
                "sleep_after": random.uniform(2.0, 4.0),  # Random delay after session creation
                "starting_url": "https://www.tiktok.com/explore",  # Start from explore page instead of direct hashtag access
            }
            if self.proxy:
                session_params["proxies"] = [self.proxy]
                
            logger.info(f"Creating TikTok session with browser {browser_config['browser']} at location {location['name']}...")
            await self.api.create_sessions(**session_params)
            
            # Add random delay after session creation
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            # Store initialization time
            self.last_init_time = time.time()
            self.last_location = location
            
        except Exception as e:
            logger.error(f"Error initializing API: {str(e)}")
            if self.api:
                try:
                    await self.api.close_sessions()
                except Exception as close_error:
                    logger.error(f"Error closing API: {str(close_error)}")
            raise

    async def _should_rotate_session(self) -> bool:
        """Check if we should rotate to a new session based on various factors"""
        if not self.api:
            return True
            
        # Always rotate if we haven't initialized in a while
        if time.time() - self.last_init_time > 300:  # 5 minutes
            logger.info("Rotating session due to age")
            return True
            
        # Random rotation to be unpredictable
        if random.random() < 0.1:  # 10% chance of rotation
            logger.info("Random session rotation")
            return True
            
        return False

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=3,
        max_time=30
    )
    async def _make_request(self, func, *args, **kwargs):
        """Make an API request with retry logic and session management"""
        # Check if we should rotate session
        if await self._should_rotate_session():
            await self._init_api()
            
        if not self.api:
            raise RuntimeError("Failed to initialize TikTok API")
        
        try:
            result = await func(*args, **kwargs)
            # Add random delay between requests
            await asyncio.sleep(random.uniform(2.0, 4.0))
            return result
        except Exception as e:
            logger.error(f"API request failed: {e}")
            # Force reinitialization on next request
            self.last_init_time = 0
            raise

    async def get_hashtag(self, name: str) -> dict:
        """Get information about a hashtag by name.
        
        Args:
            name (str): The hashtag name (without the #)
            
        Returns:
            dict: Hashtag information including id, name, and stats
        """
        try:
            # Remove # if present and clean the name
            name = name.lstrip('#').strip().lower()
            logger.info(f"Getting hashtag info for #{name}")
            
            # Simulate human behavior - random delay before search
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            # Get hashtag info
            hashtag = self.api.hashtag(name=name)
            
            # Random delay before getting info to simulate reading
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            info = await self._make_request(hashtag.info)
            
            # Extract relevant fields from the response
            challenge_info = info.get("challengeInfo", {}).get("challenge", {})
            stats = info.get("challengeInfo", {}).get("stats", {})
            stats_v2 = info.get("challengeInfo", {}).get("statsV2", {})  # Some stats are in statsV2
            
            # Use statsV2 if available, fall back to stats
            video_count = int(stats_v2.get("videoCount", 0)) if stats_v2.get("videoCount") else stats.get("videoCount", 0)
            view_count = int(stats_v2.get("viewCount", 0)) if stats_v2.get("viewCount") else stats.get("viewCount", 0)
            
            # Construct a simplified response
            result = {
                "id": challenge_info.get("id", ""),
                "name": name,
                "desc": challenge_info.get("desc", ""),
                "stats": {
                    "video_count": video_count,
                    "view_count": view_count
                }
            }
            
            logger.info(f"Retrieved hashtag info: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting hashtag info: {str(e)}")
            raise

    async def get_hashtag_videos(self, hashtag_id: str, count: int = 30) -> List[Dict[str, Any]]:
        """Get videos for a hashtag using the hashtag ID"""
        logger.info(f"Fetching videos for hashtag ID {hashtag_id}")
        
        try:
            # Get hashtag object first
            hashtag = self.api.hashtag(id=hashtag_id)
            # Then get videos using the videos method
            videos = []
            async for video in await self._make_request(hashtag.videos, count=count):
                video_info = await video.info()
                videos.append(video_info)
            
            logger.info(f"Successfully retrieved {len(videos)} videos for hashtag ID {hashtag_id}")
            return videos
        except Exception as e:
            logger.error(f"Error getting videos for hashtag ID {hashtag_id}: {str(e)}")
            raise

    async def search_videos(self, term: str, count: int = 30) -> Dict[str, Any]:
        """
        Search for videos by hashtag or keyword.
        For multi-word terms, converts each word into a hashtag and searches all.
        Returns a dict with results, transformations, and any errors.
        """
        videos_by_term = {}
        transformations = {}
        errors = {}
        
        try:
            original_term = term
            
            # Handle multi-word searches
            if ' ' in term:
                # Split into individual hashtags
                hashtags = [f"#{word.strip().lower()}" for word in term.split() if word.strip()]
                logger.info(f"Split multi-word search '{term}' into hashtags: {', '.join(hashtags)}")
                transformations[original_term] = hashtags
                
                # Search each hashtag
                all_videos = []
                for hashtag in hashtags:
                    try:
                        # Get hashtag object
                        hashtag_obj = await self.get_hashtag(hashtag)
                        # Get videos for this hashtag
                        hashtag_videos = await self.get_hashtag_videos(hashtag_obj["challengeID"], count)
                        all_videos.extend(hashtag_videos)
                    except Exception as e:
                        logger.error(f"Error searching hashtag '{hashtag}': {str(e)}")
                        errors[hashtag] = str(e)
                        continue
                
                # Deduplicate videos by ID
                seen_ids = set()
                unique_videos = []
                for video in all_videos:
                    if video.id not in seen_ids:
                        seen_ids.add(video.id)
                        unique_videos.append(video)
                
                videos_by_term[original_term] = unique_videos
                logger.info(f"Found {len(unique_videos)} unique videos across all hashtags for '{original_term}'")
                
            else:
                # Single hashtag search
                try:
                    hashtag_obj = await self.get_hashtag(term)
                    videos = await self.get_hashtag_videos(hashtag_obj["challengeID"], count)
                    videos_by_term[original_term] = videos
                    logger.info(f"Found {len(videos)} videos for '{original_term}'")
                except Exception as e:
                    logger.error(f"Error searching term '{term}': {str(e)}")
                    errors[original_term] = str(e)
                    videos_by_term[original_term] = []
            
            return {
                "results": videos_by_term,
                "transformations": transformations,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to search for videos: {e}")
            raise

    async def get_user(self, username: str) -> TikTokUser:
        """Get user object"""
        logger.info(f"Getting user info for @{username}")
        
        return await self._make_request(
            lambda: self.api.user(username)
        )

    @lru_cache(maxsize=100)
    async def get_trending_videos(self, count: int = 30) -> List[TikTokVideo]:
        """Get trending videos with caching"""
        logger.info("Fetching trending videos")
        
        videos = []
        try:
            async for video in await self._make_request(
                lambda: self.api.trending.videos(count=count)
            ):
                videos.append(video)
        except Exception as e:
            logger.error(f"Failed to get trending videos: {e}")
            raise
            
        return videos

    async def close(self) -> None:
        """Close the API client"""
        if self.api:
            try:
                await self.api.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing API: {str(e)}")
            finally:
                self.api = None 