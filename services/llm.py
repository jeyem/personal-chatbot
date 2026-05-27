import httpx
from huggingface_hub import InferenceClient
from app.models import Message
from app.state import get_config


def build_prompt(context_chunks: list[str], history: list[Message], question: str) -> str:
    context = "\n\n---\n\n".join(context_chunks)
    history_text = "\n".join(f"{m.role.value.capitalize()}: {m.content}" for m in reversed(history))

    return (
        f"You are Ehsan, a software engineer. Answer as yourself in first person.\n"
        f"Rules:\n"
        f"- Keep answers short, 2-4 sentences max unless asked for more detail\n"
        f"- Answer only what was asked\n"
        f"- Use plain text, no markdown, no bullet points, no headers\n"
        f"- If the context contains partial information, use it and be honest about uncertainty\n"
        f"- Never say you don't know if the context has anything relevant at all\n"
        f"- Sound natural and human, like a real conversation\n\n"
        f"--- CONTEXT ---\n"
        f"{context}\n\n"
        f"--- CONVERSATION ---\n"
        f"{history_text}\n\n"
        f"User: {question}\n"
        f"Ehsan:"
    )


async def _ask_ollama(prompt: str) -> str:
    cfg = get_config()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{cfg.LLM.base_url}/api/generate",  # pyright: ignore[reportOptionalMemberAccess]
            json={
                "model": cfg.LLM.model,
                "prompt": prompt,
                "stream": False,
                "keep_alive": -1,
            },
            timeout=cfg.LLM.timeout,
        )
    return response.json()["response"].strip()


async def _ask_huggingface(prompt: str) -> str:
    cfg    = get_config()
    client = InferenceClient(api_key=cfg.LLM.api_token)
    result = client.chat.completions.create(
        model    = cfg.LLM.model,
        messages = [{"role": "user", "content": prompt}],
        max_tokens = cfg.LLM.max_new_tokens,
    )
    if result.choices[0].message.content is not None:
        return result.choices[0].message.content.strip()
    return ""


_PROVIDERS = {
    "ollama": _ask_ollama,
    "huggingface": _ask_huggingface,
}


async def ask(context_chunks: list[str], history: list[Message], question: str) -> str:
    cfg = get_config()
    if not cfg.LLM or not cfg.LLM.provider:
        raise ValueError("LLM configuration is missing or incomplete. Cannot call any provider.")

    provider = cfg.LLM.provider
    handler = _PROVIDERS.get(provider)
    if handler is None:
        raise ValueError(f"Unknown LLM provider '{provider}'. choices: {list(_PROVIDERS)}")

    prompt = build_prompt(context_chunks, history, question)
    return await handler(prompt)
