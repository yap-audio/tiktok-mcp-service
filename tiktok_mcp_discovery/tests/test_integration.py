import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

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

if __name__ == "__main__":
    asyncio.run(main()) 