from typing import Dict, Optional, Callable
from dataclasses import dataclass

@dataclass
class User:
    """
    Represents a TikTok user.
    """
    id: str
    username: str
    info: Dict
    
    @classmethod
    async def get_or_create(
        cls,
        user_id: str,
        username: str,
        get_info_func,
        get_cached_user: Callable[[str], Optional['User']] = None,
        cache_user: Callable[[str, 'User'], None] = None
    ) -> 'User':
        """
        Get a User from cache or create if not exists.
        
        Args:
            user_id: The TikTok user ID
            username: The TikTok username
            get_info_func: Async function to call for getting user info if needed
            get_cached_user: Optional function to get a cached user
            cache_user: Optional function to cache a user
        """
        # Try to get from cache first
        if get_cached_user:
            user = get_cached_user(user_id)
            if user:
                return user
        
        # If not in cache or no cache functions provided, create new
        info = await get_info_func()
        user = cls(id=user_id, username=username, info=info)
        
        # Cache if caching is enabled
        if cache_user:
            cache_user(user_id, user)
            
        return user
    
    def to_dict(self) -> Dict:
        """Convert User to dictionary representation"""
        return {
            'id': self.id,
            'username': self.username,
            'info': self.info
        } 