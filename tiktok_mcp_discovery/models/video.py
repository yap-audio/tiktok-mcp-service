from typing import Dict, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime
from .user import User
from .hashtag import Hashtag
from TikTokApi.api.video import Video as TikTokVideo

@dataclass
class Video:
    """
    Represents a TikTok video with all its associated data.
    """
    id: str
    desc: str
    create_time: datetime
    author_id: str
    author_username: str
    music_id: str
    music_title: str
    view_count: int
    like_count: int
    comment_count: int
    share_count: int
    duration: int
    height: int
    width: int
    hashtags: List[str]
    
    @classmethod
    async def from_tiktok_video(
        cls,
        video: 'TikTokVideo',
        get_cached_user: Callable[[str], Optional['User']] = None,
        cache_user: Callable[[str, 'User'], None] = None,
        get_cached_hashtag: Callable[[str], Optional['Hashtag']] = None,
        cache_hashtag: Callable[[str, 'Hashtag'], None] = None
    ) -> 'Video':
        """
        Create a Video instance from a TikTokApi Video object.
        
        Args:
            video: The TikTokApi Video object
            get_cached_user: Optional function to get a cached user
            cache_user: Optional function to cache a user
            get_cached_hashtag: Optional function to get a cached hashtag
            cache_hashtag: Optional function to cache a hashtag
        """
        # Extract video info
        video_info = await video.info()
        item_struct = video_info.get("itemInfo", {}).get("itemStruct", {})
        
        # Extract author info
        author = item_struct.get("author", {})
        
        # Extract music info
        music = item_struct.get("music", {})
        
        # Extract stats
        stats = item_struct.get("stats", {})
        
        # Extract video dimensions
        video_data = item_struct.get("video", {})
        
        # Extract hashtags
        hashtags = [
            tag.get("hashtagName")
            for tag in item_struct.get("challenges", [])
            if tag.get("hashtagName")
        ]
        
        return cls(
            id=item_struct.get("id", ""),
            desc=item_struct.get("desc", ""),
            create_time=datetime.fromtimestamp(int(item_struct.get("createTime", 0))),
            author_id=author.get("id", ""),
            author_username=author.get("uniqueId", ""),
            music_id=music.get("id", ""),
            music_title=music.get("title", ""),
            view_count=stats.get("playCount", 0),
            like_count=stats.get("diggCount", 0),
            comment_count=stats.get("commentCount", 0),
            share_count=stats.get("shareCount", 0),
            duration=video_data.get("duration", 0),
            height=video_data.get("height", 0),
            width=video_data.get("width", 0),
            hashtags=hashtags
        )
    
    def to_dict(self) -> Dict:
        """Convert Video to dictionary representation"""
        return {
            'id': self.id,
            'desc': self.desc,
            'create_time': self.create_time.isoformat(),
            'author_id': self.author_id,
            'author_username': self.author_username,
            'music_id': self.music_id,
            'music_title': self.music_title,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'share_count': self.share_count,
            'duration': self.duration,
            'height': self.height,
            'width': self.width,
            'hashtags': self.hashtags,
            'url': f"https://www.tiktok.com/@{self.author_username}/video/{self.id}"
        } 