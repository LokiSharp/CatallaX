# CatallaX

Quantitative Research & Portfolio Platform

License: [MIT](LICENSE)

## Current Status

**Milestone 1.3 — AKShare Instrument Provider**

Security Master + `daily_price` schema, plus **instrument list sync** from
AKShare (CN/US) into `instrument` / `instrument_symbol_map` (idempotent).
Daily price download is **not** implemented yet (Milestone 1.4).

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

`devbox run setup` points `core.hooksPath` at [`.githooks/`](.githooks):

| Hook | Checks |
| --- | --- |
| `commit-msg` | [Conventional Commits](https://www.conventionalcommits.org/) subject |
| `pre-commit` | Ruff lint + format `--check` + Pyright (`devbox run precommit`) |
| `pre-push` | Full suite (`devbox run check`, includes pytest) |

Examples: `feat(db): ...`, `fix(config): ...`, `chore: ...`.

Emergency skip: `CATALLAX_SKIP_HOOKS=1 git commit ...` or `git commit --no-verify`.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs the same gates as local hooks on every push/PR to `main`:

`ruff check` · `ruff format --check` · `pyright` · `pytest`

Toolchain is installed via Devbox so CI matches the local environment.

## Useful Commands

| Command | Purpose |
| --- | --- |
| `devbox run setup` | Sync Python deps with uv; create `.env` if missing; install git hooks |
| `devbox run precommit` | Lint + format check + typecheck (same as pre-commit hook) |
| `devbox run db-start` | Start local PostgreSQL on port **15432** |
| `devbox run db-stop` | Stop local PostgreSQL |
| `devbox run db-init` | Create `catallax` role, `catallax_dev`, and `catallax_test` (idempotent) |
| `devbox run db-reset` | Drop + recreate `catallax_dev`, then migrate (local only) |
| `devbox run db-check` | Smoke-test app → PostgreSQL connectivity |
| `devbox run migrate` | Run Alembic migrations |
| `devbox run sync-instruments` | Sync CN/US instrument master from AKShare |
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
