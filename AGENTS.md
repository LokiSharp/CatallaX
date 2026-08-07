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
15. Critical database behavior must eventually have PostgreSQL integration tests.
16. Do not implement future milestones unless explicitly requested.
