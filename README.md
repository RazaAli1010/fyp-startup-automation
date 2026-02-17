# StartBot -- AI-Powered Startup Execution Platform

StartBot is a production-grade, multi-agent AI system that transforms a raw startup idea into a complete execution plan. The platform orchestrates six specialized agents -- Idea Validation, Market Research, Pitch Deck Generation, MVP Planning, Legal Document Drafting, and an AI Chat Co-Founder -- backed by deterministic scoring formulas, structured LLM responses, real-time web research, and retrieval-augmented generation (RAG). The system is fully Dockerized, uses SQLite for lightweight persistence, GPT-4.1 for all language model operations, and supports asynchronous parallel API execution across its agent pipeline.


---

## Table of Contents

1. [Core AI Agents](#core-ai-agents)
2. [System Architecture](#system-architecture)
3. [Tech Stack](#tech-stack)
4. [Database Schema](#database-schema)
5. [Environment Variables](#environment-variables)
6. [Local Development Setup](#local-development-setup)
7. [Dockerized Deployment](#dockerized-deployment)
8. [Production Deployment Notes](#production-deployment-notes)
9. [API Reference](#api-reference)
10. [AI System Design Philosophy](#ai-system-design-philosophy)
11. [Academic Value](#academic-value)
12. [Future Improvements](#future-improvements)
13. [License](#license)


---

## Core AI Agents

### Idea Validation Agent

Orchestrated via a LangGraph `StateGraph` with parallel execution. Three data-gathering nodes -- Reddit pain mining, Google Trends demand analysis, and Exa-powered competitor discovery -- execute concurrently via `asyncio.gather`. Their raw signals flow into a deterministic normalization engine (pure math, no LLM) and then a weighted scoring engine that produces five module scores and a final viability score on a 0--100 scale.

### Market Research Agent

A multi-stage asynchronous pipeline: (1) Tavily API fetches market-size articles and industry reports, (2) Exa semantic search discovers competitors, (3) OpenAI GPT-4.1 extracts structured ranges and confidence levels from the research text, and (4) a deterministic calculator computes TAM, SAM, and SOM estimates with explicit assumptions. All stages run in parallel where dependencies allow.

### Pitch Deck Generator

Consumes validated idea signals and evaluation scores to produce an investor-ready slide deck via the Alai Slides API. The agent builds a structured input narrative from evaluation data, submits it to the Alai generation endpoint, polls for completion, and extracts a shareable presentation URL and PDF export link. No silent fallbacks -- generation failures propagate as explicit errors.

### MVP Generator

A fully rule-based blueprint engine with zero LLM calls. Decision functions select the MVP type, core and excluded features, recommended tech stack, build plan phases, validation criteria, and risk notes based on the idea's industry, customer type, team size, technical complexity, and market research signals. Output is a structured JSON blueprint.

### Legal Document Generator

GPT-4.1 powered, jurisdiction-aware document generation. Supports four document types: NDA, Founder Agreement, Privacy Policy, and Terms of Service. Each document type has a dedicated prompt builder with jurisdiction-specific rules. JSON response format is enforced at the OpenAI client level. All generated documents include a mandatory legal disclaimer.

### AI Chat Co-Founder (RAG)

A retrieval-augmented generation agent backed by ChromaDB. Every agent output (evaluation scores, market research, MVP blueprints, pitch deck summaries, legal documents) is chunked into semantic sections, embedded using OpenAI `text-embedding-3-large`, and indexed in a persistent ChromaDB collection (`startbot_agent_outputs`). User questions are embedded, matched against the idea's indexed data via cosine similarity (top-k=5), and answered by GPT-4.1 with strict context-only guardrails. The agent cites source labels and reports which agents have indexed data.


---

## System Architecture

```
+---------------------------------------------------------------+
|                    Next.js 16 Frontend                         |
|              React 19  /  Tailwind CSS 4                       |
|         (SSR, App Router, TypeScript, ErrorBoundary)           |
+-----------------------------+---------------------------------+
                              | REST API (JSON)
+-----------------------------v---------------------------------+
|                     FastAPI Backend (ASGI)                      |
|                                                                |
|  Routes          Services             Agents                   |
|  +-----------+   +----------------+   +---------------------+  |
|  | auth      |   | openai_client  |   | idea_validation/    |  |
|  | ideas     |   | query_builder  |   |   graph (LangGraph) |  |
|  | evaluation|   | normalization  |   |   nodes/ (parallel) |  |
|  | market-   |   | scoring_engine |   | market_research/    |  |
|  |  research |   | trend_agent    |   |   agent, calculator |  |
|  | pitch-deck|   | problem_agent  |   |   competitors,      |  |
|  | mvp       |   | competitor_    |   |   reasoning,        |  |
|  | legal     |   |  agent/cleaner |   |   research          |  |
|  | chat      |   | reddit_agent   |   | pitch_deck_agent/   |  |
|  +-----------+   | alai_client    |   | mvp_agent/          |  |
|                  | chat_service   |   | legal_agent/        |  |
|                  | vector_store   |   +---------------------+  |
|                  | idea_inference |                             |
|                  +----------------+                             |
|                                                                |
|  +------------------+    +----------------------------------+  |
|  | SQLAlchemy ORM   |--->| SQLite (file: data/startbot.db)  |  |
|  +------------------+    +----------------------------------+  |
|                                                                |
|  +------------------+    +----------------------------------+  |
|  | ChromaDB Client  |--->| Persistent Store (vector_store/) |  |
|  +------------------+    +----------------------------------+  |
+---------------------------------------------------------------+

External APIs:
  OpenAI GPT-4.1          -- LLM inference + embeddings
  Tavily Search API       -- Article and report search
  SerpAPI (Google Trends) -- Trend demand signals
  Exa Search API          -- Semantic competitor discovery
  Reddit API (PRAW)       -- Pain-point mining
  Alai Slides API         -- Pitch deck generation
```


---

## Tech Stack

| Layer               | Technology                                        |
|---------------------|---------------------------------------------------|
| Frontend            | Next.js 16, React 19, Tailwind CSS 4, TypeScript  |
| Backend             | FastAPI 0.115, Python 3.10, Uvicorn (ASGI)        |
| Database            | SQLite (file-based persistence)                   |
| ORM                 | SQLAlchemy 2.0                                    |
| AI Model            | OpenAI GPT-4.1                                    |
| Embeddings          | OpenAI text-embedding-3-large                     |
| Vector Database     | ChromaDB (persistent mode)                        |
| Agent Orchestration | LangGraph (StateGraph with parallel edges)         |
| Search APIs         | Tavily, SerpAPI, Exa                              |
| Social API          | Reddit (PRAW)                                     |
| Slides API          | Alai Slides API                                   |
| Authentication      | JWT (python-jose) + Google OAuth 2.0              |
| Containerization    | Docker, Docker Compose                            |
| Data Validation     | Pydantic 2.10                                     |


---

## Database Schema

StartBot uses SQLite with SQLAlchemy ORM. All primary keys are UUID v4, stored as `CHAR(36)` via a custom `GUID` type decorator for cross-backend compatibility. The database file is persisted at `data/startbot.db` inside the backend container via a Docker volume.

### Tables

| Table              | Description                                                        |
|--------------------|--------------------------------------------------------------------|
| `users`            | User accounts with email, username, hashed password, auth provider (local or Google), and email verification status. |
| `ideas`            | Startup ideas with structured input fields (name, description, industry, customer type, geography) plus OpenAI-inferred attributes (revenue model, technical complexity, regulatory risk, problem/market keywords) and persisted evaluation scores. |
| `market_research`  | Market research reports with TAM/SAM/SOM ranges, ARPU, growth rate, demand strength, competitor data, assumptions, confidence scores, and source references. One-to-one with ideas. |
| `pitch_decks`      | Pitch deck metadata including Alai generation ID, shareable view URL, PDF export URL, provider, and status. Deck content stored as JSON text. One-to-one with ideas. |
| `mvp_reports`      | MVP blueprint reports stored as JSON text. Contains MVP type, core features, tech stack, build plan, validation plan, and risk notes. One-to-one with ideas. |
| `legal_documents`  | Legal documents with type (NDA, founder agreement, privacy policy, terms of service), jurisdiction, and generated content as JSON text. Many-to-one with ideas. |

### Relationships

- **User** 1:N **Idea** -- a user owns many ideas
- **Idea** 1:1 **MarketResearch**
- **Idea** 1:1 **PitchDeck**
- **Idea** 1:1 **MVPReport**
- **Idea** 1:N **LegalDocument** -- multiple document types per idea
- All report tables reference **User** via `user_id` foreign key

### Vector Store (ChromaDB)

Agent outputs are chunked into semantic sections, embedded via `text-embedding-3-large`, and stored in a persistent ChromaDB collection (`startbot_agent_outputs`). Chunks carry metadata including `idea_id`, `agent` name, and `section` label. This index powers the AI Chat Co-Founder RAG pipeline. The vector store is persisted at `vector_store/` via a Docker volume.


---

## Environment Variables

### Backend (`backend/.env.example`)

```
DATABASE_URL=sqlite:///./data/startbot.db

ENV=development
HOST=0.0.0.0
PORT=8000
DEBUG=false
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1
OPENAI_MAX_COMPLETION_TOKENS=4000
OPENAI_TEMPERATURE=0.7
OPENAI_REQUEST_TIMEOUT=40

CHROMADB_PERSIST_DIR=./vector_store

TAVILY_API_KEY=
SERPAPI_KEY=
EXA_API_KEY=

ALAI_API_KEY=
ALAI_BASE_URL=https://slides-api.getalai.com/api/v1
ALAI_MAX_SLIDES=10

JWT_SECRET=
JWT_EXPIRE_MINUTES=1440

EMAIL_HOST=
EMAIL_PORT=587
EMAIL_USER=
EMAIL_PASSWORD=
EMAIL_FROM=
EMAIL_VERIFICATION_SECRET=
FRONTEND_URL=http://localhost:3000

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

### Frontend (`frontend/.env.example`)

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=StartBot
```


---

## Local Development Setup

### Backend

```bash
cd backend
python -m venv env
env\Scripts\activate        # Windows
# source env/bin/activate   # macOS / Linux
pip install -r requirements.txt
copy .env.example .env      # then fill in API keys
uvicorn app.main:app --reload
```

The backend starts at `http://localhost:8000`. Interactive API documentation is available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

The frontend starts at `http://localhost:3000`.


---

## Dockerized Deployment

### Build and Run

```bash
docker compose build
docker compose up
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs

### Service Architecture

The `docker-compose.yml` defines two services:

- **backend** -- FastAPI application served by Uvicorn. Reads API keys from `backend/.env` via `env_file`. Exposes port 8000. Mounts two Docker volumes for persistence. Includes a health check that polls `/health`.
- **frontend** -- Next.js production build served by Node.js. Build-time arguments bake `NEXT_PUBLIC_API_URL` into the JavaScript bundle. Depends on the backend service health check. Exposes port 3000.

### Persistence

| Volume         | Mount Point         | Purpose                               |
|----------------|---------------------|---------------------------------------|
| `backend-data` | `/app/data`         | SQLite database file (`startbot.db`)  |
| `vector-store` | `/app/vector_store` | ChromaDB persistent embeddings        |

Data in both volumes survives container restarts and rebuilds. To reset all data:

```bash
docker compose down -v
docker compose up --build
```

### Networking

Both services communicate over a shared Docker bridge network (`startbot-network`). The frontend calls the backend via the host-mapped port.


---

## Production Deployment Notes

- **Frontend** can be deployed to Vercel. Set `NEXT_PUBLIC_API_URL` to the production backend URL during the build.
- **Backend** can be deployed to Railway, Render, or any platform supporting Docker containers. Set all environment variables via the platform's secret management.
- **SQLite** is suitable for single-node deployments and evaluation environments. For horizontal scaling or multi-instance deployments, migration to PostgreSQL is recommended.
- **ChromaDB** persistence directory should be backed by a persistent volume in cloud deployments.
- **API keys** must never be committed to version control. Use platform-level environment variable injection.


---

## API Reference

### Authentication

| Method | Endpoint                      | Description                              |
|--------|-------------------------------|------------------------------------------|
| `POST` | `/auth/signup`                | Create a new local account               |
| `POST` | `/auth/login`                 | Authenticate and receive a JWT           |
| `GET`  | `/auth/verify-email`          | Verify email via token (query parameter) |
| `GET`  | `/auth/me`                    | Get current authenticated user           |
| `GET`  | `/auth/dashboard`             | Aggregated dashboard with all user data  |
| `GET`  | `/auth/google/status`         | Check if Google OAuth is enabled         |
| `GET`  | `/auth/google/login`          | Initiate Google OAuth flow               |
| `GET`  | `/auth/google/callback`       | Google OAuth callback handler            |

### Ideas

| Method | Endpoint                          | Description                             |
|--------|-----------------------------------|-----------------------------------------|
| `POST` | `/ideas/`                         | Submit a structured startup idea        |

### Idea Evaluation

| Method | Endpoint                          | Description                             |
|--------|-----------------------------------|-----------------------------------------|
| `POST` | `/ideas/{idea_id}/evaluate`       | Run the full evaluation pipeline        |
| `GET`  | `/ideas/{idea_id}/evaluation`     | Retrieve stored evaluation report       |

### Market Research

| Method | Endpoint                              | Description                         |
|--------|---------------------------------------|-------------------------------------|
| `POST` | `/market-research/generate`           | Generate market research for an idea|
| `GET`  | `/market-research/idea/{idea_id}`     | Get research report by idea         |
| `GET`  | `/market-research/`                   | List all research for current user  |

### Pitch Deck

| Method | Endpoint                          | Description                             |
|--------|-----------------------------------|-----------------------------------------|
| `POST` | `/pitch-deck/generate`            | Generate an investor pitch deck         |
| `GET`  | `/pitch-deck/idea/{idea_id}`      | Get pitch deck by idea                  |
| `GET`  | `/pitch-deck/{pitch_deck_id}`     | Get a specific pitch deck               |
| `GET`  | `/pitch-deck/`                    | List all pitch decks for current user   |

### MVP Blueprint

| Method | Endpoint                      | Description                             |
|--------|-------------------------------|-----------------------------------------|
| `POST` | `/mvp/generate`               | Generate MVP blueprint for an idea      |
| `GET`  | `/mvp/idea/{idea_id}`         | Get MVP report by idea                  |
| `GET`  | `/mvp/`                       | List all MVP reports for current user   |

### Legal Documents

| Method | Endpoint                      | Description                             |
|--------|-------------------------------|-----------------------------------------|
| `POST` | `/legal/generate`             | Generate a legal document               |
| `GET`  | `/legal/idea/{idea_id}`       | List all legal documents by idea        |
| `GET`  | `/legal/{document_id}`        | Get a specific legal document           |

### AI Chat Co-Founder

| Method | Endpoint                      | Description                             |
|--------|-------------------------------|-----------------------------------------|
| `POST` | `/chat/{idea_id}/ask`         | Ask the AI Co-Founder a question        |
| `GET`  | `/chat/{idea_id}/status`      | Check which agents have indexed data    |

### System

| Method | Endpoint       | Description              |
|--------|----------------|--------------------------|
| `GET`  | `/`            | API root with metadata   |
| `GET`  | `/health`      | Service health check     |


---

## AI System Design Philosophy

### Structured Scoring Formulas

Evaluation scores are computed by a deterministic scoring engine using explicit mathematical formulas with fixed weights. Five module scores (Problem Intensity, Market Timing, Competition Pressure, Market Potential, Execution Feasibility) are combined into a final viability score. No LLM is involved in scoring -- the formulas are transparent, reproducible, and auditable.

### Deterministic Normalization

A dedicated normalization engine converts heterogeneous raw signals (sentiment scores, growth rates, competitor counts, complexity levels) into a common 0--100 scale using tiered mapping functions, linear interpolation, and clamping. The engine operates under strict rules: no API calls, no database writes, no LLMs, no randomness.

### JSON-Enforced LLM Responses

All GPT-4.1 calls use the `json_object` response format with explicit JSON schema instructions in system prompts. A centralized OpenAI client enforces model, temperature, timeout, and token limits. Invalid JSON responses trigger one automatic retry before falling back to safe defaults.

### Competitor Filtering Pipeline

A three-stage competitor cleaning pipeline operates across both Idea Validation and Market Research agents: (1) hard filtering removes directories, media sites, social platforms, and editorial content using domain and URL-path exclusion lists, (2) OpenAI extracts company names from survivors with strict 2-word and 5-name caps, (3) a final safety check deduplicates, normalizes capitalization, and strips corporate suffixes.

### Async Parallel Execution

The evaluation pipeline dispatches all three data-gathering agents (problem intensity, trend demand, competitor discovery) simultaneously via `asyncio.gather` with `return_exceptions=True`. Each agent independently calls external APIs (Tavily, SerpAPI, Exa, Reddit) in parallel. Failures in one agent do not block others -- empty signals are substituted and scoring continues with degraded confidence.

### Defensive Error Handling

Every agent and route is wrapped in structured error handling. External API failures produce empty-but-valid signal objects rather than crashes. A global exception handler in FastAPI returns sanitized error responses. The frontend uses a React Error Boundary and normalized API error classes.


---

## Academic Value

### Multi-Agent Architecture

StartBot implements a genuine multi-agent system where six specialized agents operate independently, each with a distinct responsibility, data source, and output schema. The Idea Validation Agent uses LangGraph for graph-based orchestration with parallel node execution, demonstrating modern agent framework patterns.

### RAG-Based Conversational AI

The AI Chat Co-Founder implements a complete RAG pipeline: document chunking with agent-specific semantic sections, embedding via OpenAI `text-embedding-3-large`, persistent vector storage in ChromaDB with cosine similarity search, context assembly with source attribution, and grounded answer generation with hallucination guardrails.

### Real API Orchestration

The system integrates five external APIs (OpenAI, Tavily, SerpAPI, Exa, Alai) with proper authentication, timeout handling, retry logic, and graceful degradation. This demonstrates production-level API orchestration rather than mock or simulated data flows.

### Dockerized Microservice-Like Deployment

The Docker Compose configuration isolates frontend and backend into independently buildable, multi-stage Docker images with health checks, volume-based persistence, non-root users, dependency ordering, and network isolation.

### Engineering Maturity

The codebase demonstrates separation of concerns (routes, services, agents, models, schemas), centralized configuration (constants module, OpenAI client), deterministic scoring (no LLM in scoring path), comprehensive Pydantic validation, type-safe TypeScript frontend with 1:1 schema mirroring, and structured logging throughout.

### Scalable Architecture Design

While currently deployed with SQLite for simplicity, the architecture cleanly separates the database layer via SQLAlchemy ORM, the vector store via a service abstraction, and the LLM client via a centralized module. Each layer can be independently swapped or scaled without modifying agent logic.


---

## Future Improvements

- Migration to PostgreSQL for multi-instance and concurrent-write support
- Background task queue (Celery or ARQ) for long-running agent pipelines
- Application performance monitoring and structured logging aggregation
- Redis caching layer for repeated API queries and embedding results
- Horizontal scaling with container orchestration (Kubernetes)
- Alembic database migrations for schema versioning
- Rate limiting and usage quotas per user
- Webhook notifications for completed agent runs
- Export functionality for reports (PDF, DOCX)


---

## License

MIT
