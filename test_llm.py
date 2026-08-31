"""Test every model in MODEL_CHAIN: plain chat + function calling."""
from openai import OpenAI
from core.config import Config

client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)

TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "Returns the current local time",
        "parameters": {"type": "object", "properties": {}},
    },
}]

for model in Config.MODEL_CHAIN:
    print(f"\n=== {model} ===")
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say hello in Persian (one short sentence)."}],
        )
        print("  chat  ✅")
    except Exception as e:
        print(f"  chat  ❌  {type(e).__name__}: {str(e)[:120]}")
        continue
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Use the get_current_time tool please."}],
            tools=TOOLS,
        )
        tc = r.choices[0].message.tool_calls
        print(f"  tools {'✅ ' + tc[0].function.name if tc else '⚠️  no tool call — weak for JARVIS'}")
    except Exception as e:
        print(f"  tools ❌  {type(e).__name__}: {str(e)[:120]}")