# Interview — Personal RAG Chatbot

A lightweight RAG (Retrieval-Augmented Generation) system built as both a learning project and a real production tool. It powers the AI on [e-mahmoudi.me](https://e-mahmoudi.me) — a chatbot that lets people interview me, ask about my background, work, and life, and get answers grounded in what I have actually written about myself.

If you want to understand how RAG works end to end — from document ingestion to vector search to LLM response — this is a clean, minimal codebase to read through. No frameworks hiding the logic, no magic. Just the pieces you need and nothing else.

---

## What It Does

1. You write about yourself in plain text or markdown files
2. The ingest script reads those files, splits them into chunks, embeds them with a local sentence transformer, and stores the vectors in Postgres
3. A visitor sends a question to the API
4. The API embeds the question, searches for the closest chunks by cosine distance, builds a prompt with that context, and sends it to a local LLM via Ollama
5. The answer comes back grounded in what you actually wrote

---

## Stack

| layer | tool |
|---|---|
| API | FastAPI |
| Embeddings | SentenceTransformers (all-MiniLM-L6-v2, fully local) |
| Vector storage | PostgreSQL + pgvector |
| LLM | Ollama (local, no API key needed) |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Config | YAML (no .env) |

Everything runs locally. No OpenAI key, no HuggingFace token, no external API calls after the first model download.

---

## Project Structure

```
interview/
├── serve.py              # start the API server
├── ingest.py             # ingest documents into vector store
├── migrate.py            # database migrations
├── config.yml            # your config (gitignored)
├── config.example.yml    # template to copy from
├── alembic/
│   ├── env.py
│   └── versions/
└── app/
    ├── __init__.py       # application factory
    ├── config.py         # Config class, loads from yml
    ├── db.py             # SQLAlchemy engine and session
    ├── models.py         # Chunk, Chat, Message models
    ├── router.py         # POST /chat route
    ├── middleware.py      # rate limiting and bot protection
    ├── state.py          # shared instances (config, embedder)
    └── services/
        ├── embed.py      # embedding and chunk search
        └── llm.py        # prompt building and Ollama call
```

---

## Setup

### Prerequisites

- Python 3.12+
- Docker (for Postgres with pgvector)
- [Ollama](https://ollama.ai) installed and running

### 1. Clone and install dependencies

```bash
git clone https://github.com/jeyem/interview
cd interview
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start Postgres with pgvector

```bash
docker compose up -d
```

### 3. Copy and edit config

```bash
cp config.example.yml config.yml
```

Edit `config.yml` with your database credentials and Ollama model name.

### 4. Pull your LLM

```bash
ollama pull gemma3:4b
```

Any model that runs on Ollama works. Adjust the model name in `config.yml`.

### 5. Run migrations

```bash
python migrate.py upgrade
```

### 6. Write about yourself

Create a markdown file describing who you are. See `ehsan.md` as an example. Write in natural language using the same words people would use to ask questions — if someone might ask "what is your level at Python", your document should contain the word "level" near Python.

### 7. Ingest your content

```bash
# single file
python ingest.py --file about-me.md

# entire folder
python ingest.py --dir docs/
```

Supported formats: `.md`, `.txt`, `.pdf`, and any plain text format.

### 8. Start the server

```bash
python serve.py
```

---

## Usage

The API has a single endpoint.

```
POST /chat
```

```json
{
  "message": "tell me about yourself",
  "user_hash": "b94d27b9934d3e08a52e52d7da7dabfac484efe04294e576e4eb9aed5c5b3e12"
}
```

The `user_hash` identifies a visitor without login. Generate it on the frontend from browser fingerprint data (user agent, timezone, screen resolution) and hash with sha256. It must be a 64 character hex string.

Response:

```json
{
  "chat_id": "6e06c20e-6a3f-4317-ad1b-7f9b31d9b6b2",
  "message": {
    "role": "assistant",
    "content": "I'm Ehsan, a software engineer with 12 years of experience..."
  }
}
```

Each visitor gets one persistent chat. Conversation history is stored in Postgres and included in the context for follow-up questions.

### Test with curl
**Note:** The protection middleware blocks requests that do not come from a real browser — no valid `User-Agent`, `Accept`, or `Accept-Language` headers means a 403. curl fails this check in production.
>
> In **debug mode** (`debug: true` in `config.yml`) the middleware is bypassed so you can test freely from the terminal. In **production** (`debug: false`) all requests must come from a real browser client.

```bash
# generate a user hash
HASH=$(echo -n "my-browser" | sha256sum | cut -d' ' -f1)

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Accept-Language: en-US" \
  -d "{\"message\": \"tell me about yourself\", \"user_hash\": \"$HASH\"}"
```

---

## Configuration

`config.yml` is the single source of truth. No environment variables except secrets injected via `${VAR}` placeholders in production.

```yaml
app:
  name: "interview"
  debug: true
  host: "localhost"
  port: 8000

database:
  host: "localhost"
  port: 5432
  name: "chatbot"
  user: "chatbot"
  password: "passwd"

embeddings:
  model: "sentence-transformers/all-MiniLM-L6-v2"
  dimensions: 384
  chunk_size: 150
  chunk_overlap: 20
  top_k: 3
  offline: true

llm:
  provider: "ollama"
  model: "gemma3:4b"
  base_url: "http://localhost:11434"
  timeout: 120
```

---

## Migration Commands

```bash
python migrate.py upgrade              # apply all pending migrations
python migrate.py downgrade            # roll back one step
python migrate.py revision -m "msg"    # generate a new migration
python migrate.py history              # show migration history
```

---

## Rate Limiting

The middleware protects the API at two levels. By IP address: 5 requests per minute, 100 per day. By user hash: same limits on top of the IP check. Basic bot protection checks that requests carry real browser headers (User-Agent, Accept, Accept-Language). Counters are in-memory and reset on restart.

---

## How RAG Works (the learning part)

**Ingestion**

Your documents are split into overlapping chunks of fixed word length. Each chunk is passed through a sentence transformer model that converts it into a vector — a list of 384 numbers that represent the meaning of the text. These vectors are stored in Postgres alongside the original text.

**Retrieval**

When a question arrives, it is embedded with the same model. Postgres finds the chunks whose vectors are closest to the question vector using cosine distance. Closest means most semantically similar — not keyword matching, meaning matching.

**Generation**

The retrieved chunks are inserted into a prompt as context. The LLM reads the context and the question and produces an answer grounded in what was retrieved. If nothing relevant was retrieved, the LLM is instructed to say so rather than hallucinate.

The quality of answers depends on three things: how well your document is written, how well the chunk size matches the granularity of questions, and how clearly the prompt instructs the model. All three are tunable without touching the code.

---

## Adding a New LLM Provider

The service layer is provider-agnostic. To add a new provider, add one function to `services/llm.py` and register it:

```python
async def _ask_openai(prompt: str) -> str:
    # your implementation
    ...

_PROVIDERS = {
    "ollama":      _ask_ollama,
    "huggingface": _ask_huggingface,
    "openai":      _ask_openai,     # added
}
```

Then change `provider` in `config.yml`. Nothing else changes.

---

## Production

For production, keep `config.yml` outside the repository and pass the path at startup:

```bash
python serve.py -c /etc/interview/config.yml
python migrate.py -c /etc/interview/config.yml upgrade
```

Secrets like database passwords can be injected via environment variables using `${VAR}` syntax in the yml file:

```yaml
database:
  password: "${DB_PASSWORD}"
```

---

## License

GPLv3

---

Built by [Ehsan Mahmoudi](https://e-mahmoudi.me)