# M1 — 数据地基（已关闭）

**状态：** 已关闭（CLOSED）  
**数据源：** 仅 Longbridge OpenAPI  
**市场：** CN、HK、US  

本文记录 M1 **交付了什么**、**刻意不做了什么**。  
是收口说明，不是产品路线图。

---

## 目标

建立正确、最小的数据地基：

- PostgreSQL 为唯一 Source of Truth  
- 内部证券身份使用 `instrument_id`  
- 自 Longbridge **幂等**同步标的与日线  
- 研究代码有只读入口，不直接碰 Provider  

---

## 已交付

### Schema（baseline `0001`）

| 表 | 作用 |
| --- | --- |
| `instrument` | 规范证券主数据 |
| `instrument_symbol_map` | Provider 符号 → `instrument_id` |
| `daily_price` | 日线 OHLCV，主键 `(instrument_id, trade_date)` |
| `provider_history_symbol` | 长桥历史 K **月度标的配额**本地账本 |
| `data_sync_log` | 同步任务审计 |

#### `instrument`

- 字段：`id`、`symbol`、`market`、`exchange`、`name_cn`、`name_en`、`name_hk`、`currency`、时间戳  
- 唯一：`(market, symbol)`  
- 索引：`market`、`exchange`  

#### **明确不进** `instrument` 的字段

| 已删 / 从未落库 | 原因 |
| --- | --- |
| `asset_type` | list/static 无可靠类型，禁止瞎填 |
| `list_date` / `delist_date` | SDK 无法稳定提供上市生命周期 |
| `status` | 无可靠上游生命周期状态 |

#### `daily_price`

- `open` / `high` / `low` / `close` / `volume` / `amount`（长桥 `turnover`）  
- `source` = **`longbridge:forward`**  
- 请求约定：`Period.Day`、**ForwardAdjust**、仅 Intraday  
- **不**单独建复权类型列  

#### `provider_history_symbol`

- 长桥历史 K 按 **自然月内唯一标的** 计配额  
- 官方 **无** 剩余额度 API，也 **无** 服务端「已查列表」  
- 本表为成功请求后的 **本地估计**  
- 唯一：`(provider, provider_symbol, year_month)`  

---

### Pipeline / CLI

| 命令 | 作用 |
| --- | --- |
| `devbox run sync-instruments` | `security_list` + `static_info` → 主数据 + 映射 |
| `devbox run sync-daily-prices -- …` | 历史 K 线 → `daily_price` |
| `devbox run list-history-symbols` | 查看本月配额账本中的标的 |

`sync-daily-prices` 常用参数：

- `--start` / `--end` — 可选；**都省略时默认最近 10 个自然日**（UTC 今日为 end）  
- `--days N` — 省略 start/end 时的窗口长度（默认 10，含首尾）  
- `--markets` / `--symbols` / `--limit`  
- `--max-new-symbols` — 限制本 run 新占配额的标的数  
- `--only-already-queried` — 优先本月账本中已有标的  

入库前做 **OHLC 简单校验**（`high>=low`、高低包住开收、价格>0、量/额非负）；不通过则跳过并打日志，不写库。

参数写在 `--` 之后（Devbox 通过 `"$@"` 转发）。

覆盖策略：**按需（demand-driven）**——研究池 / 自选 / 已查过的标的。  
不要假设在长桥配额下可以随便刷全市场历史日线。

---

### 应用层只读 API（M1 收口时一并纳入）

```python
from catallax.services.prices import PriceQueryService

PriceQueryService(session).get_prices(
    instrument_id=...,
    start_date=...,
    end_date=...,
)

PriceQueryService(session).get_prices_by_symbol(
    market="US",
    symbol="AAPL",
    start_date=...,
    end_date=...,
)
```

- 只读 PostgreSQL，**不**调用 Longbridge  
- 内部解析为 `instrument_id`  
- 按 `trade_date` **升序**返回  

---

### Provider 层要点

- 身份 / 名称 / 交易所 / 币种来自 `security_list` + `static_info`  
- 交易所必须来自 `static_info`（仅 region `US` **不是**交易所）  
- `timestamp` 按市场时区转为 `trade_date`（US / CN / HK）  
- 历史 K 按窗口拉取（单次约 ≤900 自然日）  
- 标的间默认节流约 0.6s（限速余量）  

---

## 明确非目标（设计如此）

- 周 / 月 / 年 K 表（需要时从日线聚合）  
- Historical Universe / 幸存者无偏成员集（阻塞：无生命周期数据）  
- 独立 OHLC 校验模块  
- 产品化「默认近 5～10 个交易日」增量  
- 日频估值面板（见 M2 决策文档）  
- 三大报表、SEC EDGAR、因子、回测  

---

## 测试

- 单元：符号解析、K 线辅助、注入 Provider  
- 集成（PostgreSQL）：主数据、日线、同步管线、PriceQueryService  
- CI **不**访问真实 Longbridge  

---

## 相关文档

- [`docs/m2_valuation.md`](m2_valuation.md) — M2.0 决策；M2.1 日频估值 **阻塞**  
- `AGENTS.md` — 持续工程规则（报表 PIT、禁止伪造历史等）  

---

## 非阻塞后续（不重开 M1）

1. ~~入库 OHLC 校验~~ — 已做（跳过非法 bar）  
2. ~~默认增量日期~~ — 已做（`--days`，默认 10 自然日）  
3. 稀疏估值观测（仅当产品需要长桥周/月 PE 历史——**不要**做成 `daily_valuation`）  
