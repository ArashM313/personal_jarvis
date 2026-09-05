"""Finds currently-free OpenRouter models that support tool calling AND
tolerate our no-reasoning flags. Reasoning-mandatory models are auto-skipped."""
import requests
from openai import OpenAI
from core.config import Config

TOP_N_TO_TEST = 8

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

free.sort(key=lambda x: -x[1])
candidates = [mid for mid, _ in free[:TOP_N_TO_TEST]]
print(f"{len(free)} free models support tools. Testing top {len(candidates)}...\n")

client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "Returns the current local time",
        "parameters": {"type": "object", "properties": {}},
    },
}]

flags = Config.LLM_EXTRA_BODY or None
working = []
for model in candidates:
    print(f"=== {model} ===")
    try:
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say hello in Persian (one short sentence)."}],
            extra_body=flags,
        )
        print("  chat  ✅ (accepts our no-reasoning flags)")
    except Exception as e:
        print(f"  chat  ❌ {str(e)[:90]}")
        continue
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Use the get_current_time tool please."}],
            tools=TOOLS,
            extra_body=flags,
        )
        tc = r.choices[0].message.tool_calls
        if tc:
            print(f"  tools ✅ ({tc[0].function.name})")
            working.append(model)
        else:
            print("  tools ⚠️ no tool call — skip")
    except Exception as e:
        print(f"  tools ❌ {str(e)[:90]}")

print("\n═══════ Paste into .env ═══════")
if working:
    print("MODEL_CHAIN=" + ",".join(working))
else:
    print("(none found today — rerun later, or add a cheap paid non-reasoning model)")