# CatallaX

Quantitative Research & Portfolio Platform

License: [MIT](LICENSE)

## Current Status

Milestone 0 / Development Environment

Python **3.14+**, Devbox, uv, and local PostgreSQL. No quant business logic yet.

## Prerequisites

- [Devbox](https://www.jetify.com/devbox)

## Environment Setup

```bash
devbox shell
devbox run setup
devbox run db-start
devbox run db-init
devbox run migrate
devbox run check
```

Copy `.env.example` to `.env` if you need local overrides (defaults work out of the box).

## Useful Commands

| Command | Purpose |
| --- | --- |
| `devbox run setup` | Sync Python deps with uv; create `.env` if missing |
| `devbox run db-start` | Start local PostgreSQL on port **15432** |
| `devbox run db-stop` | Stop local PostgreSQL |
| `devbox run db-init` | Create `catallax` role and `catallax_dev` (idempotent) |
| `devbox run db-reset` | Drop + recreate `catallax_dev`, then migrate (local only) |
| `devbox run db-check` | Smoke-test app → PostgreSQL connectivity |
| `devbox run migrate` | Run Alembic migrations |
| `devbox run test` | Run pytest |
| `devbox run lint` | Ruff check |
| `devbox run format` | Ruff format |
| `devbox run typecheck` | Pyright |
| `devbox run check` | lint + format check + typecheck + test |

## Tech Stack

- Python 3.14+
- Devbox
- uv
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- pytest
- Ruff
- Pyright
- Pydantic Settings
