"""Anti-bot detection configuration and rotation logic."""

import random
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# NYC locations for realistic movement patterns
NYC_LOCATIONS = [
    {
        "name": "Wall & Broad",
        "latitude": 40.7075,
        "longitude": -74.0021,
        "accuracy": 20
    },
    {
        "name": "Union Square",
        "latitude": 40.7359,
        "longitude": -73.9911,
        "accuracy": 20
    },
    {
        "name": "Bryant Park",
        "latitude": 40.7536,
        "longitude": -73.9832,
        "accuracy": 20
    },
    {
        "name": "Central Park",
        "latitude": 40.7829,
        "longitude": -73.9654,
        "accuracy": 20
    }
]

# Browser configurations for rotation
BROWSER_CONFIGS = [
    {
        "browser": "chromium",
        "viewport": {"width": 1280, "height": 720},
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    },
    {
        "browser": "firefox",
        "viewport": {"width": 1366, "height": 768},
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0"
    },
    {
        "browser": "webkit",
        "viewport": {"width": 1440, "height": 900},
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15"
    }
]

class AntiDetectionConfig:
    """Manages browser and location configurations for anti-bot detection."""
    
    def __init__(self):
        """Initialize with default configurations."""
        self.locations = NYC_LOCATIONS
        self.browsers = BROWSER_CONFIGS
        self.last_browser_index: Optional[int] = None
    
    def get_next_location(self, current_location: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get next location based on current location for realistic movement.
        
        Args:
            current_location: The current location being used, if any
            
        Returns:
            Dict containing the next location to use
        """
        if not current_location:
            return random.choice(self.locations)
            
        # Find current location index
        try:
            current_index = self.locations.index(current_location)
        except ValueError:
            logger.warning("Current location not found in locations list, choosing random location")
            return random.choice(self.locations)
            
        # Move to adjacent location (or stay) for realism
        possible_moves = []
        
        # Can stay at current location (30% chance)
        possible_moves.append((current_index, 0.3))
        
        # Can move to adjacent locations (35% chance each)
        if current_index > 0:
            possible_moves.append((current_index - 1, 0.35))  # Move south
        if current_index < len(self.locations) - 1:
            possible_moves.append((current_index + 1, 0.35))  # Move north
            
        # Normalize probabilities if at edge location
        total_prob = sum(prob for _, prob in possible_moves)
        possible_moves = [(idx, prob/total_prob) for idx, prob in possible_moves]
        
        # Choose next location based on probabilities
        next_index = random.choices(
            [idx for idx, _ in possible_moves],
            weights=[prob for _, prob in possible_moves]
        )[0]
        
        logger.info(f"Moving from {current_location['name']} to {self.locations[next_index]['name']}")
        return self.locations[next_index]
    
    def get_browser_config(self) -> Dict[str, Any]:
        """Get a browser configuration, rotating through options.
        
        Returns:
            Dict containing browser configuration
        """
        if self.last_browser_index is None:
            # First time, choose random browser
            self.last_browser_index = random.randrange(len(self.browsers))
        else:
            # Rotate to next browser
            self.last_browser_index = (self.last_browser_index + 1) % len(self.browsers)
        
        config = self.browsers[self.last_browser_index]
        logger.info(f"Selected browser: {config['browser']}")
        return config
    
    def get_context_options(self, browser_config: Dict[str, Any], location: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Playwright context options for the given browser and location.
        
        Args:
            browser_config: Browser configuration to use
            location: Location configuration to use
            
        Returns:
            Dict containing Playwright context options
        """
        return {
            "viewport": browser_config["viewport"],
            "user_agent": browser_config["user_agent"],
            "geolocation": {
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "accuracy": location["accuracy"]
            },
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["geolocation"],
            "color_scheme": "light"
        } 