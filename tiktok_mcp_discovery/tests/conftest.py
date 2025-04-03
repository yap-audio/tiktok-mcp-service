"""Pytest configuration and fixtures."""

import pytest
import asyncio
import os
from dotenv import load_dotenv
import logging
import pytest_asyncio
from typing import Generator

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

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def mock_session():
    """Mock TikTok session for testing."""
    class MockSession:
        def __init__(self):
            self.api = None
            self.initialized = False
            self.rotation_count = 0
            
        async def initialize(self):
            self.initialized = True
            self.api = "mock_api"
            
        async def close(self):
            self.initialized = False
            self.api = None
            
        async def should_rotate(self):
            return self.rotation_count >= 3
            
    return MockSession()

@pytest.fixture
async def mock_client(mock_session):
    """Mock TikTok client for testing."""
    class MockClient:
        def __init__(self):
            self.api = None
            self.session = mock_session
            
        async def _init_api(self):
            self.api = "mock_api"
            
        async def close(self):
            self.api = None
            
        async def search_videos(self, term, count=30):
            return {
                "results": {
                    term: [{"id": "123", "desc": "Test video"}]
                }
            }
            
    return MockClient() 