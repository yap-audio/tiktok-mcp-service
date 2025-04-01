import pytest
import asyncio
import logging
from pathlib import Path
from mcp import ClientSession, StdioServerParameters, stdio_client
from tiktok_mcp_discovery.tiktok_client import TikTokClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def tiktok_client():
    """Create a TikTokClient instance for testing."""
    client = TikTokClient()
    try:
        await client._init_api()
        yield client
    finally:
        await client.close()

@pytest.fixture(scope="session")
async def mcp_session():
    """Create an MCP client session for testing."""
    # Get absolute path to main.py
    main_py = str(Path(__file__).parent.parent / "main.py")
    logger.info(f"Using server script at: {main_py}")

    # Create server parameters
    server_params = StdioServerParameters(
        command="python",
        args=[main_py],
        env=None  # Use current environment
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize with longer timeout
            try:
                await asyncio.wait_for(session.initialize(), timeout=120.0)
                yield session
            except asyncio.TimeoutError:
                logger.error("Server initialization timed out after 120 seconds")
                raise
            except Exception as e:
                logger.error(f"Server initialization failed: {str(e)}")
                raise 