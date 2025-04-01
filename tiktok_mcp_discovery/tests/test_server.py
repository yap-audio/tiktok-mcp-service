import asyncio
import json
import logging
import os
from pathlib import Path
import pytest
from typing import Dict, Any

from mcp import ClientSession, StdioServerParameters, stdio_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_server():
    # Get absolute path to main.py
    main_py = str(Path(__file__).parent.parent / "main.py")
    logger.info(f"Using server script at: {main_py}")

    # Create server parameters
    server_params = StdioServerParameters(
        command="python",
        args=[main_py],
        env=None  # Use current environment
    )

    try:
        logger.info("Starting stdio client...")
        async with stdio_client(server_params) as (read, write):
            logger.info("Stdio client started, creating session...")
            async with ClientSession(read, write) as session:
                # Initialize connection with longer timeout
                try:
                    logger.info("Initializing server connection...")
                    await asyncio.wait_for(session.initialize(), timeout=120.0)
                    logger.info("Server connection initialized successfully")
                except asyncio.TimeoutError:
                    logger.error("Server initialization timed out after 120 seconds")
                    raise
                except Exception as e:
                    logger.error(f"Server initialization failed: {str(e)}")
                    logger.error(f"Error type: {type(e)}")
                    raise

                # Test health endpoint
                logger.info("\nTesting health endpoint")
                try:
                    response = await session.read_resource("status://health")
                    health_json = json.loads(response.contents[0].text)
                    # health_json is a list containing [json_string, mime_type]
                    health_data = json.loads(health_json[0])
                    mime_type = health_json[1]
                    logger.info(f"Health status: {health_data}")
                    assert mime_type == "application/json"
                    assert health_data["status"] == "running"
                    assert health_data["api_initialized"] is True
                    logger.info("Health check passed")
                except Exception as e:
                    logger.error(f"Health endpoint test failed: {str(e)}")
                    raise

                # Test search endpoint
                logger.info("\nTesting search endpoint")
                try:
                    # Test multi-word search transformation
                    logger.info("\nTesting multi-word search transformation...")
                    multi_word_result = await session.call_tool("search_videos", arguments={"search_terms": ["snowboarder influencer", "professional snowboarder"]})
                    multi_word_data = json.loads(multi_word_result.content[0].text)
                    
                    # Verify transformations
                    transformations = multi_word_data.get("transformations", {})
                    logger.info(f"Search transformations: {transformations}")
                    assert "snowboarder influencer" in transformations, "Missing transformation for 'snowboarder influencer'"
                    assert "professional snowboarder" in transformations, "Missing transformation for 'professional snowboarder'"
                    
                    # Verify transformed searches returned results
                    snowboarder_influencer_videos = multi_word_data["results"].get("snowboarder influencer", [])
                    professional_snowboarder_videos = multi_word_data["results"].get("professional snowboarder", [])
                    
                    logger.info(f"Found {len(snowboarder_influencer_videos)} videos for 'snowboarder influencer'")
                    logger.info(f"Found {len(professional_snowboarder_videos)} videos for 'professional snowboarder'")
                    
                    # At least one of the transformed searches should return results
                    assert len(snowboarder_influencer_videos) > 0 or len(professional_snowboarder_videos) > 0, "No videos found for any transformed search terms"
                    
                    # Verify video structure for multi-word results
                    for video in snowboarder_influencer_videos + professional_snowboarder_videos:
                        assert "url" in video
                        assert "description" in video
                        assert "stats" in video
                        assert all(key in video["stats"] for key in ["views", "likes", "shares", "comments"])

                except Exception as e:
                    logger.error(f"Search endpoint test failed: {str(e)}")
                    logger.error(f"Error type: {type(e)}")
                    logger.error(f"Error args: {e.args}")
                    raise

    except Exception as e:
        logger.error(f"Server test failed: {str(e)}")
        raise

async def main():
    try:
        logger.info("Starting server tests...")
        await test_server()
        logger.info("\nServer tests completed successfully!")
    except Exception as e:
        logger.error(f"\nServer tests failed: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_health_endpoint(mcp_session):
    """Test the health status endpoint"""
    response = await mcp_session.read_resource("status://health")
    health_json = json.loads(response.contents[0].text)
    health_data = json.loads(health_json[0])
    mime_type = health_json[1]
    
    assert mime_type == "application/json"
    assert health_data["status"] == "running"
    assert health_data["api_initialized"] is True
    assert "service" in health_data
    assert health_data["service"]["name"] == "TikTok MCP Service"

@pytest.mark.asyncio
async def test_single_hashtag_search(mcp_session):
    """Test searching with a single hashtag"""
    result = await mcp_session.call_tool(
        "search_videos",
        arguments={"search_terms": ["#python"]}
    )
    data = json.loads(result.content[0].text)
    
    assert "results" in data
    assert "#python" in data["results"]
    videos = data["results"]["#python"]
    assert len(videos) > 0
    
    # Test video structure
    video = videos[0]
    assert "id" in video
    assert "description" in video
    assert "author" in video
    assert "stats" in video
    assert "url" in video
    assert "sound" in video
    assert "hashtags" in video

@pytest.mark.asyncio
async def test_multi_word_search(mcp_session):
    """Test searching with multi-word terms"""
    result = await mcp_session.call_tool(
        "search_videos",
        arguments={"search_terms": ["python programming"]}
    )
    data = json.loads(result.content[0].text)
    
    # Check transformations
    assert "transformations" in data
    assert "python programming" in data["transformations"]
    hashtags = data["transformations"]["python programming"]
    assert len(hashtags) == 2
    assert "#python" in hashtags
    assert "#programming" in hashtags
    
    # Check results
    assert "results" in data
    assert "python programming" in data["results"]
    videos = data["results"]["python programming"]
    assert len(videos) > 0

@pytest.mark.asyncio
async def test_mixed_search(mcp_session):
    """Test searching with both hashtags and keywords"""
    result = await mcp_session.call_tool(
        "search_videos",
        arguments={"search_terms": ["#python coding"]}
    )
    data = json.loads(result.content[0].text)
    
    assert "transformations" in data
    assert "#python coding" in data["transformations"]
    assert "results" in data
    assert "#python coding" in data["results"]

@pytest.mark.asyncio
async def test_error_handling(mcp_session):
    """Test error handling for invalid searches"""
    result = await mcp_session.call_tool(
        "search_videos",
        arguments={"search_terms": ["!@#$%^"]}
    )
    data = json.loads(result.content[0].text)
    
    assert "errors" in data
    assert "!@#$%^" in data["errors"]

@pytest.mark.asyncio
async def test_caching(mcp_session):
    """Test that caching is working for repeated searches"""
    # Make two identical searches
    search_term = "#python"
    result1 = await mcp_session.call_tool(
        "search_videos",
        arguments={"search_terms": [search_term]}
    )
    result2 = await mcp_session.call_tool(
        "search_videos",
        arguments={"search_terms": [search_term]}
    )
    
    data1 = json.loads(result1.content[0].text)
    data2 = json.loads(result2.content[0].text)
    
    # Results should be consistent
    assert data1["results"][search_term] == data2["results"][search_term]
    
    # Check logs for cache hits
    assert "logs" in data2
    cache_hits = [log for log in data2["logs"] if "cache hit" in log.lower()]
    assert len(cache_hits) > 0

if __name__ == "__main__":
    asyncio.run(main())