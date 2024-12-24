from flask import Flask, render_template, jsonify
from flight_service import FlightService
from cache_service import cache
import asyncio

app = Flask(__name__)
flight_service = FlightService()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/flight-stats')
async def flight_stats():
    stats = await flight_service.get_flight_stats()
    return jsonify(stats)

@app.route('/api/cache/clear')
def clear_cache():
    """Admin endpoint to clear the cache"""
    cache.clear()
    return jsonify({'status': 'success', 'message': 'Cache cleared'})

@app.route('/api/cache/status')
def cache_status():
    """Get cache status"""
    cached_data = cache.get(flight_service.CACHE_KEY)
    if cached_data and 'cached_at' in cached_data:
        return jsonify({
            'has_cache': True,
            'cached_at': cached_data['cached_at']
        })
    return jsonify({
        'has_cache': False
    })

if __name__ == '__main__':
    app.run(debug=True) 