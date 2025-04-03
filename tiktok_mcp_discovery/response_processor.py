"""Process TikTok API responses into domain models."""

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone

from TikTokApi.exceptions import InvalidResponseException

from .models.hashtag import Hashtag
from .models.user import User
from .models.video import Video

logger = logging.getLogger(__name__)

class TikTokResponseProcessor:
    """Process TikTok API responses into domain models.
    
    This class is responsible for:
    1. Validating raw API responses
    2. Extracting relevant data
    3. Converting to domain models
    4. Handling response-specific errors
    """
    
    def __init__(self):
        """Initialize the response processor."""
        pass
        
    def process_hashtag_info(self, raw_response: Dict[str, Any]) -> Hashtag:
        """Process hashtag info response into a Hashtag model.
        
        Args:
            raw_response: Raw API response for hashtag info
            
        Returns:
            Hashtag model with processed data
            
        Raises:
            InvalidResponseException: If response is missing required fields
        """
        try:
            # Extract challenge info
            challenge_info = raw_response.get("challengeInfo", {})
            if not challenge_info:
                logger.error("Missing challengeInfo in hashtag response")
                raise InvalidResponseException(
                    message="Missing challengeInfo in response",
                    raw_response=raw_response
                )
                
            stats = challenge_info.get("stats", {})
            challenge = challenge_info.get("challenge", {})
            
            # Log missing but non-critical fields
            if not challenge.get("desc"):
                logger.warning("Hashtag description is missing")
            if not stats.get("videoCount"):
                logger.warning("Hashtag video count is missing")
            if not stats.get("viewCount"):
                logger.warning("Hashtag view count is missing")
            
            hashtag = Hashtag(
                id=challenge.get("id"),
                name=challenge.get("title"),
                desc=challenge.get("desc", ""),
                video_count=stats.get("videoCount", 0),
                view_count=stats.get("viewCount", 0),
                is_commerce=bool(challenge.get("isCommerce")),
                created_at=datetime.fromtimestamp(
                    int(challenge.get("createTime", 0)),
                    tz=timezone.utc
                ).replace(tzinfo=None)
            )
            
            logger.info(
                "Successfully processed hashtag %s (id: %s) with %d videos and %d views",
                hashtag.name, hashtag.id, hashtag.video_count, hashtag.view_count
            )
            return hashtag
            
        except (KeyError, TypeError, ValueError) as e:
            logger.error(
                "Failed to process hashtag response: %s. Raw response: %s",
                str(e), raw_response
            )
            raise InvalidResponseException(
                message=f"Invalid hashtag response format: {str(e)}",
                raw_response=raw_response
            )
            
    def process_user_info(self, raw_response: Dict[str, Any]) -> User:
        """Process user info response into a User model.
        
        Args:
            raw_response: Raw API response for user info
            
        Returns:
            User model with processed data
            
        Raises:
            InvalidResponseException: If response is missing required fields
        """
        try:
            # Extract user info
            user_info = raw_response.get("userInfo", {})
            if not user_info:
                logger.error("Missing userInfo in user response")
                raise InvalidResponseException(
                    message="Missing userInfo in response",
                    raw_response=raw_response
                )
                
            stats = user_info.get("stats", {})
            user_data = user_info.get("user", {})
            
            # Log missing but non-critical fields
            if not user_data.get("nickname"):
                logger.warning("User nickname is missing")
            if not user_data.get("signature"):
                logger.warning("User bio/signature is missing")
            if not stats.get("followerCount"):
                logger.warning("User follower count is missing")
            
            user = User(
                id=user_data.get("id"),
                username=user_data.get("uniqueId"),
                nickname=user_data.get("nickname", ""),
                bio=user_data.get("signature", ""),
                follower_count=stats.get("followerCount", 0),
                following_count=stats.get("followingCount", 0),
                video_count=stats.get("videoCount", 0),
                heart_count=stats.get("heartCount", 0),
                verified=bool(user_data.get("verified")),
                private=bool(user_data.get("privateAccount")),
                created_at=datetime.fromtimestamp(
                    int(user_data.get("createTime", 0)),
                    tz=timezone.utc
                ).replace(tzinfo=None)
            )
            
            logger.info(
                "Successfully processed user %s (id: %s) with %d followers",
                user.username, user.id, user.follower_count
            )
            return user
            
        except (KeyError, TypeError, ValueError) as e:
            logger.error(
                "Failed to process user response: %s. Raw response: %s",
                str(e), raw_response
            )
            raise InvalidResponseException(
                message=f"Invalid user response format: {str(e)}",
                raw_response=raw_response
            )
            
    def process_video_info(self, raw_response: Dict[str, Any]) -> Video:
        """Process video info response into a Video model.
        
        Args:
            raw_response: Raw API response for video info
            
        Returns:
            Video model with processed data
            
        Raises:
            InvalidResponseException: If response is missing required fields
        """
        try:
            # Extract video info
            video_info = raw_response.get("itemInfo", {}).get("itemStruct", {})
            if not video_info:
                logger.error("Missing itemStruct in video response")
                raise InvalidResponseException(
                    message="Missing video info in response",
                    raw_response=raw_response
                )
                
            stats = video_info.get("stats", {})
            music = video_info.get("music", {})
            author = video_info.get("author", {})
            video_data = video_info.get("video", {})
            
            # Log missing but non-critical fields
            if not video_info.get("desc"):
                logger.warning("Video description is missing")
            if not music.get("title"):
                logger.warning("Video music title is missing")
            if not video_data.get("duration"):
                logger.warning("Video duration is missing")
            
            video = Video(
                id=video_info.get("id"),
                desc=video_info.get("desc", ""),
                create_time=datetime.fromtimestamp(
                    int(video_info.get("createTime", 0)),
                    tz=timezone.utc
                ).replace(tzinfo=None),
                author_id=author.get("id"),
                author_username=author.get("uniqueId"),
                music_id=music.get("id"),
                music_title=music.get("title", ""),
                view_count=stats.get("playCount", 0),
                like_count=stats.get("diggCount", 0),
                comment_count=stats.get("commentCount", 0),
                share_count=stats.get("shareCount", 0),
                duration=video_data.get("duration", 0),
                height=video_data.get("height", 0),
                width=video_data.get("width", 0),
                hashtags=[
                    tag.get("hashtagName")
                    for tag in video_info.get("challenges", [])
                    if tag.get("hashtagName")
                ]
            )
            
            logger.info(
                "Successfully processed video %s by %s with %d views",
                video.id, video.author_username, video.view_count
            )
            return video
            
        except (KeyError, TypeError, ValueError) as e:
            logger.error(
                "Failed to process video response: %s. Raw response: %s",
                str(e), raw_response
            )
            raise InvalidResponseException(
                message=f"Invalid video response format: {str(e)}",
                raw_response=raw_response
            )
           
    def process_search_results(
        self,
        raw_response: Dict[str, Any],
        result_type: str
    ) -> List[Union[Hashtag, User, Video]]:
        """Process search results into a list of domain models.
        
        Args:
            raw_response: Raw API response from search
            result_type: Type of results ('hashtag', 'user', or 'video')
            
        Returns:
            List of processed models
            
        Raises:
            InvalidResponseException: If response format is invalid
            ValueError: If result_type is invalid
        """
        # Validate result type first
        if result_type not in ["hashtag", "user", "video"]:
            logger.error("Invalid search result type: %s", result_type)
            raise ValueError(f"Invalid result type: {result_type}")
            
        try:
            # Extract search results
            search_results = []
            
            if result_type == "hashtag":
                items = raw_response.get("challenge", {}).get("challengeInfoList", [])
                if not items:
                    logger.error("Missing challengeInfoList in hashtag search response")
                    raise InvalidResponseException(
                        message="Invalid hashtag search response format",
                        raw_response=raw_response
                    )
                for item in items:
                    try:
                        search_results.append(
                            self.process_hashtag_info({"challengeInfo": item})
                        )
                    except InvalidResponseException as e:
                        logger.warning(
                            "Skipping invalid hashtag result: %s. Raw item: %s",
                            str(e), item
                        )
                        
            elif result_type == "user":
                items = raw_response.get("user", {}).get("userInfoList", [])
                if not items:
                    logger.error("Missing userInfoList in user search response")
                    raise InvalidResponseException(
                        message="Invalid user search response format",
                        raw_response=raw_response
                    )
                for item in items:
                    try:
                        search_results.append(
                            self.process_user_info({"userInfo": item})
                        )
                    except InvalidResponseException as e:
                        logger.warning(
                            "Skipping invalid user result: %s. Raw item: %s",
                            str(e), item
                        )
                        
            elif result_type == "video":
                items = raw_response.get("item", {}).get("itemInfoList", [])
                if not items:
                    logger.error("Missing itemInfoList in video search response")
                    raise InvalidResponseException(
                        message="Invalid video search response format",
                        raw_response=raw_response
                    )
                for item in items:
                    try:
                        search_results.append(
                            self.process_video_info({"itemInfo": {"itemStruct": item}})
                        )
                    except InvalidResponseException as e:
                        logger.warning(
                            "Skipping invalid video result: %s. Raw item: %s",
                            str(e), item
                        )
            
            logger.info(
                "Successfully processed %d %s search results",
                len(search_results), result_type
            )
            return search_results
            
        except (KeyError, TypeError) as e:
            logger.error(
                "Failed to process %s search results: %s. Raw response: %s",
                result_type, str(e), raw_response
            )
            raise InvalidResponseException(
                message=f"Invalid search response format: {str(e)}",
                raw_response=raw_response
            ) 