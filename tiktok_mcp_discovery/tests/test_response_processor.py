"""Tests for the TikTokResponseProcessor class."""

import pytest
from datetime import datetime
from TikTokApi.exceptions import InvalidResponseException

from tiktok_mcp_discovery.response_processor import TikTokResponseProcessor

@pytest.fixture
def processor():
    """Create a TikTokResponseProcessor instance."""
    return TikTokResponseProcessor()

@pytest.fixture
def sample_hashtag_response():
    """Sample response for hashtag info."""
    return {
        "challengeInfo": {
            "challenge": {
                "id": "123456",
                "title": "python",
                "desc": "Share your Python coding!",
                "createTime": "1577836800",  # 2020-01-01
                "isCommerce": False
            },
            "stats": {
                "videoCount": 1000,
                "viewCount": 1000000
            }
        }
    }

@pytest.fixture
def sample_user_response():
    """Sample response for user info."""
    return {
        "userInfo": {
            "user": {
                "id": "user123",
                "uniqueId": "pythondev",
                "nickname": "Python Developer",
                "signature": "I code in Python!",
                "verified": True,
                "privateAccount": False,
                "createTime": "1577836800"  # 2020-01-01
            },
            "stats": {
                "followerCount": 10000,
                "followingCount": 100,
                "videoCount": 50,
                "heartCount": 50000
            }
        }
    }

@pytest.fixture
def sample_video_response():
    """Sample response for video info."""
    return {
        "itemInfo": {
            "itemStruct": {
                "id": "video123",
                "desc": "Python coding tutorial",
                "createTime": "1577836800",  # 2020-01-01
                "author": {
                    "id": "user123",
                    "uniqueId": "pythondev"
                },
                "music": {
                    "id": "music123",
                    "title": "Coding Music"
                },
                "stats": {
                    "playCount": 5000,
                    "diggCount": 1000,
                    "commentCount": 100,
                    "shareCount": 50
                },
                "video": {
                    "duration": 60,
                    "height": 1920,
                    "width": 1080
                },
                "challenges": [
                    {"hashtagName": "python"},
                    {"hashtagName": "coding"}
                ]
            }
        }
    }

def test_process_hashtag_info(processor, sample_hashtag_response):
    """Test processing hashtag info response."""
    hashtag = processor.process_hashtag_info(sample_hashtag_response)
    
    assert hashtag.id == "123456"
    assert hashtag.name == "python"
    assert hashtag.desc == "Share your Python coding!"
    assert hashtag.video_count == 1000
    assert hashtag.view_count == 1000000
    assert not hashtag.is_commerce
    assert hashtag.created_at == datetime(2020, 1, 1)

def test_process_hashtag_info_missing_data(processor):
    """Test processing hashtag info with missing data."""
    with pytest.raises(InvalidResponseException):
        processor.process_hashtag_info({})

def test_process_user_info(processor, sample_user_response):
    """Test processing user info response."""
    user = processor.process_user_info(sample_user_response)
    
    assert user.id == "user123"
    assert user.username == "pythondev"
    assert user.nickname == "Python Developer"
    assert user.bio == "I code in Python!"
    assert user.follower_count == 10000
    assert user.following_count == 100
    assert user.video_count == 50
    assert user.heart_count == 50000
    assert user.verified
    assert not user.private
    assert user.created_at == datetime(2020, 1, 1)

def test_process_user_info_missing_data(processor):
    """Test processing user info with missing data."""
    with pytest.raises(InvalidResponseException):
        processor.process_user_info({})

def test_process_video_info(processor, sample_video_response):
    """Test processing video info response."""
    video = processor.process_video_info(sample_video_response)
    
    assert video.id == "video123"
    assert video.desc == "Python coding tutorial"
    assert video.create_time == datetime(2020, 1, 1)
    assert video.author_id == "user123"
    assert video.author_username == "pythondev"
    assert video.music_id == "music123"
    assert video.music_title == "Coding Music"
    assert video.view_count == 5000
    assert video.like_count == 1000
    assert video.comment_count == 100
    assert video.share_count == 50
    assert video.duration == 60
    assert video.height == 1920
    assert video.width == 1080
    assert video.hashtags == ["python", "coding"]

def test_process_video_info_missing_data(processor):
    """Test processing video info with missing data."""
    with pytest.raises(InvalidResponseException):
        processor.process_video_info({})

def test_process_search_results_hashtags(processor, sample_hashtag_response):
    """Test processing hashtag search results."""
    raw_response = {
        "challenge": {
            "challengeInfoList": [
                sample_hashtag_response["challengeInfo"]
            ]
        }
    }
    
    results = processor.process_search_results(raw_response, "hashtag")
    assert len(results) == 1
    assert results[0].name == "python"

def test_process_search_results_users(processor, sample_user_response):
    """Test processing user search results."""
    raw_response = {
        "user": {
            "userInfoList": [
                sample_user_response["userInfo"]
            ]
        }
    }
    
    results = processor.process_search_results(raw_response, "user")
    assert len(results) == 1
    assert results[0].username == "pythondev"

def test_process_search_results_videos(processor, sample_video_response):
    """Test processing video search results."""
    raw_response = {
        "item": {
            "itemInfoList": [
                sample_video_response["itemInfo"]["itemStruct"]
            ]
        }
    }
    
    results = processor.process_search_results(raw_response, "video")
    assert len(results) == 1
    assert results[0].desc == "Python coding tutorial"

def test_process_search_results_invalid_type(processor):
    """Test processing search results with invalid type."""
    with pytest.raises(ValueError):
        processor.process_search_results({}, "invalid_type")

def test_process_search_results_invalid_format(processor):
    """Test processing search results with invalid format."""
    with pytest.raises(InvalidResponseException):
        processor.process_search_results({"invalid": "format"}, "hashtag") 