# StartBot — Multi-Agent AI System for Startup Workflow Automation

StartBot is a multi-agent AI system that transforms a raw startup idea into a complete, data-backed execution plan. A user provides five inputs — startup name, description, industry, geography, and customer type — and the platform orchestrates six specialised agents to produce an idea evaluation with deterministic scores, a TAM/SAM/SOM market research report, an investor-grade pitch deck, a rule-based MVP blueprint, jurisdiction-aware legal documents, and a RAG-powered AI chat co-founder that can answer questions about any previously generated output.

The system is fully Dockerised (PostgreSQL 16 + FastAPI + Next.js 16), uses GPT-4.1 for all LLM operations, and executes all external API calls asynchronously in parallel via `asyncio.gather`. Scoring is **100 % deterministic** — no LLM is involved in computing the final viability score.

> **Transparency note — Reddit / PRAW.** The previous README listed Reddit (PRAW) as a data source for the Idea Validation Agent. **This is incorrect.** The files `reddit_agent.py` and `reddit_schema.py` exist in the repository but are **dead code** — they are never imported by any active route or service. The Problem Intensity module uses **Tavily + SerpAPI only**. PRAW remains in `requirements.txt` as a vestigial dependency. This README documents the system as it actually runs.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Tech Stack](#3-tech-stack)
4. [How the System Works — End-to-End](#4-how-the-system-works--end-to-end)
5. [Agent 1 — Idea Validation (Deep Dive)](#5-agent-1--idea-validation-deep-dive)
6. [Agent 2 — Market Research (Deep Dive)](#6-agent-2--market-research-deep-dive)
7. [Agent 3 — Pitch Deck Generator](#7-agent-3--pitch-deck-generator)
8. [Agent 4 — MVP Blueprint Generator](#8-agent-4--mvp-blueprint-generator)
9. [Agent 5 — Legal Document Generator](#9-agent-5--legal-document-generator)
10. [Agent 6 — AI Chat Co-Founder (RAG)](#10-agent-6--ai-chat-co-founder-rag)
11. [Scoring & Formula Breakdown](#11-scoring--formula-breakdown)
12. [Database Schema](#12-database-schema)
13. [External API Integrations & Fallbacks](#13-external-api-integrations--fallbacks)
14. [Environment Variables](#14-environment-variables)
15. [Local Development Setup](#15-local-development-setup)
16. [Docker Deployment](#16-docker-deployment)
17. [API Reference](#17-api-reference)
18. [Frontend Architecture](#18-frontend-architecture)
19. [Known Limitations & Future Improvements](#19-known-limitations--future-improvements)
20. [Why This Project Is Technically Strong](#20-why-this-project-is-technically-strong)
21. [License](#21-license)

---

## 1. Project Overview

StartBot automates the early-stage startup workflow. A founder enters five fields:

| Input                  | Example                                                         |
| ---------------------- | --------------------------------------------------------------- |
| `startup_name`         | "PayFlow"                                                       |
| `one_line_description` | "AI-powered invoice automation for freelancers" (min 20 chars)  |
| `industry`             | Multi-select from 40 industries (centralised in `constants.py`) |
| `geography`            | Multi-select countries                                          |
| `target_customer_type` | B2B / B2C / B2B2C                                               |

From these inputs, the system infers additional attributes via OpenAI (revenue model, technical complexity, regulatory risk, keywords) and then runs six agents sequentially or on demand.

### The Six Agents

| #   | Agent                | LLM? | External APIs        | Output                                      |
| --- | -------------------- | ---- | -------------------- | ------------------------------------------- |
| 1   | Idea Validation      | No\* | Tavily, SerpAPI, Exa | 5 module scores + final viability 0-100     |
| 2   | Market Research      | Yes  | Tavily, Exa, OpenAI  | TAM/SAM/SOM ranges, competitors, confidence |
| 3   | Pitch Deck Generator | No   | Alai Slides API      | Shareable URL + PDF                         |
| 4   | MVP Blueprint        | No   | None                 | Rule-based MVP plan (JSON)                  |
| 5   | Legal Document       | Yes  | OpenAI               | Jurisdiction-aware legal docs               |
| 6   | AI Chat Co-Founder   | Yes  | OpenAI + ChromaDB    | RAG-grounded answers with sources           |

\*Agent 1 uses OpenAI only for attribute inference (step 2 of the pipeline), never for scoring.

---

## 2. System Architecture

### Diagram 1 — High-Level Architecture

```mermaid
graph TB
    subgraph Frontend["Next.js 16 Frontend"]
        FE_Pages["Pages: Dashboard · Ideas · Evaluation<br/>Market Research · Pitch Deck · MVP · Legal · Chat"]
        FE_API["api.ts — centralised fetch client"]
        FE_Auth["AuthProvider — JWT token management"]
    end

    subgraph Backend["FastAPI Backend — ASGI"]
        Routes["Routes: auth · ideas · evaluation<br/>market_research · pitch_deck · mvp · legal · chat"]
        Services["Services: openai_client · query_builder<br/>normalization_engine · scoring_engine<br/>problem_intensity_agent · trend_agent<br/>competitor_agent · competitor_cleaner<br/>idea_inference · alai_client<br/>chat_service · vector_store"]
        Agents["Agents: market_research/<br/>pitch_deck/ · mvp_agent/ · legal_agent/"]
    end

    subgraph Storage["Persistence"]
        PG[("PostgreSQL 16")]
        Chroma[("ChromaDB<br/>vector_store/")]
    end

    subgraph ExtAPIs["External APIs"]
        OpenAI["OpenAI GPT-4.1<br/>+ text-embedding-3-large"]
        Tavily["Tavily Search"]
        SerpAPI["SerpAPI — Google Trends"]
        Exa["Exa Semantic Search"]
        Alai["Alai Slides API"]
    end

    FE_Pages --> FE_API
    FE_API -->|"REST / JSON"| Routes
    Routes --> Services
    Routes --> Agents
    Services --> PG
    Services --> Chroma
    Services --> OpenAI
    Services --> Tavily
    Services --> SerpAPI
    Services --> Exa
    Services --> Alai
    Agents --> Services
```

### Diagram 2 — Docker Deployment

```mermaid
graph LR
    subgraph DockerCompose["docker-compose.yml"]
        DB["db<br/>postgres:16-alpine<br/>Port 5432"]
        BE["backend<br/>FastAPI + Uvicorn<br/>Port 8000"]
        FE["frontend<br/>Next.js production<br/>Port 3000"]
    end

    DB -->|"pg_isready healthcheck"| BE
    BE -->|"HTTP healthcheck /health"| FE

    Volume1[("postgres-data<br/>/var/lib/postgresql/data")]
    Volume2[("vector-store<br/>/app/vector_store")]

    DB --- Volume1
    BE --- Volume2

    Network["startbot-network — bridge"]
    DB --- Network
    BE --- Network
    FE --- Network
```

---

## 3. Tech Stack

| Layer            | Technology                                                 |
| ---------------- | ---------------------------------------------------------- |
| Frontend         | Next.js 16.1.6, React 19.2.3, Tailwind CSS 4, TypeScript 5 |
| Backend          | FastAPI 0.115, Python 3.10+, Uvicorn (ASGI)                |
| Database         | PostgreSQL 16 (Alpine)                                     |
| ORM              | SQLAlchemy 2.0                                             |
| AI Model         | OpenAI GPT-4.1 (configurable via `OPENAI_MODEL`)           |
| Embeddings       | OpenAI `text-embedding-3-large`                            |
| Vector Database  | ChromaDB (persistent mode, cosine similarity)              |
| Search APIs      | Tavily, SerpAPI, Exa                                       |
| Slides API       | Alai Slides API                                            |
| Authentication   | JWT (`python-jose`) + Google OAuth 2.0                     |
| HTTP Client      | `httpx` (async)                                            |
| Containerisation | Docker, Docker Compose                                     |
| Data Validation  | Pydantic 2.10                                              |

> **Note on LangGraph:** The file `idea_validation/graph.py` defines a `StateGraph` with nodes `search_reddit`, `search_trends`, `search_competitors`, and `judge_logic`. However, **all three search nodes are deprecated stubs** that return no-op values. The actual evaluation pipeline runs directly from the route handler (`routes/evaluation.py`) by calling service-layer agents in parallel via `asyncio.gather`. The LangGraph graph is retained as legacy code.
>
> **Note on Reddit / PRAW:** `reddit_agent.py` and `reddit_schema.py` exist in the repository and `praw` is in `requirements.txt`, but **no active route or service imports them**. The Problem Intensity module uses Tavily + SerpAPI exclusively.

---

## 4. How the System Works — End-to-End

### Diagram 3 — Request Lifecycle: User Submits an Idea

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant BE as Backend API
    participant DB as PostgreSQL
    participant OAI as OpenAI
    participant Tav as Tavily
    participant Serp as SerpAPI
    participant ExaAPI as Exa
    participant CV as ChromaDB

    User->>FE: Fill form (5 inputs)
    FE->>BE: POST /ideas/
    BE->>DB: INSERT idea row
    BE-->>FE: { id: uuid }

    User->>FE: Click Evaluate
    FE->>BE: POST /ideas/{id}/evaluate

    Note over BE,OAI: Step 1 — OpenAI Inference
    BE->>OAI: Infer revenue_model, tech_level, reg_level, keywords
    OAI-->>BE: Structured JSON
    BE->>DB: UPDATE idea (inferred columns)

    Note over BE: Step 2 — Build QueryBundle (deterministic)

    Note over BE,Serp: Step 3 — Parallel Signal Fetch
    par Problem Intensity
        BE->>Tav: 7 pain queries
        BE->>Serp: 6 search-intent queries
    and Trend Demand
        BE->>Serp: Google Trends 3-tier fallback
    and Competitor Discovery
        BE->>ExaAPI: 5 semantic queries
    end

    Tav-->>BE: ProblemIntensitySignals
    Serp-->>BE: TrendDemandSignals
    ExaAPI-->>BE: CompetitorSignals

    Note over BE: Step 4 — Normalize (pure math, 0-100)
    Note over BE: Step 5 — Score (deterministic formulas)
    Note over BE: Step 6 — Rule-based summary

    BE->>DB: UPDATE idea (score + report JSON)
    BE->>CV: Index chunks for RAG
    BE-->>FE: IdeaEvaluationReport
    FE-->>User: Display scores + verdict
```

### Pipeline Steps (as implemented in `routes/evaluation.py`)

1. **Fetch Idea** from PostgreSQL by UUID.
2. **OpenAI Inference** (`idea_inference.py`) — infer `revenue_model`, `technical_complexity_level` (low/medium/high), `regulatory_risk_level` (low/medium/high), `core_problem_keywords`, `market_keywords`. Map levels to numeric: low→0.20, medium→0.50, high→0.75/0.80. Persist to Idea model.
3. **Build QueryBundle** (`query_builder.py`) — deterministic keyword generation: core queries, 3-tier trend keywords, 5 Exa competitor queries, industry tags. No randomness.
4. **Parallel Signal Fetch** via `asyncio.gather(return_exceptions=True)`:
   - `fetch_problem_intensity_signals(idea)` — Tavily + SerpAPI
   - `fetch_trend_demand_signals(query_bundle)` — SerpAPI Google Trends
   - `fetch_competitor_signals(query_bundle)` — Exa semantic search
5. **Normalize** (`normalization_engine.py`) — convert raw signals to 0-100.
6. **Score** (`scoring_engine.py`) — compute 5 module scores + final viability.
7. **Summary** — rule-based verdict (Strong/Moderate/Weak), risk level, key strength, key risk.
8. **Persist** — store `final_viability_score` and full `evaluation_report_json` on the Idea row.
9. **Index for RAG** — chunk report, embed via `text-embedding-3-large`, upsert into ChromaDB.
10. **Return** `IdeaEvaluationReport` to frontend.

### GET-First Pattern

The frontend tries `GET /ideas/{id}/evaluation` first (reads stored JSON). Only if that returns 404 does it call `POST /ideas/{id}/evaluate`. The pipeline never re-runs for an already-evaluated idea.

---

## 5. Agent 1 — Idea Validation (Deep Dive)

### Diagram 4 — Idea Validation Pipeline

```mermaid
graph LR
    INF["OpenAI<br/>Inference"] --> QB["Query<br/>Builder"]
    QB --> PI["Problem Intensity<br/>Tavily + SerpAPI"]
    QB --> TD["Trend Demand<br/>SerpAPI Trends"]
    QB --> CD["Competitor Discovery<br/>Exa + Cleaner"]
    PI --> NE["Normalization<br/>Engine"]
    TD --> NE
    CD --> NE
    INF -->|"tech/reg levels"| NE
    NE --> SE["Scoring<br/>Engine"]
    SE --> FS["Final Score<br/>0-100"]
    SE --> SUM["Rule-Based<br/>Summary"]
```

### 5.1 Problem Intensity Agent

**File:** `services/problem_intensity_agent.py` — **APIs: Tavily + SerpAPI only. No Reddit, no Exa, no LLM.**

#### Signal Collection

**Tavily** (7 parallel queries): pain/fix queries, manual workflow detection, inefficiency/cost queries, alternatives queries. Each: `search_depth=advanced`, `max_results=5`, `timeout=15s`. Deduplicated by URL, boilerplate stripped.

**SerpAPI** (6 parallel queries): 4 problem-oriented + 2 general baseline. Computes `problem_query_ratio` and `alternatives_query_ratio`.

#### Signal Extraction from Content

- **Pain article count** — articles with pain keywords (`manual`, `slow`, `inefficient`, `expensive`, etc.)
- **Complaint density** — fraction of passages with complaint phrases (`"too slow"`, `"waste of time"`, etc.)
- **Manual process detection** — keywords like `"spreadsheet"`, `"email-based"`, `"copy-paste"`
- **Avg article recency** — months since publication (default 24)
- **Estimated time waste** — `min(manual_keyword_hits × 1.5, 20.0)` hours/week

#### Component Scoring (Deterministic, Tiered)

| Component         | Thresholds                                               | Range |
| ----------------- | -------------------------------------------------------- | ----- |
| **Search Intent** | ratio > 0.6→75, 0.4-0.6→60, 0.2-0.4→45, <0.2→30          | 30-75 |
| **Evidence**      | ≥3 articles AND ≤12mo→70, ≥2 OR ≤18mo→55, 0→30           | 30-70 |
| **Complaint**     | density≥0.5 AND ≥3 phrases→70, ≥0.25→55, any→40, none→35 | 35-70 |
| **Manual Cost**   | detected AND >10h→80, 5-10h→65, <5h→50, none→30          | 30-80 |

#### Final Problem Intensity Score

```
problem_intensity = 0.30 × search_intent + 0.25 × complaint + 0.25 × manual_cost + 0.20 × evidence
```

#### Guardrails

- All 4 categories missing → score = 35
- < 2 categories present → cap at 55
- No manual + complaint < 45 → cap at 60
- Always clamped to [1, 99]

#### Confidence: HIGH (≥3 categories), MEDIUM (2), LOW (0-1)

### 5.2 Trend & Demand Agent

**File:** `services/trend_agent.py` — **API: SerpAPI Google Trends. No LLM.**

#### Multi-Tier Keyword Fallback

- **Tier 1** — idea-specific (e.g., `"automated bookkeeping"`)
- **Tier 2** — category-level (e.g., `"accounting software"`)
- **Tier 3** — broad market (e.g., `"accounting"`)

Stops at first tier with usable data. All keywords per tier fetched in parallel. Google Trends `TIMESERIES`, 5-year window.

#### Metrics

| Metric            | Formula                                                              |
| ----------------- | -------------------------------------------------------------------- |
| `growth_rate_5y`  | `(last_12mo_avg - first_12mo_avg) / first_12mo_avg`, clamped [-1, 2] |
| `momentum_score`  | `((last_6mo - prev_6mo) / prev_6mo + 1) / 2`, clamped [0, 1]         |
| `demand_strength` | `min(avg_volume/100, 1.0) × (1 + growth_rate)`, clamped [0, 1]       |

**Fallback:** If demand < 0.05, uses search demand proxy (regular Google search results count). Floor: 0.05.

### 5.3 Competitor Discovery Agent

**File:** `services/competitor_agent.py` — **API: Exa semantic search.**

1. 5 Exa queries (parallel, 10 results each)
2. Domain dedup — exclude 30+ directories/media/social sites
3. Shared **competitor cleaner** (`competitor_cleaner.py`): hard filter → OpenAI name extraction (≤5 names, max 2 words) → domain-root fallback → final safety check

| Metric                     | Formula                                              |
| -------------------------- | ---------------------------------------------------- |
| `competitor_density_score` | `min(total_competitors / 20, 1.0)`                   |
| `feature_overlap_score`    | Jaccard similarity of description nouns vs. keywords |

### 5.4 Normalization Engine

**File:** `services/normalization_engine.py` — **Pure math. No API, no DB, no LLM.**

| Signal                  | Raw Source                 | Mapping                     |
| ----------------------- | -------------------------- | --------------------------- |
| `pain_intensity`        | Problem Intensity score    | Direct pass-through (0-100) |
| `demand_strength`       | Trend demand (0-1)         | × 100                       |
| `market_growth`         | Trend growth_rate_5y       | Tiered (see below)          |
| `market_momentum`       | Trend momentum (0-1)       | × 100                       |
| `competition_density`   | Competitor density (0-1)   | × 100                       |
| `feature_overlap`       | Competitor overlap (0-1)   | × 100                       |
| `tech_complexity_score` | Idea tech_complexity (0-1) | × 100                       |
| `regulatory_risk_score` | Idea regulatory_risk (0-1) | × 100                       |

#### Market Growth Tiered Mapping

```
≥ 20%     → 80 (hard cap — Google Trends ≠ real CAGR)
10%-20%   → 65 + (rate-0.10)/0.10 × 15   →  [65, 80]
3%-10%    → 50 + (rate-0.03)/0.07 × 15   →  [50, 65]
0%-3%     → 35 + rate/0.03 × 15           →  [35, 50]
0 (none)  → 40 (neutral default)
negative  → 10 + max(rate+1, 0) × 10      →  [10, 20]
```

**Low-confidence cap:** If `trend_data_available = False`, market signals capped at 50.
**Missing signal default:** 40.

---

## 6. Agent 2 — Market Research (Deep Dive)

### Diagram 5 — Market Research Agent Flow

```mermaid
sequenceDiagram
    participant Route as Route
    participant Agent as agent.py
    participant Tav as Tavily
    participant ExaMR as Exa
    participant OAI as OpenAI
    participant Calc as Calculator

    Route->>Agent: run_market_research(idea fields)
    par Parallel
        Agent->>Tav: fetch_market_research_text()
        Agent->>ExaMR: fetch_competitors()
    end
    Tav-->>Agent: research passages
    ExaMR-->>Agent: competitors + count
    Agent->>OAI: run_reasoning(passages, ...)
    OAI-->>Agent: customer_count, growth, confidence
    Agent->>Calc: calculate_market_size(...)
    Calc-->>Agent: TAM/SAM/SOM ranges
    Agent-->>Route: MarketResearchResult
```

### 6.1 Tavily Research (`research.py`)

5 numeric-seeking queries built from industry, description, geography, customer type. All parallel. Passages ≥ 50 chars, deduplicated by URL, boilerplate stripped. Numeric signal detection for `$`, `%`, `billion/million`, `CAGR`, year references.

**Fallback:** If `TAVILY_API_KEY` missing → returns empty list, agent continues with low confidence.

### 6.2 Exa Competitor Discovery (`competitors.py`)

Same shared `competitor_cleaner.py` pipeline as Idea Validation. 5 Exa queries in parallel. Returns `{competitors: [{name, description}], competitor_count}`.

### 6.3 OpenAI Reasoning (`reasoning.py`)

Sends research passages + context to GPT-4.1. Required JSON output: `customer_count_estimate` (min/max), `growth_rate_estimate`, `assumptions` (list), `confidence` (low/medium/high).

**Fallback** (OpenAI unavailable): B2B→50K-500K customers, B2C→500K-10M, Marketplace→100K-2M. Growth: "10-20% CAGR (fallback)". Confidence: "low".

### 6.4 Deterministic Calculator (`calculator.py`)

```
ARPU_annual = pricing_estimate × 12
TAM = customer_count × ARPU_annual     (min/max range)
SAM = TAM × SAM_ratio                  (B2B: 8-15%, B2C: 3-8%, Marketplace: 5-12%)
SOM = SAM × SOM_ratio                  (0.5-2%)
```

Supports bottom-up (customer count available) and top-down (fallback) modes. All values capped at reasonable maximums.

---

## 7. Agent 3 — Pitch Deck Generator

**File:** `agents/pitch_deck_agent/generator.py` — **API: Alai Slides. No LLM.**

1. Route re-runs evaluation (or reads stored) to get module scores
2. `_build_input_text()` creates structured narrative from idea + validation data
3. Calls `generate_pitch_deck_via_alai(input_text, deck_title)`
4. Alai client: `POST /generations` → poll `GET /generations/{id}` (up to 20×, 3s interval) → extract `view_url` + `pdf_url`
5. Returns `PitchDeckOutput` with `generation_id`, `view_url`, `pdf_url`

**No silent fallback** — if Alai key is missing or generation fails, raises `AlaiError`.

---

## 8. Agent 4 — MVP Blueprint Generator

**File:** `agents/mvp_agent/generator.py` + `rules.py` — **Zero LLM calls. Pure rule-based.**

### Diagram 6 — MVP Type Decision Tree

```mermaid
graph TD
    A["Start"] --> B{"market_confidence == low<br/>OR exec_feasibility < 40?"}
    B -->|Yes| C["Concierge MVP"]
    B -->|No| D{"problem_intensity < 50<br/>AND market_potential < 50?"}
    D -->|Yes| E["Landing Page + Waitlist"]
    D -->|No| F{"tech_complexity > 0.7?"}
    F -->|Yes| G["Wizard of Oz MVP"]
    F -->|No| H{"competition_pressure < 50?"}
    H -->|Yes| I["Single-Feature MVP"]
    H -->|No| J["Functional Prototype"]
```

Decision functions: `decide_mvp_type`, `decide_core_features` (3-5 features based on revenue model), `decide_excluded_features`, `decide_user_flow` (customer type aware), `decide_tech_stack` (team size + complexity), `decide_build_plan` (3 phases, timeline adjusted by team), `decide_validation_plan` (metrics by confidence), `decide_risk_notes` (contextual warnings).

---

## 9. Agent 5 — Legal Document Generator

**File:** `agents/legal_agent/generator.py` — **API: OpenAI GPT-4.1.**

Supports: NDA, Founder Agreement, Privacy Policy, Terms of Service. Jurisdiction-aware via `resolve_jurisdiction(geography)` — maps country to governing law, GDPR flag, legal notes. Calls `call_openai_chat_async(max_tokens=4000)`. Validates response keys. Attaches mandatory disclaimer. **No fallback** — raises `RuntimeError` on failure.

---

## 10. Agent 6 — AI Chat Co-Founder (RAG)

### Diagram 7 — RAG Pipeline

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant Chat as chat route
    participant VS as vector_store
    participant OAI as OpenAI

    User->>FE: Ask question
    FE->>Chat: POST /chat/{idea_id}/ask
    Chat->>VS: get_indexed_agents(idea_id)
    Chat->>VS: embed_single_async(question)
    VS->>OAI: text-embedding-3-large
    OAI-->>VS: query vector
    Chat->>VS: query_by_idea(id, vector, top_k=5)
    VS-->>Chat: 5 ranked chunks
    Chat->>OAI: GPT-4.1 (context + question)
    OAI-->>Chat: grounded answer
    Chat-->>FE: answer + sources + indexed_agents
```

Every agent indexes its output after completion. Chunks are created by agent-specific chunkers in `vector_store.py` with deterministic IDs (`SHA-256(idea_id:agent:section)[:24]`). Collection: `startbot_agent_outputs`, cosine similarity. Chat LLM config: model `gpt-4.1`, temperature `0.6`, max_tokens `900`, no JSON mode.

---

## 11. Scoring & Formula Breakdown

### Diagram 8 — Score Composition

```mermaid
graph LR
    PI["pain_intensity"] -->|"× 0.25"| FV["Final Viability Score"]
    MT["market_timing"] -->|"× 0.25"| FV
    CP["competition_pressure"] -->|"× 0.20"| FV
    MP["market_potential"] -->|"× 0.15"| FV
    EF["execution_feasibility"] -->|"× 0.15"| FV
```

### Module Score Formulas (from `scoring_engine.py`)

| Module                    | Formula                                                               | Meaning                      |
| ------------------------- | --------------------------------------------------------------------- | ---------------------------- |
| **Problem Intensity**     | `pain_intensity` (direct pass-through)                                | How painful is the problem?  |
| **Market Timing**         | `0.4 × market_growth + 0.3 × market_momentum + 0.3 × demand_strength` | Is the market growing now?   |
| **Competition Pressure**  | `100 - (0.6 × competition_density + 0.4 × feature_overlap)`           | Less competition = higher    |
| **Market Potential**      | `0.6 × demand_strength + 0.4 × market_growth`                         | How large/growing is demand? |
| **Execution Feasibility** | `100 - (0.6 × tech_complexity_score + 0.4 × regulatory_risk_score)`   | Easier to build = higher     |

### Final Viability Score

```
final_viability = 0.25 × problem_intensity
               + 0.25 × market_timing
               + 0.20 × competition_pressure
               + 0.15 × market_potential
               + 0.15 × execution_feasibility
```

All scores clamped to **[0, 100]**.

### Rule-Based Summary

| Final Score | Verdict                                                            |
| ----------- | ------------------------------------------------------------------ |
| ≥ 70        | **Strong** — "shows strong potential based on validated signals"   |
| 45-69       | **Moderate** — "has moderate potential with some risk factors"     |
| < 45        | **Weak** — "faces significant challenges based on current signals" |

Risk level, key strength (highest module), key risk (lowest module) determined programmatically.

### Normalization Explanations

Every signal includes a `NormalizationExplanation` with `raw_value`, `formula` (human-readable), and `description` — returned in the API response for full transparency.

---

## 12. Database Schema

### Diagram 9 — Entity Relationship

```mermaid
erDiagram
    USERS ||--o{ IDEAS : owns
    IDEAS ||--o| MARKET_RESEARCH : has
    IDEAS ||--o| PITCH_DECKS : has
    IDEAS ||--o| MVP_REPORTS : has
    IDEAS ||--o{ LEGAL_DOCUMENTS : has

    USERS {
        CHAR36 id PK
        string email UK
        string username UK
        string hashed_password
        bool is_email_verified
        string auth_provider
    }

    IDEAS {
        CHAR36 id PK
        string startup_name
        text one_line_description
        string industry
        string target_customer_type
        string geography
        float tech_complexity
        float regulatory_risk
        string inferred_revenue_model
        float final_viability_score
        text evaluation_report_json
        CHAR36 user_id FK
    }

    MARKET_RESEARCH {
        CHAR36 id PK
        CHAR36 idea_id FK
        float tam_min
        float tam_max
        float sam_min
        float sam_max
        float som_min
        float som_max
        text competitors_json
    }

    PITCH_DECKS {
        CHAR36 id PK
        CHAR36 idea_id FK
        string view_url
        string pdf_url
        string generation_id
    }

    MVP_REPORTS {
        CHAR36 id PK
        CHAR36 idea_id FK
        text blueprint_json
    }

    LEGAL_DOCUMENTS {
        CHAR36 id PK
        CHAR36 idea_id FK
        string document_type
        text document_json
    }
```

All PKs are UUID v4 stored as `CHAR(36)` via custom `GUID` TypeDecorator. Tables created via `Base.metadata.create_all()` at startup (no Alembic).

### Vector Store (ChromaDB)

- **Collection:** `startbot_agent_outputs` — cosine similarity, HNSW index
- **Embedding:** `text-embedding-3-large`
- **Persistence:** `./vector_store/` (Docker volume `vector-store`)
- **Chunk ID:** `SHA-256(idea_id:agent:section)[:24]`

---

## 13. External API Integrations & Fallbacks

### Diagram 10 — API Usage Map

```mermaid
graph TD
    subgraph Agents
        IV["Idea Validation"]
        MR["Market Research"]
        PD["Pitch Deck"]
        LE["Legal"]
        CH["Chat"]
        INF["Inference"]
        CC["Competitor Cleaner"]
    end

    subgraph APIs
        OAI["OpenAI GPT-4.1"]
        EMB["OpenAI Embeddings"]
        TAV["Tavily"]
        SERP["SerpAPI"]
        EXA["Exa"]
        ALAI["Alai Slides"]
    end

    INF --> OAI
    IV --> TAV
    IV --> SERP
    IV --> EXA
    CC --> OAI
    MR --> TAV
    MR --> EXA
    MR --> OAI
    PD --> ALAI
    LE --> OAI
    CH --> OAI
    CH --> EMB
```

### Per-API Details

| API                   | Timeout          | Retry   | Fallback                                         |
| --------------------- | ---------------- | ------- | ------------------------------------------------ |
| **OpenAI GPT-4.1**    | 40s              | 1 retry | Returns `None` → safe defaults or `RuntimeError` |
| **OpenAI Embeddings** | 15s              | 0       | Logs error, skips indexing                       |
| **Tavily**            | 15s              | 0       | Returns empty → agent continues                  |
| **SerpAPI**           | 10s              | 0       | Returns empty → neutral defaults (40)            |
| **Exa**               | 10s              | 0       | Returns empty → 0 competitors                    |
| **Alai Slides**       | 30s + 20×3s poll | 0       | Raises `AlaiError` (no fallback)                 |

### OpenAI Client (`openai_client.py`)

Single module for all GPT-4.1 calls. Enforces `response_format: {"type": "json_object"}`. JSON sanitiser strips markdown fences, trailing commas, prose. `validate_required_keys()` shared across agents. Config from env: `OPENAI_MODEL`, `OPENAI_TEMPERATURE` (0.7), `OPENAI_REQUEST_TIMEOUT` (40s), `OPENAI_MAX_COMPLETION_TOKENS` (4000).

---

## 14. Environment Variables

### Backend (`backend/.env.example`)

| Variable                 | Default                                                  | Purpose                   |
| ------------------------ | -------------------------------------------------------- | ------------------------- |
| `DATABASE_URL`           | `postgresql://startbot:startbot@localhost:5432/startbot` | DB connection             |
| `OPENAI_API_KEY`         | required                                                 | All OpenAI calls          |
| `OPENAI_MODEL`           | `gpt-4.1`                                                | LLM model                 |
| `OPENAI_TEMPERATURE`     | `0.7`                                                    | LLM temperature           |
| `OPENAI_REQUEST_TIMEOUT` | `40`                                                     | LLM timeout (seconds)     |
| `TAVILY_API_KEY`         | required for eval                                        | Problem Intensity, MR     |
| `SERPAPI_KEY`            | required for eval                                        | Problem Intensity, Trends |
| `EXA_API_KEY`            | required for eval                                        | Competitor agent, MR      |
| `ALAI_API_KEY`           | required for pitch                                       | Pitch Deck                |
| `CHROMADB_PERSIST_DIR`   | `./vector_store`                                         | ChromaDB path             |
| `JWT_SECRET`             | required                                                 | Auth tokens               |
| `CORS_ORIGINS`           | `http://localhost:3000,...`                              | Allowed origins           |
| `GOOGLE_CLIENT_ID`       | optional                                                 | Google OAuth              |
| `EMAIL_HOST`             | optional                                                 | SMTP verification         |

### Frontend

| Variable               | Default                 | Purpose     |
| ---------------------- | ----------------------- | ----------- |
| `NEXT_PUBLIC_API_URL`  | `http://localhost:8000` | Backend URL |
| `NEXT_PUBLIC_APP_NAME` | `StartBot`              | App title   |

---

## 15. Local Development Setup

### Backend

```bash
cd backend
python -m venv env
env\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env        # fill in API keys
uvicorn app.main:app --reload
```

Backend: `http://localhost:8000` — Docs: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:3000`

### PostgreSQL

Run via Docker Compose (recommended): `docker compose up db`

---

## 16. Docker Deployment

```bash
docker compose build
docker compose up
```

### Services

| Service    | Image                | Port | Depends On          | Healthcheck    |
| ---------- | -------------------- | ---- | ------------------- | -------------- |
| `db`       | `postgres:16-alpine` | 5432 | —                   | `pg_isready`   |
| `backend`  | Custom (FastAPI)     | 8000 | `db` (healthy)      | HTTP `/health` |
| `frontend` | Custom (Next.js)     | 3000 | `backend` (healthy) | —              |

### Persistence

| Volume          | Mount                      | Purpose             |
| --------------- | -------------------------- | ------------------- |
| `postgres-data` | `/var/lib/postgresql/data` | PostgreSQL data     |
| `vector-store`  | `/app/vector_store`        | ChromaDB embeddings |

All services on `startbot-network` (bridge). Backend `DATABASE_URL` overridden to `postgresql://startbot:startbot@db:5432/startbot`. Reset: `docker compose down -v && docker compose up --build`.

---

## 17. API Reference

| Method | Endpoint                     | Description             |
| ------ | ---------------------------- | ----------------------- |
| `POST` | `/auth/signup`               | Create account          |
| `POST` | `/auth/login`                | Authenticate → JWT      |
| `GET`  | `/auth/me`                   | Current user            |
| `GET`  | `/auth/dashboard`            | Aggregated dashboard    |
| `GET`  | `/auth/verify-email`         | Email verification      |
| `GET`  | `/auth/google/login`         | Google OAuth            |
| `GET`  | `/auth/google/callback`      | Google callback         |
| `POST` | `/ideas/`                    | Submit idea (5 fields)  |
| `POST` | `/ideas/{id}/evaluate`       | Run evaluation pipeline |
| `GET`  | `/ideas/{id}/evaluation`     | Get stored evaluation   |
| `POST` | `/market-research/generate`  | Generate TAM/SAM/SOM    |
| `GET`  | `/market-research/idea/{id}` | Get stored MR           |
| `GET`  | `/market-research/`          | List all MR             |
| `POST` | `/pitch-deck/generate`       | Generate pitch deck     |
| `GET`  | `/pitch-deck/idea/{id}`      | Get deck by idea        |
| `GET`  | `/pitch-deck/{id}`           | Get deck by ID          |
| `GET`  | `/pitch-deck/`               | List all decks          |
| `POST` | `/mvp/generate`              | Generate MVP blueprint  |
| `GET`  | `/mvp/idea/{id}`             | Get MVP by idea         |
| `GET`  | `/mvp/`                      | List all MVPs           |
| `POST` | `/legal/generate`            | Generate legal doc      |
| `GET`  | `/legal/idea/{id}`           | List legal docs by idea |
| `GET`  | `/legal/{id}`                | Get legal doc           |
| `POST` | `/chat/{id}/ask`             | Ask AI Co-Founder       |
| `GET`  | `/chat/{id}/status`          | Chat data status        |
| `GET`  | `/`                          | API root                |
| `GET`  | `/health`                    | Health check            |

---

## 18. Frontend Architecture

### Diagram 11 — Frontend Structure

```mermaid
graph TD
    subgraph Pages["App Router Pages"]
        Home["/ — Landing"]
        Auth["auth/ — Login · Signup"]
        Dash["dashboard/ — Overview"]
        Ideas["ideas/ — New · Detail"]
        MR["market-research/ — Report"]
        PD["pitch-deck/ — (future)"]
        MVP["mvp/ — Blueprint"]
        Legal["legal/ — Documents"]
        Chat["chat/ — AI Co-Founder"]
    end

    subgraph Lib["Shared Library"]
        API["api.ts — centralised fetch"]
        Types["types.ts — TypeScript types"]
        Constants["constants.ts — industries · countries"]
        AuthCtx["auth-context.tsx — JWT provider"]
    end

    subgraph Components
        UI["ui/ — buttons, cards, modals"]
        Report["report/ — score visualisations"]
        Forms["forms/ — idea input"]
        Layout["layout/ — navbar, sidebar"]
        EB["ErrorBoundary.tsx"]
    end

    Pages --> Lib
    Pages --> Components
```

- **Next.js 16.1.6** with App Router, React 19.2.3, Tailwind CSS 4, TypeScript 5
- **Centralised API client** (`api.ts`) — all backend calls via `request<T>()` with JWT injection, timeout (120s), `AbortController`, auto-clear token on 401
- **Token management** — `localStorage` via `getToken()` / `setToken()` / `clearToken()`
- **Error handling** — `ApiError` class, React `ErrorBoundary` wrapping `<main>`
- **GET-first pattern** — evaluation and MR pages try GET first, POST only on 404
- **Constants mirrored** — `constants.ts` mirrors backend `constants.py` (industries, countries, customer types)

---

## 19. Known Limitations & Future Improvements

### Current Limitations

- **No background task queue** — all agent pipelines run synchronously within the HTTP request lifecycle. Long-running evaluations block the response.
- **No Alembic migrations** — schema changes require `Base.metadata.create_all()` or manual DB recreation.
- **Reddit/PRAW dead code** — `reddit_agent.py`, `reddit_schema.py`, and `praw` dependency remain in the repo but are unused.
- **No rate limiting** — API endpoints have no per-user throttling.
- **Single-region ChromaDB** — vector store is local; no distributed vector DB.
- **Google Trends ≠ real CAGR** — the `market_growth` signal is a proxy derived from search interest, not actual revenue data. Hard-capped at 80 to prevent overestimation.

### Future Improvements

- Background task queue (Celery or ARQ) for async pipelines
- Alembic for schema version control
- Redis caching for repeated API queries
- Kubernetes for horizontal scaling
- Rate limiting and usage quotas
- Webhook notifications for completed agent runs
- PDF/DOCX export for all reports
- Remove dead Reddit/PRAW code and dependency

---

## 20. Why This Project Is Technically Strong

- **Multi-agent architecture** — six independent agents with distinct responsibilities, data sources, and schemas
- **Deterministic scoring** — no LLM in the scoring path; formulas are transparent, reproducible, auditable
- **RAG pipeline** — complete document chunking, embedding, retrieval, and grounded generation with source attribution
- **Real API orchestration** — five external APIs with proper auth, timeouts, retries, and graceful degradation
- **Async parallel execution** — `asyncio.gather` dispatches agents and API calls concurrently
- **Shared infrastructure** — centralised OpenAI client, shared competitor cleaner, mirrored constants
- **Defensive engineering** — global exception handler, React ErrorBoundary, empty-but-valid fallback signals
- **Full Dockerisation** — three-service Docker Compose with healthchecks, volumes, and dependency ordering
- **Separation of concerns** — routes → services → agents → models → schemas, each independently testable
- **Comprehensive validation** — Pydantic schemas on all API boundaries, TypeScript types mirrored 1:1

---

## 21. License

MIT
