import webbrowser
from urllib.parse import quote

import requests

from skills.base import skill


@skill(
    description="Open a URL in the default browser.",
    parameters={
        "type": "object",
        "properties": {"url": {"type": "string", "description": "e.g. https://github.com"}},
        "required": ["url"],
    },
)
def open_website(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened in browser: {url}"


@skill(
    description="Search Google in a new browser tab.",
    parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
)
def search_web(query: str) -> str:
    webbrowser.open(f"https://www.google.com/search?q={quote(query)}")
    return f"Searching Google for: {query}"


@skill(
    description="Search YouTube in a new browser tab.",
    parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
)
def search_youtube(query: str) -> str:
    webbrowser.open(f"https://www.youtube.com/results?search_query={quote(query)}")
    return f"Searching YouTube for: {query}"


@skill(
    description="Get current weather for a city.",
    parameters={"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
)
def get_weather(city: str) -> str:
    try:
        r = requests.get(f"https://wttr.in/{quote(city)}?format=3", timeout=10)
        r.raise_for_status()
        return r.text.strip()
    except Exception as exc:
        return f"Weather request failed: {exc}"