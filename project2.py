from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent 
import httpx
from zoneinfo import ZoneInfo
from datetime import datetime
from pydantic_ai.messages import ModelMessage

load_dotenv()

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 51: "Light drizzle", 61: "Light rain", 63: "Moderate rain",
    71: "Light snow", 80: "Rain showers", 95: "Thunderstorm"
}

class WeatherReport(BaseModel):
    city: str
    temperature_c: float 
    condition: str
    recommendation: str

system_prompt = """You are a helpful weather assistant. Your job is to answer weather-related 
questions for any city the user asks about.

You have access to the following tools:
- get_coordinates: Use this FIRST to convert a city name to latitude, longitude, and timezone.
- get_weather: Use this SECOND to fetch current weather data using the coordinates.
- get_local_time: Use this alongside get_weather to get the current local time at the location.

## How to approach every request

1. Always call get_coordinates first — you cannot call get_weather without lat/lng.
2. Once you have coordinates, call get_weather and get_local_time in the same step.
3. After collecting all data, produce a final structured response.

## Rules

- Never guess or assume coordinates — always use the get_coordinates tool.
- Never fabricate weather data — only report what the tool returns.
- If the user gives an ambiguous city name (e.g. "Springfield"), ask which country 
  or state they mean before calling any tool.
- If a tool returns an error, tell the user clearly and do not make up a fallback.
- If the user mentions a region instead of a city (e.g. "Uttar Pradesh"), 
  pick the most well-known city in that region (e.g. Lucknow) and proceed. 
  Do not ask clarifying questions — always produce a WeatherReport.
- Never use placeholder text like "weather condition" or "local time" as field values. 
  Always populate every field using the actual data returned by the tools.
- The local_time field must be taken exactly from the get_local_time tool result. 
  Never modify, infer, or fabricate the date or time.

## Response style

- Be concise and friendly.
- Always include: city name, local time, temperature, weather condition, 
  and a one-line practical recommendation (e.g. "Bring a jacket" or "Great day 
  for a walk").
- Do not dump raw data at the user — summarize it naturally."""

agent = Agent(
    model='groq:llama-3.3-70b-versatile',
    output_type=WeatherReport,
    instructions=system_prompt
)

router = Agent(
    model='groq:llama-3.3-70b-versatile',
    output_type=bool,
    instructions="You are a classifier. Your only job is to determine if the user's message "
        "is asking about weather. Respond with true if it is weather-related, "
        "false if it is not. Do not explain. Do not add any other text. "
        "Only output true or false.",
    retries=3
)

@agent.tool_plain
async def get_coordinates(city: str) -> dict:
    """Convert a city name to latitude and longitude using the Open-Meteo Geocoding API."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city, "count": 1, "language": "en", "format": "json"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if not data.get("results"):
            return {"error": f"Could not find coordinates for '{city}'."}
        result = data["results"][0]
        return {
            'city': result['name'],
            'country': result.get('country', ''),
            'latitude': result['latitude'],
            'longitude': result['longitude'],
            'timezone': result.get('timezone', '')
        }
    
@agent.tool_plain 
async def get_weather(latitude: float, longitude: float) -> dict:
    """Fetch current weather for a given latitude and longitude using the Open-Meteo Weather API."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'current': [
            'temperature_2m',
            'relative_humidity_2m',
            'apparent_temperature',
            'weathercode',
            'wind_speed_10m'
        ],
        'wind_speed_unit': 'mph',
        'temperature_unit': 'celsius'
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        current = data['current']
        return {
    'temperature_c': current['temperature_2m'],
    'feels_like_c': current['apparent_temperature'],
    'humidity_percent': current['relative_humidity_2m'],
    'wind_speed_mph': current['wind_speed_10m'],
    'condition': WEATHER_CODES.get(current['weathercode'], f"Code {current['weathercode']}")  # ← changed
}

@agent.tool_plain
def get_local_time(timezone: str) -> dict:
    """Get the current local time for a given IANA timezone string (e.g. 'America/New_York')."""
    try:
        tz = ZoneInfo(timezone)
        local_time = datetime.now(tz)
        return {
            'timezone': timezone,
            'local_time': local_time.strftime('%Y-%m-%d %H:%M:%S'),
            'utc_offset': local_time.strftime('%z')
        }
    except Exception:
        return {'error': f'Unknown or invalid timezone: "{timezone}".'}
    
History: list[ModelMessage] = []

def run_query(user_string: str):
    try:
        is_weather = router.run_sync(user_string).output
        if not is_weather:
            print("Sorry, I can only answer weather-related questions.")
            return
        
        data = agent.run_sync(user_string, message_history=History)
        History.extend(data.new_messages())
        print('City:', data.output.city)
        print('Temperature (°C):', data.output.temperature_c)
        print('Weather Condition:', data.output.condition)
        print('Recommendation:', data.output.recommendation)
    except Exception as e:
        print(f"Something went wrong: {e}")

if __name__ == '__main__':
    while True:
        user_string = str(input('Enter your query ("exit" for exit): '))
        if user_string.lower() == 'exit':
            break
        run_query(user_string)