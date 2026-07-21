# OpenAPI docs workflow Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update agent rules so Chinese OpenAPI Specs are the daily fact source, with a glossary-driven bilingual workflow and summary-then-confirm gate — without migrating API Reference pages yet.

**Architecture:** Phase 1 is documentation-only. Rewrite `AGENTS.md` to match the approved design; add root `glossary.zh-en.md` with product terms, Spec internal→external names, and page slug registry. Leave `docs.json` OpenAPI embedding and tag MDX pages untouched.

**Tech Stack:** Mintlify MDX docs repo; OpenAPI 3 JSON under `openapi/`; agent rules in `AGENTS.md`.

## Global Constraints

- Phase 1 scope only: `AGENTS.md` + `glossary.zh-en.md` (plus this plan already written).
- Do **not** remove `docs.json` `"openapi"` groups.
- Do **not** create `zh/api-reference/{service}/*.mdx` tag pages.
- Do **not** delete `openapi/en/`.
- Site default language remains `en`.
- Agent writing default remains Chinese-first for MDX.
- Prefer existing AGENTS product terms over conflicting Spec English tags when seeding glossary (e.g. 理财账户 → **Finance account**, not Spec’s “Wealth Management Account”).
- Follow design: `docs/superpowers/specs/2026-07-21-openapi-docs-workflow-design.md`.

---

### Task 1: Rewrite `AGENTS.md`

**Files:**
- Modify: `AGENTS.md`
- Reference: `docs/superpowers/specs/2026-07-21-openapi-docs-workflow-design.md`

**Interfaces:**
- Consumes: Locked decisions from the design (Chinese Spec fact source; glossary path; summary gate; target IA; phase-1 limits)
- Produces: Agent-facing rules that Task 2’s glossary is linked from

- [ ] **Step 1: Replace “Source of truth for APIs”** with content equivalent to:

```markdown
## Source of truth for APIs

Daily fact source for endpoint docs: the **Chinese** OpenAPI Specs in this repo:

- `openapi/mc-account.json`
- `openapi/mc-trade.json`
- `openapi/mc-risk.json`
- `openapi/mc-aggregator.json`

These Specs are the `@OpenApiPermission`-filtered public subset. Prefer them over scanning sibling `mc-*` repos for routine edits.

Hand-written MDX is the reader-facing deliverable. Target state: API Reference pages are hand-written and `docs.json` does **not** embed Specs via `"openapi"`. Until that migration ships, `docs.json` may still temporarily reference Spec files — follow the repo as it is; do not remove those entries unless the user asks to start migration.

Sibling-repo / `@OpenApiPermission` checks are reserved for:

- Suspicious or incomplete Specs
- Explicit export validation requests

Annotation definition (for validation only): `com.mc.account.api.openapi.annotation.OpenApiPermission` in `mc-account`. Typical controller locations: `**/web/openapi/**` under `mc-*-service` modules.
```

- [ ] **Step 2: Insert new section after Source of truth** titled `OpenAPI Spec → docs workflow` covering:

1. Maintainer exports latest Chinese Spec into `openapi/mc-*.json`
2. Agent diffs Specs and writes a **change summary** (required fields from design §4)
3. **No MDX/nav edits** until user confirms the summary
4. After confirm: update `glossary.zh-en.md` if needed → edit `zh/` → sync English via glossary
5. Target page split: service group + one page per **external** tag; paths like `zh/api-reference/{service}/{slug}.mdx`
6. Phase 1 note: tag pages may not exist yet; unless user asks to migrate, limit follow-up edits to applicable prose and note pending migration
7. Mandatory link/reference to `glossary.zh-en.md` for naming and English sync
8. Reader copy must use **external** names only (never raw internal Spec tags)

- [ ] **Step 3: Keep Terminology table**; add a one-line pointer that fuller zh↔en and internal→external mappings live in `glossary.zh-en.md`. Do not delete the short Prefer/Avoid table.

- [ ] **Step 4: Adjust Bilingual workflow** — after step 2 (zh first), add: consult `glossary.zh-en.md` before translating; write new renderings back to the glossary; keep technical identifiers untranslated.

- [ ] **Step 5: Replace Quality checklist** with:

```markdown
## Quality checklist

Before finishing a docs task:

- [ ] Facts checked against the latest Chinese Spec under `openapi/` (or the change is non-endpoint prose)
- [ ] For Spec-driven API changes: change summary produced and user-confirmed before MDX edits
- [ ] External naming via `glossary.zh-en.md` (no raw internal Spec tags in reader copy)
- [ ] Chinese page updated first; English synced via glossary when both exist
- [ ] Frontmatter has `title` and `description`
- [ ] Code blocks have language tags; no real secrets
- [ ] Internal links are root-relative and locale-correct (`/zh/...` vs `/...`)
- [ ] (After API Reference migration) new pages added to both language trees in `docs.json` when applicable
- [ ] Site default language remains `en`
```

- [ ] **Step 6: Verify** — read full `AGENTS.md`; confirm About / Style / Mintlify components / Content boundaries still present and coherent; confirm no instruction to scan sibling repos on every edit; confirm no instruction to migrate `docs.json` in phase 1.

- [ ] **Step 7: Commit** (only if user asked to commit; otherwise stop and report)

```bash
git add AGENTS.md
git commit -m "$(cat <<'EOF'
docs: point agents at Chinese OpenAPI Specs as fact source

EOF
)"
```

---

### Task 2: Create `glossary.zh-en.md`

**Files:**
- Create: `glossary.zh-en.md`
- Reference: `AGENTS.md` terminology; `openapi/mc-*.json` and `openapi/en/mc-*.json` tags

**Interfaces:**
- Consumes: Product terms from `AGENTS.md`; tag pairs from Specs; design §3 table shapes
- Produces: Lookup tables agents must use for naming and English sync

- [ ] **Step 1: Create file** with short intro (purpose, when to update, link from `AGENTS.md`) and **three tables**.

- [ ] **Step 2: Seed Table 1 — Product / docs terms (zh ↔ en)** at minimum:

| Chinese | English | Notes |
| --- | --- | --- |
| MC Markets OpenAPI / MC OpenAPI | MC Markets OpenAPI / MC OpenAPI | Prefer full name on first mention |
| Access Key / Secret Key（AK/SK） | Access Key / Secret Key (AK/SK) | Not API token / Bearer (except warnings) |
| API 网关 | API Gateway | |
| 资金账户 | Fund account | Not finance account |
| 理财账户 | Finance account | Prefer over Spec en “Wealth Management Account” |
| 闪兑 | Flash conversion | |
| 储备金证明（PoR） | Proof of Reserves (PoR) | |
| 币种 | Symbol / Currency | Prefer consistency with endpoint pages; Spec tag en uses Currency |
| `READ` / `TRADE` / `WITHDRAW` | `READ` / `TRADE` / `WITHDRAW` | Keep as-is |

- [ ] **Step 3: Seed Table 2 — Spec internal → external**

Include the pattern example even if not present in current Specs:

| Spec tag (internal) | External Chinese | English | Status |
| --- | --- | --- | --- |
| 业务前端-交易 | 交易 | Trading | example / when seen |

For current Spec tags that are already external-shaped, map identity rows (internal = external) so lookups always hit:

| Spec tag (internal) | External Chinese | English | Status |
| --- | --- | --- | --- |
| MLP 账户 | MLP 账户 | MLP account | confirmed |
| 理财账户 | 理财账户 | Finance account | confirmed |
| 交易 | 交易 | Trading | confirmed (use Trading; risk Spec used “Trading”, account/trade used “Trade” — standardize on **Trading** for the tag label) |
| 币种 | 币种 | Currency | confirmed |
| 资金账户 | 资金账户 | Fund account | confirmed |
| 汇率 | 汇率 | Exchange rate | confirmed |
| 成交订单 | 成交订单 | Deal orders | confirmed |
| 资金费历史 | 资金费历史 | Funding fee history | confirmed |
| 交易账户 | 交易账户 | Trading account | confirmed |
| 订单 | 订单 | Orders | confirmed |
| 成交 | 成交 | Deals | confirmed |
| 资金费率 | 资金费率 | Funding rate | confirmed |
| 行情数据 | 行情数据 | Market data | confirmed (prefer over Spec “Market Data API”) |

Mark uncertain public suitability:

| Spec tag (internal) | External Chinese | English | Status |
| --- | --- | --- | --- |
| App 全局搜索 | 待确认 | 待确认 | 待确认 — may be too app-internal for public docs |

- [ ] **Step 4: Seed Table 3 — Page title / slug registry** (service + slug; note collisions for 交易 across account/trade/risk — use service-prefixed slugs where needed):

| External Chinese | English title | slug | service |
| --- | --- | --- | --- |
| MLP 账户 | MLP account | `mlp-account` | account |
| 理财账户 | Finance account | `finance-account` | account |
| 交易 | Trading | `trading` | account |
| 币种 | Currency | `currency` | account |
| 资金账户 | Fund account | `fund-account` | account |
| 汇率 | Exchange rate | `exchange-rate` | account |
| 成交订单 | Deal orders | `deal-orders` | account |
| 资金费历史 | Funding fee history | `funding-fee-history` | account |
| App 全局搜索 | 待确认 | 待确认 | account |
| 交易 | Trading | `trading` | trade |
| 交易账户 | Trading account | `trading-account` | trade |
| 订单 | Orders | `orders` | trade |
| 成交 | Deals | `deals` | trade |
| 交易 | Trading | `trading` | risk |
| 资金费率 | Funding rate | `funding-rate` | risk |
| 行情数据 | Market data | `market-data` | aggregator |

Note under the table: same slug `trading` under different `{service}/` directories is OK; do not flatten across services.

- [ ] **Step 5: Verify** — file at repo root; three tables present; `AGENTS.md` references `glossary.zh-en.md`; App 全局搜索 left 待确认; 理财账户 English is Finance account.

- [ ] **Step 6: Commit** (only if user asked to commit; otherwise stop and report)

```bash
git add glossary.zh-en.md
git commit -m "$(cat <<'EOF'
docs: add zh-en glossary for Spec and MDX naming

EOF
)"
```

---

### Task 3: Sanity check against design

**Files:**
- Read: `AGENTS.md`, `glossary.zh-en.md`, `docs/superpowers/specs/2026-07-21-openapi-docs-workflow-design.md`
- Do not modify: `docs.json`, `openapi/**` (except if accidentally touched — revert)

- [ ] **Step 1: Confirm phase-1 success criteria**
  - Agents treat Chinese Specs as daily fact source
  - Spec-driven work defaults to summary-then-confirm
  - Glossary exists and is required for naming/translation
  - No API Reference migration happened

- [ ] **Step 2: `git status`** — only expected files changed (`AGENTS.md`, `glossary.zh-en.md`; plan/spec docs if included earlier)

- [ ] **Step 3: Report to user** — what changed; list 待确认 glossary rows; remind Phase 2 is separate

---

## Spec coverage check

| Design requirement | Task |
| --- | --- |
| Chinese Spec as fact source | Task 1 |
| Hand-written MDX target; no phase-1 nav migration | Task 1 + Task 3 |
| glossary.zh-en.md with 3 tables + internal→external | Task 2 |
| Summary-then-confirm workflow | Task 1 |
| Bilingual + glossary write-back | Task 1 |
| Checklist updates | Task 1 |
| openapi/en deprecated for daily use (not deleted) | Task 1 |
| Seed current tags + 待确认 | Task 2 |
