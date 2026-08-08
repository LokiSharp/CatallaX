# CatallaX

量化研究与组合平台（中低频）

License: [MIT](LICENSE)

## 当前状态

**M1：已关闭** · **M2.0：已决策** · **M2.1：阻塞**

### M1 — 数据地基（已关闭）

证券主数据 + 长桥标的同步 + **日线 OHLCV**（`daily_price`，幂等）。

完整收口说明：[`docs/m1_data_foundation.md`](docs/m1_data_foundation.md)。

- **数据源：** 仅 Longbridge OpenAPI（`Period.Day`、**ForwardAdjust**、Intraday）
- **市场：** `CN`、`HK`、`US`
- **日线 `source`：** `longbridge:forward`
- **历史 K 配额账本：** `provider_history_symbol` + `devbox run list-history-symbols`
- **价格只读 API：** `catallax.services.prices.PriceQueryService`（仅 PostgreSQL）

非阻塞后续（不重开 M1）：OHLC 校验、默认近 5～10 日增量产品化。

### M2 — 估值（窄切片）

| 切片 | 状态 |
| --- | --- |
| **M2.0** 设计 / Provider 语义 | **完成** — 见 [`docs/m2_valuation.md`](docs/m2_valuation.md) |
| **M2.1** 历史 `daily_valuation` | **阻塞**（Provider 能力不足） |

长桥 `FundamentalContext.valuation_history` 返回 **真实** PE 历史，但频度是 **周/月** 而非日；PB/PS 常缺失。  
**禁止** 用今日快照回填历史交易日来假装日频估值。

```text
M2.1 historical daily valuation blocked by provider capability.
```

## 前置条件

- [Devbox](https://www.jetify.com/devbox)
- [Longbridge OpenAPI](https://open.longbridge.com/) 凭证

## 环境搭建

```bash
devbox shell
devbox run setup
devbox run db-start
devbox run db-init
devbox run migrate
devbox run check
```

将 `.env.example` 复制为 `.env` 并填写长桥凭证：

```bash
CATALLAX_LONGBRIDGE_APP_KEY=...
CATALLAX_LONGBRIDGE_APP_SECRET=...
CATALLAX_LONGBRIDGE_ACCESS_TOKEN=...
```

`devbox run setup` 会把 `core.hooksPath` 指到 [`.githooks/`](.githooks)：

| Hook | 检查 |
| --- | --- |
| `commit-msg` | [Conventional Commits](https://www.conventionalcommits.org/) 主题行 |
| `pre-commit` | Ruff lint + format `--check` + Pyright（`devbox run precommit`） |
| `pre-push` | 全量门禁（`devbox run check`，含 pytest） |

示例：`feat(db): ...`、`fix(config): ...`、`chore: ...`。

紧急跳过：`CATALLAX_SKIP_HOOKS=1 git commit ...` 或 `git commit --no-verify`。

## CI

GitHub Actions（`.github/workflows/ci.yml`）在 push/PR 到 `main` 时与本地门禁对齐：

`ruff check` · `ruff format --check` · `pyright` · `pytest`

工具链经 Devbox 安装，与本地一致。

## 常用命令

| 命令 | 作用 |
| --- | --- |
| `devbox run setup` | uv 同步依赖；缺失则创建 `.env`；安装 git hooks |
| `devbox run precommit` | lint + format 检查 + 类型检查 |
| `devbox run db-start` | 本地 PostgreSQL，端口 **15432** |
| `devbox run db-stop` | 停止本地 PostgreSQL |
| `devbox run db-init` | 创建角色 `catallax`、库 `catallax_dev` / `catallax_test`（幂等） |
| `devbox run db-reset` | 删除并重建 `catallax_dev` 后 migrate（仅本地） |
| `devbox run db-check` | 应用 → PostgreSQL 连通性冒烟 |
| `devbox run migrate` | 执行 Alembic 迁移 |
| `devbox run sync-instruments` | 经长桥同步 CN/HK/US 标的 |
| `devbox run sync-daily-prices -- --start … --end …` | 同步日线（`--start`/`--end` 必填；参数在 `--` 后） |
| `devbox run list-history-symbols` | 列出本月历史 K 配额账本中的标的 |
| `devbox run test` | 运行 pytest |
| `devbox run lint` | Ruff check |
| `devbox run format` | Ruff format |
| `devbox run typecheck` | Pyright |
| `devbox run check` | lint + format 检查 + 类型检查 + 测试 |

## 技术栈

- Python 3.14+
- Devbox
- uv
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- Longbridge OpenAPI
- pytest
- Ruff
- Pyright
- Pydantic Settings
