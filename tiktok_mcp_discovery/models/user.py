from typing import Dict, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

@dataclass
class User:
    """
    Represents a TikTok user.
    """
    id: str
    username: str
    nickname: str
    bio: str
    follower_count: int
    following_count: int
    video_count: int
    heart_count: int
    verified: bool
    private: bool
    created_at: datetime
    
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
        
        # Extract user info and stats
        user_info = info.get("userInfo", {})
        user_data = user_info.get("user", {})
        stats = user_info.get("stats", {})
        
        user = cls(
            id=user_id,
            username=username,
            nickname=user_data.get("nickname", ""),
            bio=user_data.get("signature", ""),
            follower_count=stats.get("followerCount", 0),
            following_count=stats.get("followingCount", 0),
            video_count=stats.get("videoCount", 0),
            heart_count=stats.get("heartCount", 0),
            verified=bool(user_data.get("verified", False)),
            private=bool(user_data.get("privateAccount", False)),
            created_at=datetime.fromtimestamp(int(user_data.get("createTime", 0)))
        )
        
        # Cache if caching is enabled
        if cache_user:
            cache_user(user_id, user)
            
        return user
    
    def to_dict(self) -> Dict:
        """Convert User to dictionary representation"""
        return {
            'id': self.id,
            'username': self.username,
            'nickname': self.nickname,
            'bio': self.bio,
            'follower_count': self.follower_count,
            'following_count': self.following_count,
            'video_count': self.video_count,
            'heart_count': self.heart_count,
            'verified': self.verified,
            'private': self.private,
            'created_at': self.created_at.isoformat(),
            'url': f"https://www.tiktok.com/@{self.username}"
        } 