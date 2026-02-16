# StartBot

**A multi-agent AI system for structured startup idea validation, market research, and document generation.**

---

## Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [System Architecture](#system-architecture)
4. [Agent Descriptions](#agent-descriptions)
5. [Tech Stack](#tech-stack)
6. [Setup and Installation](#setup-and-installation)
7. [Environment Variables](#environment-variables)
8. [Design Decisions](#design-decisions)
9. [Limitations and Future Work](#limitations-and-future-work)
10. [Academic Context](#academic-context)
11. [Disclaimer](#disclaimer)
12. [License](#license)

---

## Overview

Early-stage startup founders face a recurring problem: validating whether an idea is worth pursuing requires gathering market signals from multiple fragmented sources, interpreting them correctly, and translating findings into actionable artifacts such as pitch decks, MVP plans, and legal documents. This process is time-consuming, subjective, and error-prone when performed manually.

StartBot addresses this by orchestrating a pipeline of specialized AI agents that collectively transform a structured startup idea intake into a comprehensive validation report, market research analysis, investor-ready pitch deck, MVP blueprint, and jurisdiction-aware legal documents. Each agent operates on a well-defined input/output contract, and the system enforces strict dependency ordering to ensure that downstream agents always receive validated upstream data.

The platform is designed as a production-grade web application with a FastAPI backend, a Next.js frontend, persistent storage, and full authentication -- suitable for demonstration as both a working product and an academically rigorous software engineering artifact.

---

## Key Features

- **Structured Idea Intake** -- Multi-step form capturing startup name, industry, geography, target customer, revenue model, pricing, team size, technical complexity, and regulatory risk.
- **Idea Validation Agent** -- Parallel data collection from Tavily, SerpAPI, and Exa, followed by deterministic scoring across five evaluation modules with epistemic rigour (kill switches, contradiction detection, uncertainty propagation).
- **Market Research Agent** -- TAM/SAM/SOM estimation using Tavily research text, Exa competitor discovery, OpenAI constrained reasoning, and a deterministic market size calculator.
- **Pitch Deck Generator** -- Investor-ready slide deck generation via the Alai Slides API, consuming validated idea data and evaluation scores.
- **MVP Blueprint Generator** -- Fully deterministic (no LLM) rule-based engine that produces MVP type selection, feature scoping, tech stack recommendations, build plans, and validation strategies.
- **Legal Document Generator** -- Jurisdiction-aware generation of NDAs, Founder Agreements, Privacy Policies, and Terms of Service using OpenAI with strict JSON output and GDPR compliance detection.
- **Unified Dashboard** -- Single view of all ideas, evaluations, reports, and generated artifacts with status tracking and cross-agent navigation.
- **Authentication** -- Email/password signup with email verification, Google OAuth 2.0, and JWT-based session management.
- **Persistence** -- All ideas, evaluations, reports, and generated documents are stored in a relational database (SQLite for development, PostgreSQL-ready for production).

---

## System Architecture

StartBot follows a layered, modular architecture with strict separation of concerns between data collection, signal normalization, scoring, and artifact generation.

```
Frontend (Next.js + TypeScript)
    |
    | HTTP/JSON (REST API)
    v
Backend (FastAPI)
    |
    +-- Routes (auth, ideas, evaluation, pitch_deck, market_research, mvp, legal)
    |
    +-- Services Layer
    |     +-- Problem Intensity Agent    (Tavily + SerpAPI)
    |     +-- Trend & Demand Agent       (SerpAPI Google Trends)
    |     +-- Competitor Discovery Agent  (Exa semantic search)
    |     +-- Normalization Engine        (deterministic 0-100 scaling)
    |     +-- Scoring Engine              (weighted module scores)
    |     +-- OpenAI Client              (centralized, GPT-4.1)
    |     +-- Alai Slides Client         (pitch deck API)
    |
    +-- Agents Layer
    |     +-- Idea Validation Agent      (LangGraph pipeline)
    |     +-- Market Research Agent      (Tavily + Exa + OpenAI + Calculator)
    |     +-- Pitch Deck Agent           (Alai Slides API)
    |     +-- MVP Agent                  (deterministic rules engine)
    |     +-- Legal Document Agent       (OpenAI + jurisdiction rules)
    |
    +-- Models (SQLAlchemy ORM)
    |     +-- User, Idea, PitchDeck, MarketResearch, MVPReport, LegalDocument
    |
    +-- Database (SQLite / PostgreSQL)
```

### Agent Dependency Graph

Agents enforce strict prerequisite ordering. No downstream agent can execute without its upstream dependencies being satisfied.

```
Idea Intake
    |
    v
Idea Validation Agent  (required by all downstream agents)
    |
    +---> Market Research Agent
    |         |
    |         +---> MVP Blueprint Generator (requires validation + market research)
    |
    +---> Pitch Deck Generator (requires validation)
    |
    +---> Legal Document Generator (requires validation)
```

### Design Principles

- **No circular dependencies** -- agents form a directed acyclic graph.
- **Deterministic where possible** -- scoring, normalization, and MVP generation use pure mathematical formulas with no LLM involvement.
- **LLM only where necessary** -- OpenAI is used only for market research reasoning (extracting ranges from research text) and legal document generation (jurisdiction-aware legal prose). All other agents use deterministic logic.
- **Graceful degradation** -- if an external API fails, agents continue with reduced confidence rather than crashing.
- **Idempotent storage** -- evaluations and documents are stored once; subsequent requests return cached results rather than regenerating.

---

## Agent Descriptions

### 1. Idea Validation Agent

**Purpose:** Evaluate a startup idea's viability by collecting real market signals from multiple independent sources and producing a transparent, scored assessment.

**Inputs:**

- Structured idea fields: startup name, description, industry, target customer type, geography, revenue model, pricing estimate, team size, technical complexity, regulatory risk.

**Core Logic:**
The agent is implemented as a LangGraph `StateGraph` with four nodes:

1. **Problem Intensity Node** -- Queries Tavily and SerpAPI to measure how painful the problem is. Extracts search intent signals, complaint frequency, manual-process indicators, and evidence density. Scoring formula: `0.30 x search_intent + 0.25 x complaint + 0.25 x manual_cost + 0.20 x evidence`. Includes guardrails: fewer than 2 evidence categories caps the score at 55; all signals missing defaults to 35.

2. **Trend & Demand Node** -- Queries SerpAPI (Google Trends engine) with a 5-year window to extract interest time-series data. Computes growth rate, momentum, and demand strength using tiered mapping functions with hard caps to prevent inflation from noisy Google Trends data.

3. **Competitor Discovery Node** -- Uses Exa semantic search to discover competitors. Extracts competitor names (normalized and deduplicated), feature overlap signals, funding indicators, and market density metrics. No LLM involvement.

4. **Judge Logic Node** -- Deterministic aggregation of all upstream signals. Runs normalization (heterogeneous raw signals to comparable 0-100 scale), then scoring across five weighted modules:
   - Problem Intensity (direct pass-through, already 0-100)
   - Market Timing (0.4 x growth + 0.3 x momentum + 0.3 x demand)
   - Competition Pressure (competitor density, funding pressure, feature overlap)
   - Market Potential (TAM proxy, demand strength, pricing viability)
   - Execution Feasibility (team adequacy, tech complexity, regulatory risk)

   Final viability score is a weighted sum of all five modules. Includes kill-switch logic (auto-reject if market dominated by well-funded incumbents) and contradiction detection between data sources.

**Outputs:** Final viability score (0-100), five module scores, verdict (Promising / Moderate / Risky / Not Viable), risk level, key strength, key risk, epistemic status, falsification tests, and conditional recommendations.

**Dependencies:** Tavily API, SerpAPI, Exa API. No OpenAI.

**Why it exists:** Provides the foundational assessment that all other agents depend on. Without validated signals, downstream agents would operate on unverified assumptions.

---

### 2. Market Research Agent

**Purpose:** Produce a quantified market analysis (TAM, SAM, SOM) grounded in real research data, competitor intelligence, and constrained LLM reasoning.

**Inputs:**

- Validated idea fields (from Idea Validation)
- Industry, geography, target customer type, pricing estimate, description

**Core Logic:**
Orchestrated as a five-step pipeline:

1. **Tavily Research** -- Fetches market-focused research text using queries built from industry, description, geography, and target customer type. Returns article snippets about market size, growth rates, and industry reports.

2. **Exa Competitor Discovery** -- Semantic search for competitors with normalized name extraction (deduplication, suffix stripping, max 8 results).

3. **OpenAI Constrained Reasoning** -- Passes research text and startup context to GPT-4.1 with a strict JSON-only system prompt. Extracts: customer count estimates (min/max), growth rate estimate (CAGR), falsifiable assumptions, and confidence level. Falls back to conservative defaults if OpenAI is unavailable.

4. **Deterministic Calculator** -- Computes TAM, SAM, SOM using customer count estimates and annual revenue per user (ARPU). Applies market penetration rates based on target customer type (B2B, B2C, Marketplace) and competition density.

5. **Result Assembly** -- Combines all outputs into a unified `MarketResearchResult` with demand strength scoring (0-100 composite of growth, SOM, pricing, competition).

**Outputs:** TAM/SAM/SOM ranges (min/max), ARPU, growth rate estimate, demand strength score, assumptions, confidence assessment, competitor list, and source URLs.

**Dependencies:** Tavily API, Exa API, OpenAI (GPT-4.1). Requires completed Idea Validation.

**Why it exists:** Provides quantified market sizing that the MVP agent uses for scope decisions and that founders need for investor conversations.

---

### 3. Pitch Deck Generator Agent

**Purpose:** Generate an investor-ready presentation deck from validated idea data and evaluation scores.

**Inputs:**

- Idea context: name, description, industry, target customer, geography, revenue model, pricing, team size
- Validation context: final score, verdict, risk level, key strength/risk, all five module scores

**Core Logic:**

1. Builds a structured input text combining idea details and validation results.
2. Calls the Alai Slides API (`POST /generations`) with the input text and deck title.
3. Polls the generation endpoint until completion.
4. Extracts the shareable view URL and PDF export URL.

The agent does not generate slide content locally -- it delegates entirely to the Alai Slides API, which produces professionally designed presentations. The agent fails loudly if the Alai API key is missing (no silent fallback).

**Outputs:** `PitchDeckOutput` containing deck title, tagline, Alai generation ID, shareable view URL, and PDF download URL.

**Dependencies:** Alai Slides API. Requires completed Idea Validation.

**Why it exists:** Transforms structured evaluation data into a visual artifact that founders can immediately use for investor meetings.

---

### 4. MVP Blueprint Generator Agent

**Purpose:** Produce a complete, actionable MVP blueprint using deterministic rules -- no LLM, no randomness.

**Inputs:**

- Validated idea fields (startup name, industry, target customer, geography, revenue model, pricing, team size, tech complexity, regulatory risk)
- Evaluation scores (all five module scores + final viability score)
- Market research confidence level and competitor data

**Core Logic:**
A pure rule-based engine with composable decision functions:

- **MVP Type Selection** -- Chooses from Concierge MVP, Landing Page + Waitlist, Wizard of Oz, Single-Feature MVP, or Functional Prototype based on market confidence, execution feasibility, problem intensity, market potential, tech complexity, and competition pressure.
- **Core Feature Scoping** -- Selects 3-5 features based on industry vertical, customer type, and viability score.
- **Excluded Features** -- Explicitly lists features deferred from MVP scope.
- **User Flow** -- Generates ordered user journey steps tailored to the MVP type.
- **Tech Stack Recommendation** -- Selects frontend, backend, database, hosting, and analytics tools based on tech complexity, team size, and industry.
- **Build Plan** -- Phased timeline with milestones.
- **Validation Plan** -- Hypothesis testing strategy with success metrics.
- **Risk Notes** -- Key risks and mitigation strategies derived from evaluation scores.

**Outputs:** `MVPBlueprint` containing MVP type, core hypothesis, primary user, core features, excluded features, user flow, tech stack, build plan, validation plan, and risk notes.

**Dependencies:** None (deterministic). Requires completed Idea Validation and Market Research.

**Why it exists:** Bridges the gap between "this idea is viable" and "here is exactly what to build first." The deterministic approach ensures reproducible, explainable recommendations.

---

### 5. Legal Document Generator Agent

**Purpose:** Generate jurisdiction-aware startup legal documents using OpenAI with structured JSON output.

**Inputs:**

- Document type (NDA, Founder Agreement, Privacy Policy, Terms of Service)
- Company name, industry, geography
- Founder count (for Founder Agreements)
- Effective date (auto-generated if not provided)

**Core Logic:**

1. **Jurisdiction Resolution** -- Maps geography to governing law clause (e.g., "Laws of the State of Delaware, United States") and detects GDPR compliance requirements for EU/UK countries. Deterministic, rule-based.
2. **Prompt Construction** -- Selects a document-type-specific prompt builder that injects company details, jurisdiction, governing law, and GDPR clauses (where required).
3. **OpenAI Generation** -- Calls GPT-4.1 with a legal drafter system prompt and `response_format: json_object`. The system prompt enforces a strict JSON schema with sections array, disclaimer, and risk notes.
4. **Validation** -- Checks for required keys, validates section shape (each must have `title` and `content`), and enforces the mandatory disclaimer.
5. **Enrichment** -- Appends jurisdiction-specific customization notes from the rules engine.

**Outputs:** `LegalDocumentOutput` containing document type, jurisdiction, governing law, mandatory disclaimer, ordered sections, customization notes, legal risk notes, and generation timestamp.

**Supported Document Types:**

- Non-Disclosure Agreement (NDA)
- Founder Agreement
- Privacy Policy
- Terms of Service

**Dependencies:** OpenAI (GPT-4.1). Requires completed Idea Validation.

**Why it exists:** Founders need basic legal documents early in the startup process. This agent provides jurisdiction-aware templates that serve as starting points, reducing the barrier to getting legally organized.

---

## Tech Stack

### Backend

| Component           | Technology                                                                                   |
| ------------------- | -------------------------------------------------------------------------------------------- |
| Framework           | FastAPI 0.115                                                                                |
| ORM                 | SQLAlchemy 2.0                                                                               |
| Database            | SQLite (development), PostgreSQL (production-ready)                                          |
| LLM                 | OpenAI GPT-4.1 (via centralized client)                                                      |
| Agent Orchestration | LangGraph (Idea Validation pipeline)                                                         |
| Validation          | Pydantic 2.10                                                                                |
| Authentication      | JWT (python-jose), bcrypt, Google OAuth 2.0                                                  |
| HTTP Client         | httpx, requests                                                                              |
| External APIs       | Tavily (research), SerpAPI (Google Trends), Exa (semantic search), Alai Slides (pitch decks) |

### Frontend

| Component        | Technology                                                                       |
| ---------------- | -------------------------------------------------------------------------------- |
| Framework        | Next.js 16 (App Router)                                                          |
| Language         | TypeScript 5                                                                     |
| UI Library       | React 19                                                                         |
| Styling          | Tailwind CSS 4                                                                   |
| Fonts            | Geist Sans, Geist Mono                                                           |
| State Management | React Context (AuthProvider)                                                     |
| Components       | Custom component library (Button, Card, Spinner, GatingModal, InfoTooltip, etc.) |

---

## Setup and Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn
- API keys for: OpenAI, Tavily, SerpAPI, Exa, Alai Slides

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/agentic-startup-fyp.git
cd agentic-startup-fyp
```

### 2. Backend Setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and fill in your API keys (see Environment Variables section)
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

### 4. Run the Application

**Start the backend** (from the `backend` directory):

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Start the frontend** (from the `frontend` directory):

```bash
npm run dev
```

### 5. Access the Application

- **Frontend:** http://localhost:3000
- **Backend API docs:** http://localhost:8000/docs
- **Backend ReDoc:** http://localhost:8000/redoc

---

## Environment Variables

Create a `.env` file in the `backend` directory based on `.env.example`:

```env
# === OpenAI Configuration ===
OPENAI_API_KEY=                         # Required for Market Research + Legal agents
OPENAI_MODEL=gpt-4.1                    # Model used by all OpenAI-dependent agents
OPENAI_MAX_COMPLETION_TOKENS=4000       # Max response tokens
OPENAI_TEMPERATURE=0.7                  # Generation temperature
OPENAI_RESPONSE_FORMAT=json             # Enforce JSON output
OPENAI_REQUEST_TIMEOUT=40               # Request timeout in seconds

# === External Research APIs ===
EXA_API_KEY=                            # Exa.ai — competitor discovery
TAVILY_API_KEY=                         # Tavily — market research + problem intensity
SERPAPI_KEY=                            # SerpAPI — Google Trends data

# === Pitch Deck Generation ===
ALAI_API_KEY=                           # Alai Slides API — pitch deck generation
ALAI_BASE_URL=https://slides-api.getalai.com/api/v1
ALAI_MAX_SLIDES=10

# === Funding Enrichment (Optional) ===
FUNDING_PROVIDER=rapidapi
RAPIDAPI_KEY=                           # RapidAPI — Crunchbase competitor funding data
RAPIDAPI_HOST=crunchbase-crunchbase-v1.p.rapidapi.com

# === Authentication ===
JWT_SECRET=                             # Secret key for JWT token signing
JWT_EXPIRE_MINUTES=1440                 # Token expiry (24 hours)
EMAIL_HOST=                             # SMTP host for email verification
EMAIL_PORT=587
EMAIL_USER=
EMAIL_PASSWORD=
EMAIL_FROM=
EMAIL_VERIFICATION_SECRET=
FRONTEND_URL=http://localhost:3000

# === Google OAuth 2.0 ===
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# === Database (Optional — defaults to SQLite) ===
# DATABASE_URL=postgresql://user:password@localhost:5432/startbot

# === Server ===
HOST=127.0.0.1
PORT=8000
DEBUG=true
```

---

## Design Decisions

### Why GPT-4.1

GPT-4.1 was selected for its balance of output quality, latency, and reliability. It supports `response_format: json_object` natively, which eliminates the need for post-hoc JSON extraction from free-text responses. Earlier experiments with GPT-5.x models showed increased timeouts, invalid JSON responses, and retry exhaustion under production-like workloads. GPT-4.1 provides deterministic-enough outputs at significantly lower latency.

### Why Deterministic Logic Where Possible

Three of the five agents (Idea Validation, MVP Blueprint, and the scoring/normalization pipeline) use no LLM at all. This is an intentional design choice:

- **Reproducibility** -- Given the same inputs, the system produces the same outputs. This is critical for academic evaluation and debugging.
- **Explainability** -- Every score can be traced to a specific formula and input signal. There are no "the model decided" black boxes in scoring.
- **Cost** -- LLM calls are expensive and slow. Restricting them to tasks that genuinely require language generation (legal prose, market reasoning) keeps the system fast and affordable.
- **Reliability** -- Deterministic code does not hallucinate, timeout, or produce malformed output.

### Why Modular Agents

Each agent has a single responsibility, a defined input/output contract, and no knowledge of other agents' internals. This enables:

- Independent testing and development of each agent
- Clear dependency ordering with no circular references
- Graceful degradation (if Market Research fails, the Idea Validation result is still valid)
- Easy addition of new agents without modifying existing ones

### Why External APIs Instead of Self-Hosted Models

The system relies on external APIs (Tavily, SerpAPI, Exa, OpenAI, Alai) rather than self-hosted models or scrapers. This decision reflects:

- **Data freshness** -- APIs like Tavily and SerpAPI provide access to current web data and Google Trends, which a static model cannot.
- **Scope management** -- Building and maintaining web scrapers, trend databases, or fine-tuned models is outside the scope of this project.
- **Quality** -- Specialized APIs (e.g., Exa for semantic search) outperform general-purpose alternatives for their specific tasks.

### How Scalability Was Considered

- The database layer supports both SQLite (development) and PostgreSQL (production) via SQLAlchemy's dialect abstraction.
- The OpenAI client reads all configuration from environment variables, enabling per-deployment tuning without code changes.
- The agent pipeline's DAG structure supports future parallelization of independent agents.
- All API routes are stateless and use dependency injection for database sessions.

---

## Limitations and Future Work

### Current Limitations

- **Single-user focus** -- The dashboard does not support team collaboration or shared idea workspaces.
- **English only** -- All prompts, research queries, and generated documents assume English-language content.
- **No real-time updates** -- Agent execution is synchronous; long-running operations (pitch deck generation) block the request.
- **Legal documents are templates** -- Generated legal documents are starting points, not attorney-reviewed instruments.
- **Google Trends as proxy** -- SerpAPI Google Trends data is a directional signal, not precise market sizing data. The normalization engine applies hard caps to prevent score inflation from noisy trend data.

### Future Work

- **Asynchronous agent execution** -- Move long-running agents to background tasks with WebSocket or polling-based status updates.
- **Financial projections agent** -- Add a dedicated agent for revenue forecasting, unit economics modeling, and burn rate estimation.
- **Multi-language support** -- Extend prompts and research queries to support non-English markets.
- **Collaborative workspaces** -- Enable team-based idea development with role-based access control.
- **Agent memory** -- Allow agents to reference previous evaluations when re-assessing updated ideas.
- **Export functionality** -- PDF export of evaluation reports, market research, and legal documents.
- **CI/CD pipeline** -- Automated testing, linting, and deployment workflows.

---

## Academic Context

### Project Type

This project was developed as a Final Year Project (FYP) in Computer Science / Software Engineering. It demonstrates the practical application of multi-agent system design, API integration, full-stack web development, and responsible AI usage within a single cohesive product.

### Scope and Learning Outcomes

- **Multi-agent architecture** -- Designing, implementing, and orchestrating multiple specialized agents with defined contracts and dependency ordering.
- **Hybrid AI systems** -- Combining deterministic algorithms with LLM-based generation, understanding when each approach is appropriate.
- **Full-stack engineering** -- Building a production-grade application with authentication, persistent storage, RESTful APIs, and a modern frontend.
- **External API integration** -- Working with rate-limited, paid APIs (OpenAI, Tavily, SerpAPI, Exa, Alai) and handling failures gracefully.
- **Data normalization and scoring** -- Converting heterogeneous signals from different sources into comparable, weighted scores using transparent mathematical formulas.

### Ethical Considerations

- **AI transparency** -- The system clearly separates deterministic scoring (fully explainable) from LLM-generated content (marked as AI-generated). Legal documents carry a mandatory disclaimer.
- **No fabricated data** -- Market research reasoning is grounded in Tavily research text. The system prompt explicitly instructs the LLM to use null values when data is insufficient rather than inventing numbers.
- **Legal responsibility** -- All generated legal documents include the disclaimer: _"This document is generated for informational purposes only and does not constitute legal advice."_
- **API key security** -- All secrets are read from environment variables and excluded from version control via `.gitignore`.

---

## Disclaimer

StartBot is an academic project and demonstration system. It is not intended for production use without further validation.

- **AI-generated content** -- Outputs from OpenAI-powered agents (Market Research reasoning, Legal Documents) are generated by a large language model and may contain inaccuracies. All outputs should be reviewed by qualified professionals before use.
- **Legal documents** -- All generated legal documents are for informational purposes only and do not constitute legal advice. Consult a licensed attorney before using any generated document in a legal context.
- **Market data** -- Market size estimates, growth rates, and competitor analyses are approximations based on publicly available data and should not be used as the sole basis for investment or business decisions.
- **No warranty** -- The software is provided as-is, without warranty of any kind.

---

## License

This project was developed as a university Final Year Project. Please contact the authors for licensing inquiries.
