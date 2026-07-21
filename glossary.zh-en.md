# MC Markets OpenAPI — zh↔en glossary

Lookup tables for bilingual docs maintenance. Agents and maintainers use this file when writing or syncing MDX, mapping Spec tags to reader-facing names, and registering page titles and slugs.

**When to update:** Before or with any MDX edit that introduces new product terms, Spec tags, or API Reference pages. After Chinese Spec exports, check whether new tags need rows here before editing pages.

Referenced from [`AGENTS.md`](AGENTS.md) — do not duplicate these tables inline in agent rules.

## Table 1 — Product / docs terms (zh ↔ en)

| Chinese | English | Notes |
| --- | --- | --- |
| MC Markets OpenAPI / MC OpenAPI | MC Markets OpenAPI / MC OpenAPI | Prefer full name on first mention |
| Access Key / Secret Key（AK/SK） | Access Key / Secret Key (AK/SK) | Not API token / Bearer (except warnings) |
| `X-Nonce` | `X-Nonce` | New per request; **UUID v4** or ≥32 hex (`0-9a-fA-F`); replay-scoped per Access Key (~11 min default); must match string to sign exactly |
| API 网关 | API Gateway | |
| 资金账户 | Fund account | Not finance account |
| 理财账户 | Finance account | Prefer over Spec en “Wealth Management Account” |
| 金库账户 | Vault account | Reader-facing name for Spec tag MLP账户 / path segment `mlp`; keep `MLP_*` enums untranslated |
| 闪兑 | Flash conversion | |
| 储备金证明（PoR） | Proof of Reserves (PoR) | |
| 币种 | Symbol / Currency | Prefer consistency with endpoint pages; Spec tag en uses Currency |
| `READ` / `TRADE` / `WITHDRAW` | `READ` / `TRADE` / `WITHDRAW` | Keep as-is |
| 遍历 | iterate / iterate through | Not 遗历; use when translating pagination “iterate” |

## Table 2 — Spec internal → external

| Spec tag (internal) | External Chinese | English | Status |
| --- | --- | --- | --- |
| 业务前端-交易 | 交易 | Trading | example / when seen |
| MLP账户 | 金库账户 | Vault account | confirmed (Spec tag still MLP账户; do not use “MLP 账户” in reader copy) |
| 理财账户 | 理财账户 | Finance account | confirmed |
| 交易 | 交易 | Trading | confirmed (use Trading; risk Spec used “Trading”, account/trade used “Trade” — standardize on **Trading** for the tag label) |
| 币种 | 币种 | Currency | confirmed |
| 资金账户 | 资金账户 | Fund account | confirmed |
| 汇率 | 汇率 | Exchange rate | confirmed |
| 成交订单服务 | 成交订单 | Deal orders | confirmed |
| 资金费历史记录 | 资金费历史 | Funding fee history | confirmed |
| 交易账户 | 交易账户 | Trading account | confirmed |
| 订单 | 订单 | Orders | confirmed |
| 成交 | 成交 | Deals | confirmed |
| 资金费率 | 资金费率 | Funding rate | confirmed |
| 行情数据 | 行情数据 | Market data | confirmed (prefer over Spec “Market Data API”) |

## Table 3 — Page title / slug registry

| External Chinese | English title | slug | service |
| --- | --- | --- | --- |
| 金库账户 | Vault account | `vault-account` | account |
| 理财账户 | Finance account | `finance-account` | account |
| 交易 | Trading | `trading` | account |
| 币种 | Currency | `currency` | account |
| 资金账户 | Fund account | `fund-account` | account |
| 汇率 | Exchange rate | `exchange-rate` | account |
| 成交订单 | Deal orders | `deal-orders` | account |
| 资金费历史 | Funding fee history | `funding-fee-history` | account |
| 交易 | Trading | `trading` | trade |
| 交易账户 | Trading account | `trading-account` | trade |
| 订单 | Orders | `orders` | trade |
| 成交 | Deals | `deals` | trade |
| 交易 | Trading | `trading` | risk |
| 资金费率 | Funding rate | `funding-rate` | risk |
| 行情数据 | Market data | `market-data` | aggregator |

**Note:** The slug `trading` appears under account, trade, and risk with the same value. That is OK — pages live at `zh/api-reference/{service}/trading.mdx` (and English mirrors). Do not flatten slugs across services.
