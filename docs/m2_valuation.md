# M2 估值 — 设计决策（M2.0）

**状态：** M2.0 决策完成 · **M2.1 历史 `daily_valuation` 阻塞**  
**日期：** 2026-08-09  
**审查对象：** Longbridge OpenAPI SDK（`longbridge` ≥ 4.4.x）

---

## M1

**已关闭。** Security Master、标的同步、日线、历史 K 配额账本均已落地。  
M1 剩余打磨（OHLC 校验、默认 5～10 日增量产品化）**不阻塞**收口。

---

## 问题：能否落「真正的历史日频估值」？

### 检查过的 API

| API | 上下文 | 性质 |
| --- | --- | --- |
| `QuoteContext.static_info` | 行情 | **当前快照**：股本、eps、bps、dividend_yield 等 |
| `QuoteContext.calc_indexes` | 行情 | **当前快照**：`PeTtmRatio`、`PbRatio`、`TotalMarketValue`、`DividendRatioTtm` 等 |
| `FundamentalContext.valuation` | 基本面 | **当前 / 丰富快照**（PE/PB/PS/股息等容器） |
| `FundamentalContext.valuation_history` | 基本面 | **真实历史序列**（主要为 PE，有时有 PB/PS） |

### 实盘探测（约 2026-08，有凭证）

| 符号 | PE 历史 | 采样间隔 | PB / PS 历史 |
| --- | --- | --- | --- |
| `AAPL.US` | 约 260 点 | **约 7 天（周频）** | **无** |
| `700.HK` | 约 60 点 | **约 30～31 天（月频）** | **无** |

结论：

1. 长桥通过 `valuation_history` **确实提供真实历史估值序列**，不是把今日 PE 回填到过去。  
2. 序列 **不是日频**。实测 PE 约为 **美股周频 / 港股月频**。  
3. 即使有 PE，**PB / PS 历史也经常缺失**。  
4. 该接口 **无** 历史市值 / 股本序列；`static_info` / `calc_indexes` 仅是 **当下快照**。  
5. 因此用 **`daily_valuation` + 交易日粒度** 承接该数据 **模型错误**。

### 禁止做法

- 用今日 `calc_indexes` / `static_info` 的 PE/PB **回填** 历史 `trade_date`  
- 把周频 PE 点伪装成「日 K」  
- 无来源却硬造流通市值、PCF 等字段  

---

## M2.1 决策

```text
M2.1 historical daily valuation blocked by provider capability.
```

中文含义：**M2.1 历史日频估值因 Provider 能力阻塞。**

- **阻塞：** 实现交易日面板式 `daily_valuation` + `sync_daily_valuation`  
- **并非永久封死：** 将来若产品需要，可做 **稀疏观测** 模型（见下，**本次不实现**）

### 未来候选模型（当前不实现）

若需要落库长桥 PE 历史：

```text
valuation_observation
  instrument_id
  as_of_date          -- 观测日历日（来自 timestamp）
  pe                  -- 可空
  pb                  -- 可空
  ps                  -- 可空
  source              -- 例如 longbridge:fundamental_valuation_history
  created_at / updated_at
  PK (instrument_id, as_of_date, source)  -- 或等价
```

语义：**不规则时间序列**，不是完整交易日历。消费方 **不得** 假设每个交易日一行。

若只要实时快照，应另表，例如  
`valuation_snapshot (instrument_id, observed_at, …)`，  
**禁止** 把快照写进历史行并挂上过去的 `trade_date`。

---

## 字段映射备忘（将来做观测表时）

| 长桥 | 是否采用 | 说明 |
| --- | --- | --- |
| `valuation_history` → PE 列表 | 是（未来） | 真实历史；周/月频 |
| `valuation_history` → PB/PS | 可选 | 经常为空 |
| `valuation` 快照 | 仅实时/研究 | 不是历史 |
| `calc_indexes` PE/PB/市值 | 仅实时 | 无日期维度 |
| `static_info` 股本/eps/bps | 实时 / 基本面快照 | 不是日频历史 |

---

## 时点正确性（财务报表 — 未来）

`daily_price` **不需要** `available_date`。

市场公开的估值 **观测点**（若将来存储）用观测日即可，它们不是会计报表。

**未来所有报表表**（`income_statement` / `balance_sheet` / `cashflow_statement`）**必须**至少包含：

- `report_period`  
- `announcement_date`  
- `available_date`  

历史读取 **必须** 满足：

```text
available_date <= as_of_date
```

本阶段 **不实现** 三大报表。

---

## Historical Universe（M3）

**暂缓 / 阻塞**：当前策略下无可靠的上市/退市/状态/成分历史。  
禁止为推进路线图伪造 Historical Universe。

---

## 下一步（仅建议）

1. 继续按需维护日线覆盖（配额账本）。  
2. 真正需要估值历史时：实现稀疏 `valuation_observation` + `FundamentalContext`，并做好限速。  
3. 或另选具备 **日频估值历史** 的数据源 / 用财报+价格自建——须单独决策。  
