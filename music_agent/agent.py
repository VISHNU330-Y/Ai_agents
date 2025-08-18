from google.adk.agents import Agent
import requests
import base64
import os
from dotenv import load_dotenv

# Load credentials from .env file
load_dotenv()
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

if not client_id or not client_secret:
    raise ValueError("Missing Spotify credentials. Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env file.")

# Get Spotify access token
def get_spotify_token(client_id: str, client_secret: str) -> str:
    auth_str = f"{client_id}:{client_secret}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": f"Basic {b64_auth_str}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}

    response = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
    response.raise_for_status()
    token = response.json().get("access_token")
    return token

# Search Spotify for tracks or artists
def search_spotify(query: str, token: str, type_: str = "track") -> str:
    url = f"https://api.spotify.com/v1/search?q={query}&type={type_}&limit=3&market=IN"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    items = response.json().get(f"{type_}s", {}).get("items", [])

    if not items:
        return f"No {type_}s found for '{query}'."

    results = []
    for item in items:
        if type_ == "track":
            name = item["name"]
            artist = item["artists"][0]["name"]
            link = item["external_urls"]["spotify"]
            results.append(f"🎵 {name} by {artist} → [Listen]({link})")
        elif type_ == "artist":
            name = item["name"]
            link = item["external_urls"]["spotify"]
            results.append(f"🎤 {name} → [View Artist]({link})")

    return "\n".join(results)

# Tool function for the agent
def music_tool(query: str) -> str:
    token = get_spotify_token(client_id, client_secret)

    if "recommend" in query.lower() or "song" in query.lower() or "track" in query.lower():
        return search_spotify(query, token, type_="track")
    elif "artist" in query.lower():
        return search_spotify(query, token, type_="artist")
    else:
        return "Try asking for a song or artist recommendation!"

# Define the MusicAgent
music_agent = Agent(
    name="MusicAgent",
    model="gemini-2.5-flash",
    description="Real-time music assistant using Spotify API.",
    instruction="You are a music expert. Always use music_tool to answer queries.",
    tools=[music_tool]
)

# Optional: expose root agent
root_agent = music_agent