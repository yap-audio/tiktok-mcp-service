from typing import Dict, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Hashtag:
    """
    Represents a TikTok hashtag with its full information.
    """
    id: str  # challengeID in TikTok's API
    name: str  # Name without the #
    desc: str  # Description of the hashtag
    video_count: int  # Number of videos using this hashtag
    view_count: int  # Total views across all videos
    is_commerce: bool  # Whether this is a commerce hashtag
    created_at: datetime  # When the hashtag was created
    
    @classmethod
    async def get_or_create(
        cls,
        tag_id: str,
        name: str,
        get_info_func,
        get_cached: Callable[[str], Optional['Hashtag']] = None,
        cache: Callable[[str, 'Hashtag'], None] = None
    ) -> 'Hashtag':
        """
        Get a Hashtag from cache or create if not exists.
        
        Args:
            tag_id: The TikTok hashtag ID (challengeID)
            name: The hashtag name (without #)
            get_info_func: Async function to call for getting hashtag info
            get_cached: Optional function to get a cached hashtag
            cache: Optional function to cache a hashtag
        """
        # Try to get from cache first
        if get_cached:
            hashtag = get_cached(tag_id)
            if hashtag:
                return hashtag
        
        # If not in cache or no cache functions provided, create new
        info = await get_info_func()
        
        # Extract the ID from the info if not provided
        if not tag_id and info:
            tag_id = info.get("challengeID", "")
            
        # Extract fields from info
        challenge = info.get("challengeInfo", {}).get("challenge", {})
        stats = info.get("challengeInfo", {}).get("stats", {})
        
        hashtag = cls(
            id=tag_id,
            name=name,
            desc=challenge.get("desc", ""),
            video_count=stats.get("videoCount", 0),
            view_count=stats.get("viewCount", 0),
            is_commerce=bool(challenge.get("isCommerce", False)),
            created_at=datetime.fromtimestamp(int(challenge.get("createTime", 0)))
        )
        
        # Cache if caching is enabled
        if cache:
            cache(tag_id, hashtag)
            
        return hashtag
    
    def to_dict(self) -> Dict:
        """Convert Hashtag to dictionary representation"""
        return {
            'id': self.id,
            'name': self.name,
            'desc': self.desc,
            'video_count': self.video_count,
            'view_count': self.view_count,
            'is_commerce': self.is_commerce,
            'created_at': self.created_at.isoformat(),
            'url': f"https://www.tiktok.com/tag/{self.name}"
        } 