import httpx
from typing import Optional, Dict, List
from datetime import datetime
from collections import defaultdict, deque
import re
import config
from urllib.parse import urlencode
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

class APIClient:
    def __init__(self, actor: str, limit: int = 100):
        self.base_url = config.BASE_URL
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

class FlightService:
    def __init__(self):
        self.api_client = APIClient(actor="did:plc:62cuohm6c6nefpnw4uujepty")
        self.takeoffs = defaultdict(int)
        self.landings = defaultdict(int)
        self.geolocator = Nominatim(user_agent="elon_tracker")
        self.location_cache = {}
        self.all_flights = []  # Store all flights with their coordinates
    
    def parse_location(self, text: str) -> tuple:
        """Extract location and type from flight text"""
        if "Landed in " in text:
            match = re.search(r"Landed in (.*?)\.", text)
            if match:
                return match.group(1), "landing"
        elif "Took off from " in text:
            match = re.search(r"Took off from (.*?)\.", text)
            if match:
                return match.group(1), "takeoff"
        return None, None
    
    def get_coordinates(self, location: str) -> tuple:
        """Get coordinates for a location with caching"""
        if location in self.location_cache:
            return self.location_cache[location]
            
        try:
            geocode_result = self.geolocator.geocode(location)
            if geocode_result:
                coords = (geocode_result.longitude, geocode_result.latitude)
                self.location_cache[location] = coords
                return coords
        except GeocoderTimedOut:
            print(f"Geocoding timed out for {location}")
        return None
    
    def process_flight(self, text: str, timestamp: str):
        """Process flight text and store flight information"""
        location, flight_type = self.parse_location(text)
        if location:
            coords = self.get_coordinates(location)
            if coords:
                if flight_type == "takeoff":
                    self.takeoffs[location] += 1
                    self.all_flights.append({
                        'type': 'takeoff',
                        'location': location,
                        'coordinates': coords,
                        'timestamp': timestamp,
                        'text': text
                    })
                elif flight_type == "landing":
                    self.landings[location] += 1
                    self.all_flights.append({
                        'type': 'landing',
                        'location': location,
                        'coordinates': coords,
                        'timestamp': timestamp,
                        'text': text
                    })

    def pair_flights(self):
        """Pair takeoffs with landings based on chronological order"""
        flight_paths = []
        takeoffs = []
        
        for flight in sorted(self.all_flights, key=lambda x: x['timestamp']):
            if flight['type'] == 'takeoff':
                takeoffs.append(flight)
            elif flight['type'] == 'landing' and takeoffs:
                # Pair with the most recent takeoff
                takeoff = takeoffs.pop()
                flight_paths.append({
                    'takeoff': {
                        'location': takeoff['location'],
                        'coordinates': takeoff['coordinates'],
                        'timestamp': takeoff['timestamp'],
                        'text': takeoff['text']
                    },
                    'landing': {
                        'location': flight['location'],
                        'coordinates': flight['coordinates'],
                        'timestamp': flight['timestamp'],
                        'text': flight['text']
                    }
                })
        
        return flight_paths

    async def get_flight_stats(self) -> Dict:
        # Reset counters and flights
        self.takeoffs.clear()
        self.landings.clear()
        self.all_flights = []
        
        try:
            response_data = await self.api_client.get_request(endpoint="/")
            
            flights = []
            if 'feed' in response_data:
                # Process posts in chronological order
                posts = sorted(
                    response_data['feed'],
                    key=lambda x: x['post']['record']['createdAt']
                )
                
                for post in posts:
                    post_data = post['post']
                    text = post_data['record'].get('text', '')
                    
                    if text.startswith(('Landed', 'Took')):
                        created_at = datetime.fromisoformat(
                            post_data['record']['createdAt'].replace('Z', '+00:00')
                        )
                        self.process_flight(text, created_at.isoformat())
                        flights.append({
                            'timestamp': created_at.isoformat(),
                            'text': text
                        })
            
            # Add coordinates to the response
            locations_with_coords = {}
            for location in set(list(self.takeoffs.keys()) + list(self.landings.keys())):
                coords = self.get_coordinates(location)
                if coords:
                    locations_with_coords[location] = {
                        'takeoffs': self.takeoffs[location],
                        'landings': self.landings[location],
                        'coordinates': coords
                    }
            
            # Get paired flights
            flight_paths = self.pair_flights()

            return {
                'locations': locations_with_coords,
                'recent_flights': flights,
                'flight_paths': flight_paths,
                'all_flights': self.all_flights  # Include all individual flights
            }
            
        except Exception as e:
            print(f"Error fetching flight stats: {e}")
            return {'error': str(e)} 