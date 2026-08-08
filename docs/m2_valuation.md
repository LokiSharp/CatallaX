# M2 估值 — 设计决策

**状态：**  
- M2.0 语义决策：**完成**  
- M2.1 直接落长桥日频 `daily_valuation`：**阻塞**（能力不匹配）  
- **主路径（已拍板）：自算 PE/PB；长桥估值仅作验证**  

**日期：** 2026-08-09（策略更新：自算为主）  
**审查对象：** Longbridge OpenAPI SDK（`longbridge` ≥ 4.4.x）+ 已有 `daily_price`

---

## 已拍板策略

```text
权威估值 = f(日线价格, 带 PIT 的基本面)
长桥 valuation / valuation_history / calc_indexes = 校验与对照，不是 SoT
```

| 角色 | 来源 | 用途 |
| --- | --- | --- |
| **权威（SoT）** | `daily_price.close` + 历史 EPS/BPS 等（PIT） | 研究 / 因子 / 回测用的 PE、PB |
| **验证** | 长桥 `valuation_history`、`calc_indexes`、`valuation` | 抽查偏差、发现口径/bug，**不**当历史日频面板主源 |

禁止：

- 用今日长桥 PE 回填历史交易日  
- 无 PIT 基本面时「假装」已有历史日频估值  
- 把验证源与权威源混在同一列且不区分 `source`  

---

## 为什么不直接用长桥当日频估值主源

### API 性质

| API | 性质 |
| --- | --- |
| `static_info` / `calc_indexes` | **当前快照** |
| `FundamentalContext.valuation` | **当前快照** |
| `FundamentalContext.valuation_history` | **真实历史**，但实测多为 **周频（美）/ 月频（港）**，PB/PS 常缺 |

### 实盘探测摘要

| 符号 | PE 历史间隔 | PB/PS |
| --- | --- | --- |
| `AAPL.US` | ~7 日 | 常无 |
| `700.HK` | ~30 日 | 常无 |

→ 不适合作为 `(instrument_id, trade_date)` 的完整交易日估值面板。

---

## 自算路径（主路径）

### 公式（默认定义，实现时写死并测）

| 指标 | 定义 |
| --- | --- |
| PE_TTM | `close / eps_ttm`（`eps_ttm ≤ 0` 或缺失 → null） |
| PB | `close / bps`（`bps ≤ 0` 或缺失 → null） |

可选后续：PS_TTM、市值 = `close × shares`（需历史股本与口径）。

### 输入依赖

| 输入 | 已有？ | 要求 |
| --- | --- | --- |
| `close` | **有** `daily_price`（`longbridge:forward`） | 与基本面复权/股本口径要对齐 |
| `eps_ttm` / 报告期 EPS | **无历史表** | 必须带 `available_date`（及 report/announcement） |
| `bps` | **无历史表** | 同上 |

**当前阻塞点：** 不是公式，而是 **带 PIT 的历史 EPS/BPS 尚未入库**。

### 复权与口径（必须先约定再写库）

二选一写进实现与文档，禁止混用：

1. **前复权价 + 与之一致调整过的每股指标**，或  
2. **未复权价 + 当时股本/EPS**  

现阶段日线是 `longbridge:forward`，自算时要么：

- 基本面侧同步做一致调整，或  
- 明确「PE/PB 仅基于前复权价 + 未调整 EPS」的近似误差，并在验证中量化  

### 目标表（实现时再建，本次可仅设计）

```text
daily_valuation
  instrument_id
  trade_date
  pe_ttm          -- nullable
  pb              -- nullable
  -- 可选: ps_ttm, market_cap, shares
  source          -- 例如 catallax:computed:v1
  created_at / updated_at
  PK (instrument_id, trade_date)
```

语义：每个**有日线且当时已可得**基本面的交易日一行；中间 EPS 不变、价格变，PE 每天可变——**合法**，前提是 EPS 的 `available_date` 正确。

计算任务（未来）：

```text
for each trade_date:
  eps, bps = latest fundamentals where available_date <= trade_date
  pe, pb = f(close[trade_date], eps, bps)
  upsert daily_valuation source=catallax:computed:...
```

---

## 长桥验证路径（辅）

### 用途

- 对同一 `as_of` 附近，比较自算 PE 与长桥 PE（允许定义差：TTM 构成、diluted、调整）  
- 抽检异常跳变、单位错误、PIT bug  

### 落库建议（与权威分离）

```text
valuation_observation   # 稀疏，非交易日面板
  instrument_id
  as_of_date
  pe / pb / ps          -- 可空
  source                -- longbridge:fundamental_valuation_history
  PK (instrument_id, as_of_date, source)
```

或仅在校验脚本中临时拉取、不落库。  
**不要** 与 `daily_valuation`（`source=catallax:computed`）混成「无 source 区分的一张糊涂表」。

### 快照 API

`calc_indexes` / `static_info` / `valuation`：仅适合 **实时对照**，禁止当历史序列主源。

---

## 财务报表 PIT（强制，未来表）

所有 `income_statement` / `balance_sheet` / `cashflow_statement`（及派生 EPS/BPS 历史）至少：

- `report_period`  
- `announcement_date`  
- `available_date`  

读取：

```text
available_date <= as_of_date
```

---

## 分阶段实现顺序（建议）

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| M2.0 | 语义：长桥非日频主源；自算为主 | **完成** |
| M2.1a | 最小基本面：EPS/BPS + PIT 字段 + 同步 | **完成（部分）** — 见下 |
| M2.1b | 自算写入 `daily_valuation`（`source=catallax:computed:…`） | **阻塞** 至 `available_date` 可填充 |
| M2.1c | 长桥 `valuation_history` → 验证 | 未开始 |

### M2.1a 已实现

- 表 **`fundamental_period`**（migration `0002`）  
  - PK：`(instrument_id, period_end, source)`  
  - 字段：`period_label`, `fiscal_year`, `eps`, `bps`, `currency`,  
    `announcement_date`, `available_date`, `source`  
- 源：`longbridge:financial_report`（`FundamentalContext.financial_report`）  
- 解析季度标签 `Q1`–`Q4 YYYY`；合并 IS.EPS 与 BS.BPS  
- CLI：`devbox run sync-fundamentals -- --symbols AAPL --markets US`  
- **长桥当前不提供** `announcement_date` / `available_date` → 入库为 **NULL**（禁止瞎填）  
- `FundamentalPeriodRepository.latest_as_of(..., require_available_date=True)`  
  **默认只使用 available_date 非空且 `<= as_of` 的行**，避免误用无 PIT 数据算 PE  

因此：M2.1a 把「能拿到的历史 EPS/BPS」落库了，但 **PIT 安全的自算 PE/PB 仍须等到 available_date 有可靠来源**（另源补日期，或将来长桥补字段）。

基本面数据源：

- 长桥 `financial_report`：EPS/BPS + `period_end`（**无**可用日）— 已接  
- 美股 SEC EDGAR 等：可用于补 `available_date` — 未接  

---

## Historical Universe（M3）

仍 **阻塞**（无可靠 list/delist/status/成分历史）。与估值主路径独立。

---

## 下一步（需用户授权再编码）

1. **M2.1a：** 设计并落地最小「每股指标 / 报表切片」表 + PIT + 一个可测源的同步。  
2. **M2.1b：** 基于 `daily_price` 与上述指标计算 PE/PB → `daily_valuation`。  
3. **M2.1c：** 长桥历史 PE 抽样验证与偏差报告。  
