# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🏛️ High-Level Architecture

The application appears to be a modern, service-oriented Python backend, likely using **FastAPI** (inferred from package dependencies and general structure) that interacts with a **PostgreSQL** database and leverages external **Large Language Models (LLMs)** for core functionality.

### Core Components & Interactions:

1.  **Configuration Management (`app/config.py`):**
    *   This module centralizes all settings by reading a `config.yml` file.
    *   It initializes and manages distinct configuration objects for `Database`, `Embeddings`, and `LLM`.
    *   It is responsible for constructing the final, usable connection strings (e.g., `self.DATABASE_URL`).

2.  **Database Layer (`app/db.py`):**
    *   Uses **SQLAlchemy** for Object-Relational Mapping (ORM).
    *   The `init_db(db_url)` function sets up global engine and session factory instances, enforcing the use of context managers (`get_session`) to ensure transactions are committed or rolled back correctly.

3.  **Business Logic / Services Layer (`services/`):**
    *   **LLM Interaction (`services/llm.py`):** This is the core intelligence layer. It encapsulates the logic for querying external LLMs.
        *   It uses an abstract provider system (`_PROVIDERS`) allowing switching between implementations (currently supports **Ollama** and **Hugging Face**).
        *   It constructs sophisticated prompts using context chunks (retrieved embeddings), conversation history (`app.models.Message`), and the current user question.
        *   Communication happens asynchronously using `httpx` to endpoints exposed by the LLM service.
    *   **Embeddings:** The `Embeddings` dataclass (defined in `app/config.py`) suggests a vector store interaction pipeline, likely pairing this service with `services/embed.py` (module exists but content was not read).

4.  **Infrastructure (Docker):**
    *   `docker-compose.yml` defines the necessary services:
        *   `postgres`: An instance of PostgreSQL with the `pgvector` extension enabled, required for storing vector embeddings.
        *   It manages networking and service dependencies (e.g., the application connecting to the `postgres` service on port `5432`).

## 🛠️ Developer Workflows & Commands

Based on the files, the typical developer workflow involves setting up the environment, migrating the database, and then running the application.

### 1. Setup & Initial Run (Development Environment)
The recommended starting point for a full local development cycle is using Docker Compose:
*   **Action:** Start all required services (Database, etc.) and bring the application online.
*   **Command:** `docker-compose up` (This assumes the structure defined in `docker-compose.yml` is used).

### 2. Database Schema Management (Migrations)
*   **Tool:** **Alembic** is the ORM migration tool used.
*   **Workflow:** Changes to the database model (`app/models.py`) require running migrations before the application can start against a clean schema.
*   **Commands (Inferred):**
    *   Generate migration scripts: `alembic revision --autogenerate [message]`
    *   Apply migrations: `alembic upgrade head`

### 3. Application Execution
*   **Primary Entry Point:** The `serve.py` file is the most likely candidate for the root execution script.
*   **Service Execution:** The application logic seems to be tied to a web framework (FastAPI/Uvicorn).
*   **Commands (Inferred):**
    *   If running via the wrapper script: `python serve.py`
    *   If running the API server directly: `uvicorn main:app --reload` (assuming `main` is the module name)

### 4. Testing, Linting, and Building
*   **Testing:** While no explicit `Makefile` or `pytest` calls were found in the root, the presence of `pytest` dependencies in the virtual environment suggests tests are unit/integration tests. A developer should check for a dedicated `tests/` directory or a script that runs: `pytest` or similar.
*   **Linting/Building:** No explicit `lint` or `build` commands were found. These are likely defined in a missing `Makefile` or within the `package.json` (if Node dependencies were present).

## 📝 Summary of Found Artifacts

*   **Configuration:** `app/config.py` loads settings from `config.yml`.
*   **Database:** Uses SQLAlchemy, PostgreSQL with `pgvector`, and is managed via `docker-compose.yml`.
*   **AI Logic:** `services/llm.py` abstracts multi-provider LLM calls (Ollama, HF).
*   **Dependencies:** Key dependencies are managed (implied by `venv` and `docker-compose.yml`), including `fastapi`, `sqlalchemy`, `pyyaml`, `httpx`, and `pgvector`.