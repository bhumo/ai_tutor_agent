# Repository Guidelines

## Project Structure & Module Organization

`main.py` creates the FastAPI application, mounts the static frontend, and exposes authentication and chat routes. Agent behavior lives in `agents/`, while `graph/workflow.py` connects the tutor, math, and physics agents through LangGraph. Reusable calculation and classification code belongs in `tools/`; API-key helpers belong in `utils/`. Authentication code is grouped under `auth/`, SQLAlchemy models and database setup under `database/`, and browser assets under `frontend/`. Tests currently consist of the authentication smoke test at `test_auth.py` and the manual API client in `tests/send_query.py`.

## Build, Test, and Development Commands

- `python -m venv .venv && source .venv/bin/activate` creates an isolated environment. Do not add virtual-environment files to source control.
- `pip install -r requirements.txt` installs runtime dependencies; `./build.sh` performs the same installation for deployment.
- `cp .env.example .env` creates local configuration. Set at least `GEMINI_API_KEY` and a strong `SECRET_KEY`.
- `uvicorn main:app --reload` starts the development server at `http://localhost:8000`; API documentation is available at `/docs`.
- `python -m pytest -q` runs retrieval, routing, schema, latency, and fallback-audit tests.
- `python test_auth.py` runs the manual authentication smoke test and may create or update `ai_tutor.db`.
- `python -m evaluation.run_ragas` runs the credentialed Ragas faithfulness gate.
- `python -m evaluation.ab_test` compares baseline and candidate retrieval configurations without API calls; add `--live` to compare Gemini judges.
- `python tests/send_query.py` exercises the chat API against an already-running server; update its endpoint or credentials when protected routes change.

## Coding Style & Naming Conventions

Follow PEP 8 with four-space indentation. Use `snake_case` for modules, functions, and variables; `PascalCase` for classes; and uppercase names for constants. Add type hints to public interfaces and keep route handlers thin by placing domain logic in agents, services, or tools. No formatter or linter is configured, so keep imports grouped, remove trailing whitespace, and match surrounding style.

## Testing Guidelines

Keep tests under `tests/`, named `test_*.py`, and run them with pytest. The retrieval benchmark enforces a local p95 below 200 ms. Use temporary databases, fake search providers, and fake LLMs; live Gemini calls belong only in explicit evaluation scripts.

## Commit & Pull Request Guidelines

History uses short, imperative summaries such as `update readme` and `added langraph`; keep subjects concise and describe one logical change per commit. Pull requests should explain behavior changes, list verification commands, link related issues, and include screenshots for edits under `frontend/`. Call out new environment variables or database changes explicitly.

## Security & Configuration

Never commit `.env`, database files, uploaded content, or real credentials from `api_keys/`. Keep `.env.example` limited to placeholder values, and restrict CORS and OAuth settings before production deployment.
