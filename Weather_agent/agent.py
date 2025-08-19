import requests, os
from dotenv import load_dotenv
from google.adk.agents import Agent

load_dotenv()
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

def get_weather(query: str) -> str:
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={query}"
    response = requests.get(url)

    if response.status_code != 200:
        return f"Sorry, I could not fetch weather for {query}."

    data = response.json()
    location = data["location"]["name"]
    region = data["location"]["region"]
    country = data["location"]["country"]
    temp_c = data["current"]["temp_c"]
    condition = data["current"]["condition"]["text"]
    humidity = data["current"]["humidity"]
    wind = data["current"]["wind_kph"]

    return f"Weather in {location}, {region}, {country}: {condition}, {temp_c}°C, Humidity: {humidity}%, Wind: {wind} kph."

weather_agent = Agent(
    name="WeatherAgent",
    model="gemini-2.5-flash",
    description="Get real-time weather info for any place in India using WeatherAPI.com",
    instruction="Always use get_weather to answer weather queries.",
    tools=[get_weather]
)

root_agent = weather_agent
