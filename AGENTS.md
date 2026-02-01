# Repository Guidelines

## Project Structure & Module Organization
- `app/` holds the FastAPI gateway code (entry point: `app/main.py`), with submodules like `providers/`, `routes/`, `services/`, and `utils/` as described in `README.md`.
- `config/`, `cookies/`, and `logs/` are runtime directories used by Docker and local runs.
- `docs/` contains architecture, API spec, configuration examples, and deployment notes.
- This workspace snapshot includes only `docs/` and top-level docs; if source code isn’t present, follow the structure documented in `README.md` when adding it.

## Build, Test, and Development Commands
- `docker-compose up -d`: build and run the gateway in the background (recommended in `README.md`).
- `curl http://localhost:8022/health`: verify the service is healthy.
- `curl -X POST http://localhost:8022/admin/config/reload -H "Authorization: Bearer <token>"`: reload config without restart.
- If running directly (when `app/` and `requirements.txt` exist), use `python -m app.main` after installing dependencies.

## Coding Style & Naming Conventions
- Python code uses 4-space indentation and type hints where practical.
- Modules are grouped by concern: `routes/` for HTTP endpoints, `providers/` for model backends, and `services/` for shared logic.
- Naming: snake_case for functions/vars, PascalCase for classes (e.g., `GeminiProvider`).
- No formatter or linter is specified in this snapshot; keep changes consistent with existing files when present.

## Testing Guidelines
- There are no tests in this snapshot. If you add tests, place them in `tests/` and name them `test_*.py` (pytest-compatible).
- Prefer coverage of provider routing, authentication middleware, and streaming responses.

## Commit & Pull Request Guidelines
- No Git history is available in this workspace, so no commit convention can be inferred.
- Suggested: use clear, imperative messages (e.g., “Add Gemini provider reload”) or Conventional Commits (`feat:`, `fix:`).
- PRs should include: scope summary, how to run/verify, and any config or cookie changes required for manual testing.

## Security & Configuration Tips
- Never commit real tokens or cookies; use placeholders and reference `docs/config-examples.md`.
- Keep `config.yaml` and `cookies/*.json` out of version control unless explicitly intended.

## Agent Skills Index
- Skills overview and decision tree: `agent-rules/skills/README.md`.
- Superpowers usage guide: `agent-rules/skills/superpowers-guide.md`.
- Planning-with-files workflow: `agent-rules/skills/planning-with-files-guide.md`.
- Frontend design workflow: `agent-rules/skills/frontend-design-guide.md`.
- Ralph Loop iteration workflow: `agent-rules/skills/ralph-loop-guide.md`.
