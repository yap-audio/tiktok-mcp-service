from typing import Dict, Optional, Callable
from dataclasses import dataclass

@dataclass
class Hashtag:
    """
    Represents a TikTok hashtag with its full information.
    """
    id: str  # challengeID in TikTok's API
    name: str  # Name without the #
    info: Dict  # Full info from the hashtag.info() call
    
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
            
        hashtag = cls(
            id=tag_id,
            name=name,
            info=info
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
            'info': self.info,
            'url': f"https://www.tiktok.com/tag/{self.name}"
        } 