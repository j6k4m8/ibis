# Ibis Backend

FastAPI service for notes, videos, and collaboration.

## Migrations

Run migrations:

```bash
uv run alembic upgrade head
```

Create a new migration (after editing models):

```bash
uv run alembic revision --autogenerate -m "describe change"
```
