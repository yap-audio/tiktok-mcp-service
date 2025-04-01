import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import pytest
import json
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="python",
        args=["tiktok_mcp_discovery/main.py"],
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                
                # Test the search prompt
                print("\nTesting search prompt...")
                prompt_result = await session.get_prompt("search_prompt", arguments={"query": "cooking recipes"})
                print("Prompt Response:")
                print(prompt_result)
                
                # Test video search
                search_terms = ["cooking", "recipe"]
                print(f"\nSearching for videos with terms: {search_terms}")
                
                result = await session.call_tool("search_videos", arguments={"search_terms": search_terms})
                
                # Display results
                for term, videos in result.items():
                    print(f"\nResults for '{term}':")
                    print(f"Found {len(videos)} videos")
                    
                    # Show first 3 videos for each term
                    for i, video in enumerate(videos[:3], 1):
                        print(f"\nVideo {i}:")
                        print(f"URL: {video['url']}")
                        print(f"Description: {video['description']}")
                        print(f"Stats: {video['stats']}")
                        print(f"Author: {video['author']['username']} ({video['author']['nickname']})")

    except Exception as e:
        print(f"Error: {str(e)}")

@pytest.mark.asyncio
async def test_search_prompt(mcp_session):
    """Test the search prompt functionality"""
    # Test with a single hashtag
    single_result = await mcp_session.get_prompt(
        "search_prompt",
        arguments={"query": "#cooking"}
    )
    assert "#cooking" in single_result
    assert "Single Hashtag Search" in single_result
    
    # Test with a multi-word query
    multi_result = await mcp_session.get_prompt(
        "search_prompt",
        arguments={"query": "cooking recipes"}
    )
    assert "cooking recipes" in multi_result
    assert "Multi-word Keyword Search" in multi_result
    assert "cooking" in multi_result
    assert "recipes" in multi_result

@pytest.mark.asyncio
async def test_end_to_end_search(mcp_session):
    """Test a complete search flow including prompt and video search"""
    # First get the prompt
    prompt_result = await mcp_session.get_prompt(
        "search_prompt",
        arguments={"query": "cooking recipes"}
    )
    assert prompt_result is not None
    
    # Then perform the search
    search_result = await mcp_session.call_tool(
        "search_videos",
        arguments={"search_terms": ["cooking recipes"]}
    )
    data = json.loads(search_result.content[0].text)
    
    # Verify the complete flow
    assert "results" in data
    assert "cooking recipes" in data["results"]
    assert "transformations" in data
    
    # Check video structure
    videos = data["results"]["cooking recipes"]
    assert len(videos) > 0
    
    video = videos[0]
    assert "url" in video
    assert "description" in video
    assert "stats" in video
    assert "author" in video
    
    # Verify author structure
    author = video["author"]
    assert "username" in author
    assert "id" in author
    
    # Verify stats structure
    stats = video["stats"]
    assert all(key in stats for key in ["views", "likes", "shares", "comments"])

@pytest.mark.asyncio
async def test_prompt_response_structure(mcp_session):
    """Test that the prompt response includes all necessary information"""
    result = await mcp_session.get_prompt(
        "search_prompt",
        arguments={"query": "fitness workout"}
    )
    
    # Check for all major sections
    assert "Video Information:" in result
    assert "Creator Information:" in result
    assert "Hashtag Details:" in result
    assert "Search Metadata:" in result
    
    # Check for specific data points mentioned
    assert "view count" in result.lower()
    assert "likes" in result.lower()
    assert "profile information" in result.lower()
    assert "hashtag metrics" in result.lower()
    assert "cache" in result.lower()

if __name__ == "__main__":
    asyncio.run(main()) 