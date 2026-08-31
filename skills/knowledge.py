"""Knowledge & research skills — real-world awareness: reading web pages,
encyclopedia lookups, news, currency rates, safe math, and a persistent
memory of facts (the seed of Phase 6 learning)."""
import ast
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from core.config import BASE_DIR
from skills.base import skill

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
FACTS_FILE = Path(BASE_DIR) / "data" / "facts.json"


def _has_persian(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06FF" for ch in text)


@skill(
    description="Fetch a web page and return its readable text. Use this to READ articles, "
                "documentation, or blogs — then answer questions about their content.",
    parameters={"type": "object",
                "properties": {"url": {"type": "string"}}, "required": ["url"]},
)
def fetch_webpage(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()
    text = re.sub(r"\n{3,}", "\n\n", soup.get_text("\n", strip=True))
    title = soup.title.string.strip() if (soup.title and soup.title.string) else url
    return f"TITLE: {title}\n\n{text[:4000]}"


@skill(
    description="Look up a topic on Wikipedia (auto-detects Persian topics and uses the "
                "Persian Wikipedia). Returns a short summary.",
    parameters={"type": "object",
                "properties": {"topic": {"type": "string"}}, "required": ["topic"]},
)
def wikipedia_summary(topic: str) -> str:
    domain = "fa" if _has_persian(topic) else "en"
    r = requests.get(
        f"https://{domain}.wikipedia.org/api/rest_v1/page/summary/{quote(topic)}",
        headers=HEADERS, timeout=15)
    if r.status_code == 404:
        return f"No Wikipedia article found for '{topic}'."
    r.raise_for_status()
    return r.json().get("extract") or "(empty summary)"


@skill(
    description="Get current news headlines, optionally filtered by topic "
                "(e.g. 'technology', 'chess', 'iran').",
    parameters={"type": "object",
                "properties": {"topic": {"type": "string", "description": "Optional filter"}}},
)
def get_news(topic: str = "") -> str:
    url = ("https://news.google.com/rss/search?q=" + quote(topic)) if topic \
        else "https://news.google.com/rss"
    r = requests.get(url, headers=HEADERS, timeout=15)
    items = ET.fromstring(r.content).findall(".//item")[:10]
    if not items:
        return "No headlines found."
    return "Top headlines:\n" + "\n".join(f"- {i.findtext('title')}" for i in items)


@skill(
    description="Convert an amount between currencies using live exchange rates. "
                "Example: amount=100, from_currency='USD', to_currency='EUR'.",
    parameters={"type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "from_currency": {"type": "string"},
                    "to_currency": {"type": "string"},
                }, "required": ["amount", "from_currency", "to_currency"]},
)
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    base = from_currency.upper().strip()
    target = to_currency.upper().strip()
    r = requests.get(f"https://open.er-api.com/v6/latest/{base}", timeout=15)
    r.raise_for_status()
    rates = r.json().get("rates", {})
    if target not in rates:
        return f"Unknown currency '{target}'."
    return f"{amount:g} {base} = {amount * rates[target]:,.2f} {target}"


_ALLOWED_FUNCS = {n: getattr(math, n) for n in
                  ("sqrt", "sin", "cos", "tan", "log", "log10", "log2", "exp",
                   "factorial", "floor", "ceil", "degrees", "radians")}
_ALLOWED_FUNCS.update({"abs": abs, "round": round, "min": min, "max": max, "pow": pow})
_ALLOWED_NODES = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Call,
                  ast.Name, ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div,
                  ast.FloorDiv, ast.Mod, ast.Pow, ast.USub, ast.UAdd, ast.Tuple, ast.List)


@skill(
    description="Evaluate a math expression safely. Supports + - * / // % ** and functions "
                "sqrt sin cos tan log round abs min max, plus pi and e. ALWAYS use this for "
                "arithmetic instead of computing in your head.",
    parameters={"type": "object",
                "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
)
def calculate(expression: str) -> str:
    try:
        tree = ast.parse(expression, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, _ALLOWED_NODES):
                return f"Forbidden element in expression: {type(node).__name__}"
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCS:
                    return "Unknown or forbidden function call."
        result = eval(compile(tree, "<calc>", "eval"),
                      {"__builtins__": {}},
                      {**_ALLOWED_FUNCS, "pi": math.pi, "e": math.e})
        return f"{expression} = {result}"
    except Exception as exc:
        return f"Could not evaluate: {type(exc).__name__}: {exc}"


# ---------- persistent facts (seed of Phase 6 learning) ----------
def _load_facts() -> dict:
    if not FACTS_FILE.exists():
        return {}
    try:
        return json.loads(FACTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


@skill(
    description="Persistently remember a fact about the user or their preferences — "
                "survives restarts and new sessions. Example: key='favorite_band', "
                "value='Pink Floyd'. Use whenever the user says 'remember that...'.",
    parameters={"type": "object",
                "properties": {"key": {"type": "string"}, "value": {"type": "string"}},
                "required": ["key", "value"]},
)
def remember_fact(key: str, value: str) -> str:
    facts = _load_facts()
    facts[key.strip().lower()] = value.strip()
    FACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    FACTS_FILE.write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
    return f"Remembered: {key} = {value}"


@skill(
    description="Recall previously remembered facts. With key: returns that fact. "
                "Without key: returns everything remembered about the user. "
                "ALWAYS check here before asking the user something they may have told you.",
    parameters={"type": "object",
                "properties": {"key": {"type": "string", "description": "Optional fact key"}}},
)
def recall_fact(key: str = "") -> str:
    facts = _load_facts()
    if not facts:
        return "(no facts remembered yet)"
    if key.strip():
        return facts.get(key.strip().lower(), f"No fact stored for '{key}'.")
    return "\n".join(f"{k}: {v}" for k, v in facts.items())