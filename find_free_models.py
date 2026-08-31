"""Finds CURRENTLY-free OpenRouter models that support tool calling,
tests them, and prints a ready-to-paste MODEL_CHAIN line for .env."""
import requests
from openai import OpenAI
from core.config import Config

TOP_N_TO_TEST = 6

print("Fetching model list from OpenRouter...")
data = requests.get("https://openrouter.ai/api/v1/models", timeout=30).json()["data"]

free = []
for m in data:
    p = m.get("pricing", {})
    try:
        is_free = float(p.get("prompt", "1")) == 0 and float(p.get("completion", "1")) == 0
    except (TypeError, ValueError):
        is_free = False
    if is_free and "tools" in m.get("supported_parameters", []):
        free.append((m["id"], m.get("context_length", 0)))

free.sort(key=lambda x: -x[1])  # biggest context first
candidates = [mid for mid, _ in free[:TOP_N_TO_TEST]]
print(f"{len(free)} free models support tools. Testing the top {len(candidates)}...\n")

client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "Returns the current local time",
        "parameters": {"type": "object", "properties": {}},
    },
}]

working = []
for model in candidates:
    print(f"=== {model} ===")
    try:
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say hello in Persian (one short sentence)."}],
        )
        print("  chat  ✅")
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Use the get_current_time tool please."}],
            tools=TOOLS,
        )
        tc = r.choices[0].message.tool_calls
        if tc:
            print(f"  tools ✅ ({tc[0].function.name})")
            working.append(model)
        else:
            print("  tools ⚠️ no tool call — skip")
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {str(e)[:100]}")

print("\n═══════ Paste this into .env ═══════")
if working:
    print("MODEL_CHAIN=" + ",".join(working))
else:
    print("(no working free model found today — rerun tomorrow or add a cheap paid fallback)")