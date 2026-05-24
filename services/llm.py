import httpx
from app.state import get_config
from app.models import Message


def build_prompt(context_chunks: list[str], history: list[Message], question: str) -> str:
    context      = "\n\n---\n\n".join(context_chunks)
    history_text = "\n".join(
        f"{m.role.value.capitalize()}: {m.content}"
        for m in reversed(history)
    )

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
            f"{cfg.LLM.base_url}/api/generate", # pyright: ignore[reportOptionalMemberAccess]
            json={"model": cfg.LLM.model, "prompt": prompt, "stream": False, "keep_alive": -1},
            timeout=cfg.LLM.timeout,
        )
    return response.json()["response"].strip()


async def _ask_huggingface(prompt: str) -> str:
    cfg = get_config()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{cfg.LLM.base_url}/models/{cfg.LLM.model}",
            headers={"Authorization": f"Bearer {cfg.LLM.api_token}"},
            json={"inputs": prompt, "parameters": {"max_new_tokens": cfg.LLM.max_new_tokens}},
            timeout=cfg.LLM.timeout,
        )
    result = response.json()
    return result[0].get("generated_text", "").replace(prompt, "").strip()


_PROVIDERS = {
    "ollama":       _ask_ollama,
    "huggingface":  _ask_huggingface,
}


async def ask(context_chunks: list[str], history: list[Message], question: str) -> str:
    cfg = get_config()
    if not cfg.LLM or not cfg.LLM.provider:
        raise ValueError("LLM configuration is missing or incomplete. Cannot call any provider.")

    provider = cfg.LLM.provider
    handler  = _PROVIDERS.get(provider)
    if handler is None:
        raise ValueError(f"Unknown LLM provider '{provider}'. choices: {list(_PROVIDERS)}")

    prompt = build_prompt(context_chunks, history, question)
    return await handler(prompt)