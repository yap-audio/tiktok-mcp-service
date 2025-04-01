import pytest
import asyncio
import os
from dotenv import load_dotenv
import logging
import pytest_asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def pytest_collection_modifyitems(items):
    """Mark tests based on their type."""
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)

@pytest.fixture(scope="session", autouse=True)
def check_env_vars(request):
    """Check that required environment variables are set for integration tests."""
    # Only check env vars for integration tests
    if request.node.get_closest_marker("integration"):
        required_vars = ["TIKTOK_SESSION_ID"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            pytest.skip(f"Missing required environment variables for integration tests: {', '.join(missing_vars)}")

@pytest_asyncio.fixture
async def event_loop():
    """Create an instance of the default event loop for each test case.
    
    Using function scope by default as recommended by pytest-asyncio.
    This ensures each test gets a fresh event loop.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # Close all tasks
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
    # Wait for tasks to cancel
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    # Close the loop
    await loop.shutdown_asyncgens()
    loop.close() 