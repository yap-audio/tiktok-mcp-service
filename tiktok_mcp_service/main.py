from fastapi import FastAPI, HTTPException
from TikTokApi import TikTokApi
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import os
from pathlib import Path
import json
import uvicorn

app = FastAPI(title="TikTok MCP Service")
api: Optional[TikTokApi] = None
captures_dir = Path("captures")

# Ensure captures directory exists
captures_dir.mkdir(exist_ok=True)

@app.on_event("startup")
async def startup_event():
    """Initialize the TikTok API on startup."""
    global api
    api = TikTokApi()
    # Create a session pool - we can adjust num_sessions based on load
    await api.create_sessions(num_sessions=1, sleep_after=3)

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global api
    if api:
        await api.close_sessions()
        api = None

@app.get("/health")
async def health_check() -> Dict:
    """Check if the service is running and initialized."""
    return {
        "status": "ok",
        "initialized": api is not None,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/search")
async def search_videos(keywords: List[str]) -> Dict:
    """
    Search for TikTok videos using the provided keywords.
    
    Args:
        keywords: List of search terms
        
    Returns:
        Dict containing search results with video metadata
    """
    if not api:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    try:
        videos = []
        search_term = " ".join(keywords)
        timestamp = datetime.utcnow().isoformat()
        
        # Search for videos
        async for video in api.search.videos(search_term, count=10):
            # Generate unique filename for screenshot
            video_id = video.id
            screenshot_path = captures_dir / f"{timestamp}_{video_id}.json"
            
            # Save video metadata
            video_data = {
                "url": f"https://www.tiktok.com/@{video.author.username}/video/{video.id}",
                "timestamp": timestamp,
                "metadata": {
                    "id": video.id,
                    "author": video.author.username,
                    "description": video.desc,
                    "stats": {
                        "likes": video.stats.digg_count,
                        "comments": video.stats.comment_count,
                        "shares": video.stats.share_count,
                        "views": video.stats.play_count
                    },
                    "music": {
                        "title": video.music.title,
                        "author": video.music.author
                    } if video.music else None
                }
            }
            
            # Save metadata to file
            with open(screenshot_path, 'w') as f:
                json.dump(video_data, f, indent=2)
            
            videos.append(video_data)
        
        return {
            "success": True,
            "query": search_term,
            "timestamp": timestamp,
            "videos": videos
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cleanup")
async def cleanup() -> Dict:
    """Clean up resources and reset the service."""
    global api
    try:
        if api:
            await api.close_sessions()
            api = None
        return {"success": True, "message": "Service cleaned up successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3333, reload=True) 