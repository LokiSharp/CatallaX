# CatallaX Agent Rules

CatallaX is a medium/low-frequency quantitative research and portfolio platform.

Core rules:

1. PostgreSQL is the source of truth.
2. Devbox manages system-level development tools (CLI binaries such as PostgreSQL, Ruff, Pyright, uv, git). Prefer packaging those via Devbox rather than PyPI wheels or OS-specific binary hacks (no patchelf scripts).
3. uv manages Python package dependencies (importable libraries and Python-only tools such as pytest).
4. Do not introduce infrastructure unless required.
5. Keep the architecture simple.
6. Full static typing is mandatory: every function/method must annotate all parameters and the return type; prefer precise types over `Any`. Enforced by Ruff `ANN` and Pyright `strict`.
7. Provider-specific code must eventually stay inside the data layer.
8. Strategies must never access external APIs directly.
9. Internal securities will eventually use instrument_id rather than provider symbols.
10. Database writes must be designed to become idempotent.
11. Data correctness is more important than performance.
12. Point-in-time correctness and survivorship bias will be critical future requirements.
13. Do not implement HFT or intraday architecture.
14. Database schema changes must use Alembic migrations.
    During active development, prefer **new incremental migrations** (0002, 0003, …)
    over editing or re-squashing the baseline. Squash/merge migration history only
    when the user explicitly asks.
15. Critical database behavior must eventually have PostgreSQL integration tests.
16. Do not implement future milestones unless explicitly requested.
17. Git hooks live in `.githooks/` (`core.hooksPath`, configured by `devbox run setup`):
    - `commit-msg`: Conventional Commits subjects (`feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert`).
    - `pre-commit`: `devbox run precommit` (ruff check + format --check + pyright).
    - `pre-push`: `devbox run check` (precommit + pytest).
    Do not use `--no-verify` / `CATALLAX_SKIP_HOOKS=1` unless explicitly necessary.
18. GitHub Actions CI (`.github/workflows/ci.yml`) must stay aligned with local gates: Devbox install, `uv sync`, then ruff / format / pyright / pytest.
