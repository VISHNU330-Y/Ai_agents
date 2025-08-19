from google.adk.agents import Agent
import requests

# Search Wikipedia for general knowledge
def search_wikipedia(query: str) -> str:
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}"
    response = requests.get(url)

    if response.status_code != 200:
        return None

    data = response.json()
    title = data.get("title", "No title")
    description = data.get("description", "No description")
    extract = data.get("extract", "No summary available")
    link = data.get("content_urls", {}).get("desktop", {}).get("page", "")

    result = f"📘 {title}\n_{description}_\n\n{extract}"
    if link:
        result += f"\n🔗 Read more: {link}"

    return result

# Fallback: DuckDuckGo Instant Answer API
def search_duckduckgo(query: str) -> str:
    url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
    response = requests.get(url)

    if response.status_code != 200:
        return f"❌ No information found for '{query}'."

    data = response.json()
    abstract = data.get("AbstractText", "")
    heading = data.get("Heading", "")
    link = data.get("AbstractURL", "")

    if not abstract:
        return f"❌ No clear information found for '{query}'. Try rephrasing."

    result = f"📗 {heading}\n\n{abstract}"
    if link:
        result += f"\n🔗 Read more: {link}"

    return result

# Tool function for the agent
def knowledge_tool(query: str) -> str:
    result = search_wikipedia(query)
    if result:
        return result
    return search_duckduckgo(query)

# Define the KnowledgeAgent
knowledge_agent = Agent(
    name="KnowledgeAgent",
    model="gemini-2.5-flash",
    description="General knowledge and information assistant using Wikipedia + DuckDuckGo fallback.",
    instruction="You are a knowledgeable assistant. Always use knowledge_tool to answer queries.",
    tools=[knowledge_tool]
)

# Optional: expose root agent
root_agent = knowledge_agent
