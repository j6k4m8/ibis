# Ibis

Modern rewrite of the Ibis lesson annotation app.

## Features

- Login/register UI with local token persistence.
- Notes list + detail editing with history snapshot preview.
- Video link preview with YouTube embed support.
- Markdown editor with preview and timestamp tokens.
- Tags page with deep-linked filters.
- Tasks page that aggregates checklist items from notes.
- Persistent tasks with creation timestamps and completion toggles.

## Dev servers

All-in-one:

```bash
./scripts/dev.sh
```

The script loads a root `.env` file if present and exports variables for both services.

Backend:

```bash
cd backend
uv venv
uv pip install -e ".[dev]"
uv run uvicorn ibis_backend.app:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Tests

Backend:

```bash
cd backend
uv run pytest
```

Frontend:

```bash
cd frontend
npm run test
```

## Development Workflow

- Update `TODO.md` as features land.
- Add major features to a `## Features` section in this README.
- Add tests/docs when they add value.
- Commit frequently with clear, scoped messages.
