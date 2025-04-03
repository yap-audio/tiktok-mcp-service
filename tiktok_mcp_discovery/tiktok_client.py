"""TikTok API client with integrated session management and anti-bot measures."""

import os
import logging
import asyncio
from typing import Optional, List, Dict, Any, Union, AsyncGenerator
from functools import lru_cache
from contextlib import asynccontextmanager

from TikTokApi import TikTokApi
from TikTokApi.api.video import Video as TikTokVideo
from TikTokApi.api.user import User as TikTokUser
from TikTokApi.api.hashtag import Hashtag as TikTokHashtag
from TikTokApi.exceptions import InvalidResponseException

from .session import TikTokSession
from .requests import TikTokRequests
from .response_processor import TikTokResponseProcessor
from .anti_detection import AntiDetectionConfig

logger = logging.getLogger(__name__)

class TikTokClient:
    """Client for interacting with TikTok API with integrated anti-bot measures."""
    
    def __init__(self):
        """Initialize the TikTok client with all necessary components."""
        # Load environment variables
        self.ms_token = os.environ.get("ms_token")
        self.proxy = os.environ.get("TIKTOK_PROXY") or None  # Convert empty string to None
        
        if not self.ms_token:
            raise ValueError("ms_token environment variable is required")
            
        # Initialize components
        self.anti_detection = AntiDetectionConfig()
        self.response_processor = TikTokResponseProcessor()

    @asynccontextmanager
    async def _session_context(self):
        """Create a new session for a single operation.
        
        This ensures each operation (search, etc) gets its own fresh session
        that is properly cleaned up afterwards.
        
        Yields:
            tuple: (TikTokSession, TikTokRequests) for the operation
        """
        session = None
        try:
            session = TikTokSession(
                ms_token=self.ms_token,
                init_cooldown=300  # Still keep cooldown in case of session reinitialization
            )
            
            # Initialize session with current anti-detection settings
            await session.initialize(proxy=self.proxy)
            
            # Create requests handler for this session
            requests = TikTokRequests(
                session=session,
                max_retries=3,
                min_delay=2.0,
                max_delay=5.0
            )
            
            yield session, requests
            
        finally:
            # Always ensure session is closed if it was created
            if session is not None:
                await session.close()
    
    async def get_hashtag(self, name: str) -> Dict[str, Any]:
        """Get information about a hashtag by name.
        
        Args:
            name: The hashtag name (without the #)
            
        Returns:
            Dict containing processed hashtag information
        """
        # Remove # if present and clean the name
        name = name.lstrip('#').strip().lower()
        logger.info(f"Getting hashtag info for #{name}")
        
        async with self._session_context() as (session, requests):
            try:
                # Use requests module for the API call
                raw_response = await requests.make_request(
                    lambda: session.api.hashtag(name=name).info()
                )
                
                # Process response through our processor
                hashtag = self.response_processor.process_hashtag_info(raw_response)
                return hashtag.to_dict()
                
            except Exception as e:
                logger.error(f"Error getting hashtag info: {str(e)}")
                raise
    
    async def get_hashtag_videos(
        self,
        hashtag_id: str,
        count: int = 30
    ) -> List[Dict[str, Any]]:
        """Get videos for a hashtag using the hashtag ID.
        
        Args:
            hashtag_id: The hashtag ID to fetch videos for
            count: Number of videos to fetch
            
        Returns:
            List of processed video information
        """
        logger.info(f"Fetching videos for hashtag ID {hashtag_id}")
        
        async with self._session_context() as (session, requests):
            try:
                # Get hashtag videos through requests module
                raw_videos = []
                hashtag = session.api.hashtag(id=hashtag_id)
                
                async for video in await requests.make_request(
                    hashtag.videos,
                    count=count
                ):
                    video_info = await requests.make_request(
                        video.info
                    )
                    raw_videos.append(video_info)
                
                # Process each video through our processor
                processed_videos = []
                for raw_video in raw_videos:
                    try:
                        video = self.response_processor.process_video_info({
                            "itemInfo": {"itemStruct": raw_video}
                        })
                        processed_videos.append(video.to_dict())
                    except InvalidResponseException as e:
                        logger.warning(f"Skipping invalid video: {str(e)}")
                
                logger.info(f"Successfully processed {len(processed_videos)} videos for hashtag ID {hashtag_id}")
                return processed_videos
                
            except Exception as e:
                logger.error(f"Error getting videos for hashtag ID {hashtag_id}: {str(e)}")
                raise
    
    async def search_videos(
        self,
        term: str,
        count: int = 30
    ) -> Dict[str, Any]:
        """Search for videos by hashtag or keyword.
        
        For multi-word terms, converts each word into a hashtag and searches all.
        Each search operation uses its own session for better anti-detection.
        
        Args:
            term: Search term or hashtag
            count: Number of videos to return per term
            
        Returns:
            Dict containing:
            - results: Dict mapping terms to lists of processed videos
            - transformations: Any transformations applied to search terms
            - errors: Any errors encountered during search
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
                
                # Search each hashtag with its own session
                all_videos = []
                for hashtag in hashtags:
                    try:
                        # Get hashtag info first (with its own session)
                        hashtag_info = await self.get_hashtag(hashtag)
                        # Then get videos for this hashtag (with its own session)
                        hashtag_videos = await self.get_hashtag_videos(
                            hashtag_info["id"],
                            count
                        )
                        all_videos.extend(hashtag_videos)
                    except Exception as e:
                        logger.error(f"Error searching hashtag '{hashtag}': {str(e)}")
                        errors[hashtag] = str(e)
                        continue
                
                # Deduplicate videos by ID
                seen_ids = set()
                unique_videos = []
                for video in all_videos:
                    if video["id"] not in seen_ids:
                        seen_ids.add(video["id"])
                        unique_videos.append(video)
                
                videos_by_term[original_term] = unique_videos
                logger.info(f"Found {len(unique_videos)} unique videos across all hashtags for '{original_term}'")
                
            else:
                # Single hashtag search
                try:
                    # Get hashtag info and videos (each with their own session)
                    hashtag_info = await self.get_hashtag(term)
                    videos = await self.get_hashtag_videos(
                        hashtag_info["id"],
                        count
                    )
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
    
    async def get_trending_videos(self, count: int = 30) -> List[Dict[str, Any]]:
        """Get trending videos.
        
        Args:
            count: Number of trending videos to fetch
            
        Returns:
            List of processed video information
        """
        logger.info("Fetching trending videos")
        
        async with self._session_context() as (session, requests):
            try:
                raw_videos = []
                async for video in await requests.make_request(
                    lambda: session.api.trending.videos(count=count)
                ):
                    video_info = await requests.make_request(
                        video.info
                    )
                    raw_videos.append(video_info)
                
                # Process videos through our processor
                processed_videos = []
                for raw_video in raw_videos:
                    try:
                        video = self.response_processor.process_video_info({
                            "itemInfo": {"itemStruct": raw_video}
                        })
                        processed_videos.append(video.to_dict())
                    except InvalidResponseException as e:
                        logger.warning(f"Skipping invalid trending video: {str(e)}")
                
                return processed_videos
                
            except Exception as e:
                logger.error(f"Failed to get trending videos: {e}")
                raise 