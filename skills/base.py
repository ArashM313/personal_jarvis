"""Skill registry.
To add a new capability:
  1. Create a file in /skills and decorate functions with @skill
  2. Import that module in skills/__init__.py
That's it — the model discovers new tools automatically."""

SKILLS: dict = {}


def skill(description: str = "", parameters: dict | None = None,
          dangerous: bool = False, name: str | None = None):
    """Decorator that registers a function as a JARVIS skill."""
    def decorator(fn):
        skill_name = name or fn.__name__
        SKILLS[skill_name] = {
            "function": fn,
            "description": description or (fn.__doc__ or "").strip(),
            "parameters": parameters or {"type": "object", "properties": {}},
            "dangerous": dangerous,  # if True, user must confirm before execution
        }
        return fn
    return decorator


def get_tools() -> list:
    """Build tool declarations in OpenAI function-calling format
    (compatible with Qwen / DashScope / SiliconFlow / OpenRouter / Ollama)."""
    return [
        {
            "type": "function",
            "function": {
                "name": skill_name,
                "description": info["description"],
                "parameters": info["parameters"],
            },
        }
        for skill_name, info in SKILLS.items()
    ]


def is_dangerous(skill_name: str) -> bool:
    return SKILLS.get(skill_name, {}).get("dangerous", False)


def execute_skill(skill_name: str, args: dict) -> str:
    """Run a skill and ALWAYS return a string (the model reads the result)."""
    if skill_name not in SKILLS:
        return f"Error: unknown skill '{skill_name}'"
    try:
        result = SKILLS[skill_name]["function"](**args)
        return str(result)
    except Exception as exc:
        return f"Error in {skill_name}: {exc}"