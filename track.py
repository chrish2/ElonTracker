import httpx
from typing import Optional
from datetime import datetime
from collections import defaultdict
import re
import config
from urllib.parse import urlencode

class APIClient:
    def __init__(self, actor: str, limit: int = 100):
        self.base_url = config.BASE_URL
        
        # Separate query parameters
        self.params = {
            'actor': actor,
            'filter': 'posts_and_author_threads',
            'includePins': 'true',
            'limit': str(limit)
        }
        
        self.headers = {
            'Authorization': f'Bearer {config.BEARER_TOKEN}',
            'Accept': 'application/json'
        }
    
    async def get_request(self, endpoint: str, additional_params: Optional[dict] = None) -> dict:
        """
        Send GET request with bearer token authentication
        
        Args:
            endpoint (str): API endpoint
            additional_params (dict, optional): Additional query parameters
            
        Returns:
            dict: Response data
        """
        # Combine default params with any additional params
        request_params = self.params.copy()
        if additional_params:
            request_params.update(additional_params)
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                headers=self.headers,
                params=request_params
            )
            response.raise_for_status()
            return response.json()

class FlightTracker:
    def __init__(self):
        self.takeoffs = defaultdict(int)
        self.landings = defaultdict(int)
    
    def parse_location(self, text: str) -> str:
        """Extract location from flight text"""
        if "Landed in " in text:
            match = re.search(r"Landed in (.*?)\.", text)
            if match:
                return match.group(1)
        elif "Took off from " in text:
            match = re.search(r"Took off from (.*?)\.", text)
            if match:
                return match.group(1)
        return ""
    
    def add_flight(self, text: str):
        """Process flight text and update counts"""
        location = self.parse_location(text)
        if location:
            if text.startswith("Landed"):
                self.landings[location] += 1
            elif text.startswith("Took"):
                self.takeoffs[location] += 1
    
    def print_stats(self):
        """Print statistics for all locations"""
        print("\n=== Flight Statistics ===")
        
        all_locations = set(list(self.takeoffs.keys()) + list(self.landings.keys()))
        for location in sorted(all_locations):
            print(f"\n{location}:")
            if self.takeoffs[location] > 0:
                print(f"  Takeoffs: {self.takeoffs[location]}")
            if self.landings[location] > 0:
                print(f"  Landings: {self.landings[location]}")

async def main():
    api_client = APIClient(
        actor="did:plc:62cuohm6c6nefpnw4uujepty"
    )
    
    tracker = FlightTracker()
    
    try:
        response_data = await api_client.get_request(
            endpoint="/",
        )
        
        if 'feed' in response_data:
            for post in response_data['feed']:
                post_data = post['post']
                text = post_data['record'].get('text', '')
                
                if text.startswith(('Landed', 'Took')):
                    created_at = datetime.fromisoformat(post_data['record']['createdAt'].replace('Z', '+00:00'))
                    print(f"\n{created_at}: {text}")
                    tracker.add_flight(text)
        
        # Print the statistics after processing all posts
        tracker.print_stats()
        
    except httpx.HTTPError as e:
        print(f"HTTP error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
