"""
Prompts used by the TikTok MCP Service.
These are stored separately to make them easier to edit and maintain.
"""

def get_search_prompt(query: str) -> str:
    """
    Create a prompt for searching TikTok videos.
    Explains the service's capabilities and guides users on how to search effectively.
    """
    return f"""I'll help you find TikTok videos related to: {query}

This service supports two types of searches:

1. Single Hashtag Search
   - Simple searches using one hashtag (e.g., #cooking, #fitness)
   - Direct and focused results
   Example searches:
   - #cooking
   - #workout
   - #dance

2. Multi-word Keyword Search
   - Converts each word into a hashtag
   - Combines and deduplicates results
   Example searches:
   - healthy cooking (searches #healthy AND #cooking)
   - dance workout (searches #dance AND #workout)
   - social media marketing (searches #social, #media, AND #marketing)

For each search, the service will return:

1. Video Information:
   - Video ID and description
   - View count, likes, shares, comments
   - Direct URL to the video
   - Sound/music details used in the video

2. Creator Information:
   - Username and TikTok ID
   - Profile information
   - Engagement metrics

3. Hashtag Details:
   - Associated hashtags and their metrics
   - Hashtag IDs for further exploration

4. Search Metadata:
   - How keywords were transformed into hashtags
   - Which searches were successful/failed
   - Deduplication statistics
   - Cache hit/miss information

The results are structured to help you:
- Analyze video performance and engagement
- Identify influential creators
- Track hashtag popularity
- Understand content trends
- Make data-driven content decisions

How would you like to search? You can:
1. Use a single hashtag (start with #)
2. Enter multiple words to search related hashtags
3. Mix and match (e.g., "#fitness workout" will search both #fitness and #workout)""" 