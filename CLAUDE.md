# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

MiroFish is a multi-agent swarm intelligence simulation engine. Users upload seed documents → the system builds a knowledge graph in Zep Cloud → generates thousands of AI agent profiles → runs a social media simulation via CAMEL-AI's OASIS engine → produces a prediction report with an interactive Q&A interface.

**Stack**: Vue 3 + Vite (frontend, port 3000) · Flask 3.0+ (backend, port 5001) · OASIS (`camel-oasis`) simulation subprocess · Zep Cloud knowledge graph · OpenAI SDK-compatible LLM API · `uv` for Python packaging

---

## Commands

### Setup
```bash
npm run setup:all          # Install root + frontend npm deps AND backend Python deps (uv sync)
cp .env.example .env       # Then fill in LLM_API_KEY, ZEP_API_KEY
```

### Development
```bash
npm run dev                # Start both frontend (Vite) and backend (Flask) concurrently
npm run frontend           # Frontend only → http://localhost:3000
npm run backend            # Backend only  → http://localhost:5001
```

### Build & Production
```bash
npm run build              # Vite build → frontend/dist/
docker compose up -d       # Run via Docker (reads .env from root)
```

### Backend tests (optional dev deps must be installed)
```bash
cd backend && uv run pytest                                            # All tests
cd backend && uv run pytest app/services/test_graph_builder.py -k test_chunk_text  # Single test
```

---

## Architecture

### 5-Step Pipeline (matches the frontend Step1–Step5 components)

1. **Graph Build** — Upload PDFs/MD/TXT → `TextProcessor` parses + chunks → `GraphBuilderService` embeds chunks into Zep Cloud via `ZepTools`
2. **Env Setup** — `ZepEntityReader` extracts entities/relationships from the Zep graph → `OntologyGenerator` builds an ontology → `OasisProfileGenerator` creates per-agent profiles with personality, memory, and social links
3. **Simulation** — `SimulationConfigGenerator` builds the OASIS config → `SimulationRunner` **spawns OASIS as a subprocess** → `SimulationIPC` handles inter-process communication for progress/status
4. **Report** — `ReportAgent` analyzes simulation output with tool-calling LLM → produces a structured prediction report
5. **Interaction** — Users chat with the report agent or interview individual simulated agents

### Backend Structure

Three Flask blueprints registered at `/api/graph`, `/api/simulation`, `/api/report` (see `backend/app/api/`). All blueprint routes are defined in `graph.py`, `simulation.py`, `report.py`.

Services in `backend/app/services/` implement the pipeline logic. Key ones:
- `simulation_runner.py` — manages OASIS subprocess lifecycle; registers cleanup on server shutdown
- `report_agent.py` — ReportAgent with configurable tool-call and reflection rounds
- `zep_graph_memory_updater.py` — writes simulation outcomes back to Zep after a run

Config is centralized in `backend/app/config.py`, loaded from the **project root `.env`** (not `backend/.env`).

### Frontend Structure

Vue 3 Composition API. The main workflow lives in `frontend/src/components/` (Step1–Step5 plus `GraphPanel`). Routes in `frontend/src/router/` map to views in `frontend/src/views/`. The Vite dev server proxies all `/api/*` requests to `http://localhost:5001`.

Lightweight state: only a `pendingUpload` store in `frontend/src/store/`. Axios service layer with auto-retry and 5-minute timeout is in `frontend/src/api/`.

### i18n

Translation files live in `/locales/` at the repo root (not inside `frontend/`), aliased as `@locales` in Vite config. Locale is persisted to `localStorage`. Add new keys to both `locales/zh.json` (default) and `locales/en.json`, then use `$t('key')` in templates.

### LLM Configuration

Two LLM configs are supported — primary (`LLM_*`) and an optional "boost" (`LLM_BOOST_*`) for faster/cheaper parallel calls. If `LLM_BOOST_*` variables are absent from `.env`, do not add them as empty strings — the app checks for key presence.

---

## Key Env Variables

Required:
```env
LLM_API_KEY=
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus
ZEP_API_KEY=
```

Optional simulation tuning:
```env
OASIS_DEFAULT_MAX_ROUNDS=10
REPORT_AGENT_MAX_TOOL_CALLS=5
REPORT_AGENT_MAX_REFLECTION_ROUNDS=2
REPORT_AGENT_TEMPERATURE=0.5
```
