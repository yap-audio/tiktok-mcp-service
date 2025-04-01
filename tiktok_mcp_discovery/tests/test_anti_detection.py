"""Tests for anti-bot detection configuration."""

import pytest
from unittest.mock import patch

from tiktok_mcp_discovery.anti_detection import AntiDetectionConfig, NYC_LOCATIONS

def test_init():
    """Test initialization of AntiDetectionConfig."""
    config = AntiDetectionConfig()
    assert config.locations == NYC_LOCATIONS
    assert len(config.browsers) == 3  # chromium, firefox, webkit
    assert config.last_browser_index is None

def test_get_next_location_initial():
    """Test getting first location."""
    config = AntiDetectionConfig()
    with patch('random.choice') as mock_choice:
        mock_choice.return_value = NYC_LOCATIONS[0]
        location = config.get_next_location()
        assert location == NYC_LOCATIONS[0]
        mock_choice.assert_called_once_with(NYC_LOCATIONS)

def test_get_next_location_movement():
    """Test realistic location movement."""
    config = AntiDetectionConfig()
    current_location = NYC_LOCATIONS[1]  # Union Square
    
    # Test staying at current location
    with patch('random.choices') as mock_choices:
        mock_choices.return_value = [1]  # Stay at index 1
        next_location = config.get_next_location(current_location)
        assert next_location == NYC_LOCATIONS[1]
    
    # Test moving north
    with patch('random.choices') as mock_choices:
        mock_choices.return_value = [2]  # Move to Bryant Park
        next_location = config.get_next_location(current_location)
        assert next_location == NYC_LOCATIONS[2]
    
    # Test moving south
    with patch('random.choices') as mock_choices:
        mock_choices.return_value = [0]  # Move to Wall & Broad
        next_location = config.get_next_location(current_location)
        assert next_location == NYC_LOCATIONS[0]

def test_get_next_location_edge():
    """Test movement at edge locations."""
    config = AntiDetectionConfig()
    
    # Test at southernmost location
    south = NYC_LOCATIONS[0]
    with patch('random.choices') as mock_choices:
        mock_choices.return_value = [1]  # Can only move north or stay
        next_location = config.get_next_location(south)
        assert next_location in [NYC_LOCATIONS[0], NYC_LOCATIONS[1]]
    
    # Test at northernmost location
    north = NYC_LOCATIONS[-1]
    with patch('random.choices') as mock_choices:
        mock_choices.return_value = [2]  # Can only move south or stay
        next_location = config.get_next_location(north)
        assert next_location in [NYC_LOCATIONS[-1], NYC_LOCATIONS[-2]]

def test_get_browser_config_rotation():
    """Test browser rotation logic."""
    config = AntiDetectionConfig()
    
    # First browser should be random
    with patch('random.randrange', return_value=0) as mock_random:
        first_browser = config.get_browser_config()
        assert first_browser["browser"] == "chromium"
        mock_random.assert_called_once_with(3)
    
    # Should rotate through browsers
    second_browser = config.get_browser_config()
    assert second_browser["browser"] == "firefox"
    
    third_browser = config.get_browser_config()
    assert third_browser["browser"] == "webkit"
    
    # Should wrap around
    fourth_browser = config.get_browser_config()
    assert fourth_browser["browser"] == "chromium"

def test_get_context_options():
    """Test generation of Playwright context options."""
    config = AntiDetectionConfig()
    browser_config = {
        "browser": "chromium",
        "viewport": {"width": 1280, "height": 720},
        "user_agent": "test-user-agent"
    }
    location = {
        "name": "Test Location",
        "latitude": 40.7075,
        "longitude": -74.0021,
        "accuracy": 20
    }
    
    options = config.get_context_options(browser_config, location)
    
    assert options["viewport"] == browser_config["viewport"]
    assert options["user_agent"] == browser_config["user_agent"]
    assert options["geolocation"]["latitude"] == location["latitude"]
    assert options["geolocation"]["longitude"] == location["longitude"]
    assert options["locale"] == "en-US"
    assert options["timezone_id"] == "America/New_York"
    assert "geolocation" in options["permissions"] 