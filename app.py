from flask import Flask, render_template, jsonify
from flight_service import FlightService
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

if __name__ == '__main__':
    app.run(debug=True) 