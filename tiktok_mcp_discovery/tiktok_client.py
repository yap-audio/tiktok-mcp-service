from TikTokApi import TikTokApi
from TikTokApi.api.video import Video
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
        self.last_location = None
        
        if not self.ms_token:
            logger.warning("No ms_token found in environment. This may cause bot detection issues.")

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
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            logger.info("Creating new TikTokApi instance...")
            self.api = TikTokApi()
            await self.api.__aenter__()
            logger.info("TikTokApi instance created successfully")
            
            # Get random location and browser config
            location = self._get_random_location()
            browser_config = self._get_random_browser_config()
            
            # Create sessions with randomized parameters
            session_params = {
                "ms_tokens": [self.ms_token] if self.ms_token else None,
                "num_sessions": 1,
                "sleep_after": random.randint(15, 20),  # Increased sleep time
                "browser": browser_config["browser"],
                "headless": False,
                "timeout": random.randint(180000, 240000),  # Increased timeout to 3-4 minutes
                "context_options": {
                    "viewport": browser_config["viewport"],
                    "user_agent": browser_config["user_agent"],
                    "locale": "en-US",
                    "timezone_id": "America/New_York",
                    "geolocation": {
                        "latitude": location["latitude"],
                        "longitude": location["longitude"],
                        "accuracy": location["accuracy"]
                    },
                    "permissions": ["geolocation"],
                    "has_touch": random.choice([True, False]),  # Randomize touch capability
                    "color_scheme": random.choice(["light", "dark"]),  # Randomize color scheme
                    "reduced_motion": random.choice(["reduce", "no-preference"])  # Randomize motion preference
                }
            }

            logger.info("Creating TikTok session...")
            await self.api.create_sessions(**session_params)
            # Add extra wait time after session creation
            await asyncio.sleep(random.uniform(8.0, 12.0))  # Increased wait time
            logger.info("TikTok session created successfully")

            logger.info("Applying stealth techniques to session...")
            for session in self.api.sessions:
                # Additional anti-detection scripts
                await session.page.add_init_script("""
                    // Randomize hardware concurrency
                    Object.defineProperty(navigator, 'hardwareConcurrency', {
                        value: """ + str(random.randint(4, 16)) + """
                    });

                    // Randomize device memory
                    Object.defineProperty(navigator, 'deviceMemory', {
                        value: """ + str(random.choice([4, 8, 16])) + """
                    });

                    // Add realistic plugins count
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => {
                            const plugins = [];
                            const count = """ + str(random.randint(3, 8)) + """;
                            for (let i = 0; i < count; i++) {
                                plugins.push({
                                    name: 'Plugin ' + i,
                                    filename: 'plugin' + i + '.dll',
                                    description: 'Generic Plugin ' + i,
                                    length: 1
                                });
                            }
                            return plugins;
                        }
                    });

                    // Add realistic languages
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });

                    // Randomize connection type
                    Object.defineProperty(navigator, 'connection', {
                        get: () => ({
                            effectiveType: """ + json.dumps(random.choice(['4g', '5g'])) + """,
                            rtt: """ + str(random.randint(50, 150)) + """,
                            downlink: """ + str(random.uniform(5, 15)) + """,
                            saveData: false
                        })
                    });

                    // Add realistic WebGL info
                    const getParameter = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function(parameter) {
                        if (parameter === 37445) {
                            return 'Intel Inc.';
                        }
                        if (parameter === 37446) {
                            return 'Intel(R) Iris(TM) Plus Graphics';
                        }
                        return getParameter.apply(this, arguments);
                    };
                """)

                # Add random delay between script applications
                await asyncio.sleep(random.uniform(0.5, 1.5))

            self.last_init_time = time.time()
            logger.info("Session initialization complete")

        except Exception as e:
            logger.error(f"Error initializing API: {str(e)}")
            if self.api:
                await self.api.__aexit__(None, None, None)
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

    async def search_videos(self, term: str, count: int = 30) -> List[Dict[str, Any]]:
        """Search for videos by hashtag or keyword"""
        videos = []
        try:
            # Initialize API if needed
            if not self.api:
                await self._init_api()
                if not self.api:
                    raise RuntimeError("Failed to initialize TikTok API")
            
            # Remove # if present
            term = term.lstrip('#')
            logger.info(f"Searching for term: {term}")
            
            try:
                # Get hashtag info first
                logger.info(f"Getting hashtag info for #{term}...")
                hashtag = await self.api.hashtag(name=term).info()
                logger.info(f"Hashtag info received: {json.dumps(hashtag, indent=2)}")
                
                # Increased delay between info and videos
                logger.info("Waiting before fetching videos...")
                await asyncio.sleep(5)  # Increased from 2 to 5
                
                # Get videos for the hashtag
                logger.info(f"Fetching videos for hashtag #{term}...")
                hashtag_id = hashtag["challengeInfo"]["challenge"]["id"]
                logger.info(f"Got hashtag ID: {hashtag_id}")
                
                # Make direct request to video listing endpoint
                raw_response = await self.api.make_request(
                    url="https://www.tiktok.com/api/challenge/item_list/",
                    params={
                        "challengeID": hashtag_id,
                        "count": count,
                        "cursor": 0
                    }
                )
                logger.info(f"Raw video listing response: {json.dumps(raw_response, indent=2)}")
                
                # Process videos from response
                videos = []
                for item in raw_response.get("itemList", []):
                    video: Video = self.api.video(data=item)
                    videos.append(video)
                    
                logger.info(f"Successfully retrieved {len(videos)} videos for #{term}")
                return videos

            except Exception as e:
                logger.error(f"Error fetching videos for #{term}: {e}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Error args: {e.args}")
                raise
                
        except Exception as e:
            logger.error(f"Failed to search for videos: {e}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error args: {e.args}")
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