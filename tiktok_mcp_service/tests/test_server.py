import asyncio
import json
import logging
import os
from pathlib import Path

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
                    await asyncio.wait_for(session.initialize(), timeout=30.0)
                    logger.info("Server connection initialized successfully")
                except asyncio.TimeoutError:
                    logger.error("Server initialization timed out after 30 seconds")
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
                    result = await session.call_tool("search_videos", arguments={"search_terms": ["python", "coding"]})
                    # Parse the JSON response from the content field
                    response_text = result.content[0].text
                    response_data = json.loads(response_text)
                    
                    # Check python results
                    python_videos = response_data.get("python", [])
                    logger.info(f"Found {len(python_videos)} videos for term 'python'")
                    assert len(python_videos) > 0, "No videos found for 'python'"
                    
                    # Check coding results
                    coding_videos = response_data.get("coding", [])
                    logger.info(f"Found {len(coding_videos)} videos for term 'coding'")
                    assert len(coding_videos) > 0, "No videos found for 'coding'"

                    # Verify video structure
                    for video in python_videos + coding_videos:
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

if __name__ == "__main__":
    asyncio.run(main())