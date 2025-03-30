from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
import json
import logging
from typing import NamedTuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_health():
    """Test the health check endpoint"""
    # Create server parameters
    server_params = StdioServerParameters(
        command="python",
        args=["tiktok_mcp_service/main.py"],
    )
    
    logger.info("Testing health endpoint...")
    async with stdio_client(server_params) as (read, write):
        logger.info("Created stdio client")
        async with ClientSession(read, write) as session:
            logger.info("Created client session")
            # Initialize connection
            await session.initialize()
            logger.info("Initialized session")
            
            # Read health status
            logger.info("Reading health status...")
            response = await session.read_resource("status://health")
            logger.info(f"Raw response: {response}")
            
            # Extract content from response
            if hasattr(response, 'contents') and response.contents:
                content = response.contents[0]
                if hasattr(content, 'text'):
                    status = json.loads(content.text)
                    logger.info("\nHealth Status:")
                    print(json.dumps(status, indent=2))
                else:
                    logger.error("Content has no text attribute")
            else:
                logger.error("No contents in response")

if __name__ == "__main__":
    asyncio.run(test_health()) 