# CatallaX Agent 规则

CatallaX 是中低频量化研究与组合平台。

核心规则：

1. PostgreSQL 是唯一 Source of Truth（数据真相源）。
2. Devbox 管理**系统级**开发工具（CLI 二进制：PostgreSQL、Ruff、Pyright、uv、git 等）。优先用 Devbox 打包，不要用 PyPI 轮子或 OS 专用二进制黑科技（例如 patchelf 脚本）。
3. uv 管理 **Python 包依赖**（可 import 的库，以及 pytest 等 Python 工具）。
4. 非必要不引入基础设施。
5. 架构保持简单。
6. **强制全量静态类型**：每个函数/方法的参数与返回值都必须标注类型；优先精确类型，避免 `Any`。由 Ruff `ANN` 与 Pyright `strict` 强制执行。
7. Provider 专有代码最终必须留在数据层内。
8. 策略层**禁止**直接访问外部 API。
9. 内部证券最终使用 `instrument_id`，而不是 Provider 符号。
10. 数据库写入必须设计为可幂等。
11. 数据正确性优先于性能。
12. 时点正确性（point-in-time）与幸存者偏差将是关键的未来要求。
13. 不实现 HFT 或日内交易架构。
14. 数据库 schema 变更必须走 Alembic migration。  
    活跃开发阶段优先使用**新的增量 migration**（`0002`、`0003`…），不要改写或重压 baseline。  
    **仅当用户明确要求时**才 squash / 合并 migration 历史。
15. 关键数据库行为最终应有 PostgreSQL 集成测试。
16. 除非用户明确要求，**不要**实现未来 milestone。
17. Git hooks 位于 `.githooks/`（`core.hooksPath`，由 `devbox run setup` 配置）：
    - `commit-msg`：Conventional Commits 主题  
      （`feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert`）
    - `pre-commit`：`devbox run precommit`（ruff check + format --check + pyright）
    - `pre-push`：`devbox run check`（precommit + pytest）  
    非必要不要使用 `--no-verify` / `CATALLAX_SKIP_HOOKS=1`。
18. GitHub Actions CI（`.github/workflows/ci.yml`）必须与本地门禁对齐：Devbox 安装、`uv sync`，然后 ruff / format / pyright / pytest。
19. **禁止伪造历史时间序列**（例如用今日 PE 回填过去日期）。  
    若 Provider 只有快照或非日频历史，应如实建模或阻塞功能——**不要**落假的日频面板。
20. 未来财务报表表（利润表 / 资产负债表 / 现金流量表）必须至少包含  
    `report_period`、`announcement_date`、`available_date`。  
    历史读取必须强制：`available_date <= as_of_date`。  
    在用户明确要求的 milestone 之前，**不要**实现这些表。
21. Historical Universe 在缺乏可靠生命周期 / 成分历史之前**阻塞**；  
    禁止为幸存者无偏宇宙伪造 list/delist/status。
