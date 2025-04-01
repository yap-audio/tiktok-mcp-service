from typing import Dict, Optional, List, Callable
from dataclasses import dataclass
from .user import User
from .hashtag import Hashtag
from TikTokApi.api.video import Video as TikTokVideo

@dataclass
class Video:
    """
    Represents a TikTok video with all its associated data.
    """
    id: str
    description: str
    author: User
    sound: Dict
    hashtags: List[Hashtag]
    stats: Dict
    
    @classmethod
    async def from_tiktok_video(
        cls,
        video: TikTokVideo,
        get_cached_user: Callable[[str], Optional[User]] = None,
        cache_user: Callable[[str, User], None] = None,
        get_cached_hashtag: Callable[[str], Optional[Hashtag]] = None,
        cache_hashtag: Callable[[str, Hashtag], None] = None
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
        # Get or create the User object
        author = await User.get_or_create(
            user_id=video.author.user_id,
            username=video.author.username,
            get_info_func=video.author.info,
            get_cached_user=get_cached_user,
            cache_user=cache_user
        )
        
        # Extract hashtag information
        hashtags = []
        if video.hashtags:  # video.hashtags is Optional[list[TikTokHashtag]]
            for tiktok_tag in video.hashtags:
                hashtag = await Hashtag.get_or_create(
                    tag_id=tiktok_tag.id,
                    name=tiktok_tag.name,
                    get_info_func=tiktok_tag.info,
                    get_cached=get_cached_hashtag,
                    cache=cache_hashtag
                )
                hashtags.append(hashtag)
        
        # Extract sound information
        sound_data = {
            'id': video.sound.id if video.sound else '',
            'title': video.sound.title if video.sound else '',
            'author': video.sound.author_name if video.sound else '',
            'duration': video.sound.duration if video.sound else 0,
            'original': video.sound.original if video.sound else False,
            'play_url': video.sound.play_url if video.sound else ''
        }
        
        return cls(
            id=video.id,
            description=video.description,
            author=author,
            sound=sound_data,
            hashtags=hashtags,
            stats=video.stats  # Pass through the raw stats dictionary
        )
    
    def to_dict(self) -> Dict:
        """Convert Video to dictionary representation"""
        return {
            'id': self.id,
            'description': self.description,
            'author': self.author.to_dict(),
            'url': f"https://www.tiktok.com/@{self.author.username}/video/{self.id}",
            'sound': self.sound,
            'hashtags': [tag.to_dict() for tag in self.hashtags],
            'stats': self.stats
        } 