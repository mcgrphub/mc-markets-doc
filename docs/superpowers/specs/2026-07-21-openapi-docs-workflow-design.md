# Design: OpenAPI Spec → hand-written MDX workflow

Date: 2026-07-21  
Status: Approved for implementation (phase 1: rules + glossary only)  
Repo: `mc-markets-doc`

## Goal

Change how MC Markets OpenAPI docs are maintained:

1. On API changes, export the latest **Chinese** OpenAPI Spec into `openapi/`.
2. Use those Specs as the **fact source** to update hand-written MDX.
3. Do **not** rely on Mintlify `"openapi"` direct embedding as the long-term API Reference UX (previous attempt was poor).
4. Phase 1 lands **rules and glossary only**; navigation migration and tag pages come later.

## Decisions (locked)

| Topic | Choice |
| --- | --- |
| API Reference end state | Hand-written MDX only; remove `docs.json` `"openapi"` groups (later) |
| Page split | By Spec service, then one MDX page per **external** tag |
| Spec locale | Chinese Spec only (`openapi/mc-*.json`) as daily fact source |
| English pages | Translate from Chinese MDX; do not require `openapi/en/` |
| Glossary | Independent `glossary.zh-en.md` at repo root |
| Glossary extras | Include Spec **internal → external** naming (e.g. `业务前端-交易` → `交易`) |
| Spec update process | Agent writes a change summary first; edit MDX only after user confirmation |
| Phase 1 scope | Update `AGENTS.md` + create `glossary.zh-en.md`; do not migrate pages or `docs.json` yet |

## Section 1 — Sources of truth and ownership

### Fact source (API facts)

- Authoritative for docs agents: Chinese Specs in
  - `openapi/mc-account.json`
  - `openapi/mc-trade.json`
  - `openapi/mc-risk.json`
  - `openapi/mc-aggregator.json`
- These Specs are already the `@OpenApiPermission`-filtered public subset.
- Agents must **not** scan sibling `mc-*` repos for `@OpenApiPermission` on every docs edit.
- Sibling-repo / annotation checks are reserved for:
  - suspicious or incomplete Specs
  - export validation when explicitly requested

### Deliverable (reader-facing)

- Hand-written MDX: edit `zh/` first, then sync English mirrors.
- Target state: no Mintlify `"openapi"` embedding in `docs.json`.
- Phase 1: **rules only** — do not change navigation or remove current `"openapi"` groups yet. Current auto-generated reference pages may remain until a dedicated migration task.

### Supporting assets

- `glossary.zh-en.md` — zh↔en terms + Spec internal→external names + slug/title table.
- `openapi/en/` — non-required / deprecated for daily workflow; keep as optional backup until a later cleanup.

### Change cadence

1. Maintainer exports and overwrites Chinese Specs under `openapi/`.
2. Agent produces a change summary (added / changed / deleted paths + suggested MDX targets).
3. After explicit user confirmation, agent updates `zh/` MDX, then English via glossary.

## Section 2 — Target IA and page split (document now, implement later)

### Target sidebar shape

```
API Reference
├── Overview / Base URL / Versioning / Error codes  (existing hand-written pages)
├── Account
│   ├── one page per external tag
├── Trade
│   ├── …
├── Risk
└── Aggregator
```

### Split rules

| Rule | Detail |
| --- | --- |
| Top-level groups | One per Spec file: Account / Trade / Risk / Aggregator |
| Second-level pages | One page per **external** tag (after glossary internal→external) |
| Page contents | All operations under that tag: method, path, permission, params, request/response highlights, examples |
| Path style | Full gateway paths (e.g. `/openapi/v1/mc-account/...`) |
| Suggested file paths | `zh/api-reference/{service}/{slug}.mdx` ↔ English mirror without `zh/` |

### Phase 1 agent behavior

- When writing rules or summaries, describe suggested pages using the target split above.
- Do **not** create/move endpoint MDX.
- Do **not** change `docs.json` `"openapi"` entries.
- Auto-generated pages remain until migration starts.

### Slug convention

- Map each external Chinese tag to a stable English slug in the glossary (e.g. 理财账户 → `finance-account`).
- If the same external name collides across services, prefix the slug with the service (rare).

### Current Spec tags (snapshot for migration planning)

As of 2026-07-21 Chinese Specs:

- **mc-account:** MLP 账户, 理财账户, 交易, 币种, 资金账户, 汇率, 成交订单, App 全局搜索, 资金费历史
- **mc-trade:** 交易, 交易账户, 订单, 成交
- **mc-risk:** 交易, 资金费率
- **mc-aggregator:** 行情数据

Internal→external mappings still apply when Specs use prefixed/internal tags (example pattern: `业务前端-交易` → `交易`).

## Section 3 — Glossary file

### Location

- Repo root: `glossary.zh-en.md`
- `AGENTS.md` references it; does not inline the full tables

### Tables

1. **Product / docs terms (zh ↔ en)**  
   Extend the existing AGENTS terminology set (Fund account, Flash conversion, PoR, etc.).

2. **Spec internal → external (Chinese, then en)**  
   Example: `业务前端-交易` → `交易` → `Trading`  
   Reader-facing MDX titles, sidebar labels, and body copy use **external** names only.  
   Change summaries may still mention the original Spec tag for verification.

3. **Page title / slug registry**  
   Columns: external Chinese name | English title | slug | service  
   Example: 理财账户 | Finance account | `finance-account` | account

### Maintenance

- New tags/terms: update glossary **before** or **with** MDX edits.
- English sync: look up glossary first; if missing, translate once and **write back**.
- Phase 1: seed from existing zh/en Specs and paired MDX where confident; mark uncertain internal tags as 待确认 instead of guessing.

## Section 4 — Spec change summary gate

### Trigger

After Chinese Specs under `openapi/` are updated (or the maintainer says they were), the agent runs this flow.  
**No MDX / navigation edits** until the user confirms the summary.

### Summary must include

1. **Scope** — which Spec files changed
2. **Path list** by service — added / changed / deleted (note method, path, tag, permission, notable param/schema changes)
3. **External mapping** — Spec tag → glossary external name; missing entries marked 待确认
4. **Suggested MDX targets** using target paths even if files do not exist yet  
   Example: `zh/api-reference/account/finance-account.mdx` (+ English mirror)
5. **Glossary updates needed** — new terms, tags, slugs
6. **Risks** — breaking changes, permission changes, renames, description-only diffs

### After confirmation

1. Update `glossary.zh-en.md` if needed
2. Edit Chinese MDX
3. Sync English via glossary
4. Run quality checklist

### Phase 1 special case

- Always produce the summary.
- If hand-written tag pages do not exist yet, post-confirmation work may be limited to overview/changelog/prose that still applies, plus an explicit note that full tag-page migration is pending — **unless** the user asks to start creating specific pages immediately.

## Section 5 — `AGENTS.md` rewrite outline

### Replace “Source of truth for APIs”

- Daily fact source: `openapi/mc-*.json` (Chinese)
- Deliverable: hand-written MDX; target state without `"openapi"` embedding
- Note honestly: until migration, `docs.json` may still temporarily embed Specs — follow repo reality; migration is a separate task
- `@OpenApiPermission` / sibling repos: export validation and dispute checks only

### Add “OpenAPI Spec → docs workflow”

- Export → summary → confirm → `zh/` → English via glossary
- Link `glossary.zh-en.md`
- Document target split (service + external tag page) and phase-1 “rules first”

### Adjust bilingual workflow

- Chinese pages first (unchanged)
- English translation must consult glossary; new renderings write back
- Keep technical identifiers untranslated (headers, paths, enum names)

### Update quality checklist

- [ ] Facts checked against latest Chinese Spec (or task is non-endpoint prose)
- [ ] Change summary produced and user-confirmed (for Spec-driven API changes)
- [ ] External naming via glossary (no raw internal Spec tags in reader copy)
- [ ] `zh/` before English; English consulted glossary
- [ ] No real secrets; locale-correct internal links
- [ ] (After migration) new pages registered in both language trees in `docs.json`; site default language remains `en`

### Out of scope for phase 1 implementation

- Removing `docs.json` `"openapi"` groups
- Bulk-creating tag MDX pages
- Deleting `openapi/en/` (rules may mark it non-required / deprecated only)

## Phase 1 implementation plan (after this spec is accepted)

1. Rewrite `AGENTS.md` per Section 5
2. Create `glossary.zh-en.md` with three tables; seed known rows; list 待确认 items
3. Do **not** migrate API Reference pages or `docs.json` in the same change set unless explicitly requested

## Phase 2 (future, not this change set)

1. Remove `"openapi"` from `docs.json`
2. Create hand-written tag pages per service using Spec + glossary
3. Update overview copy that still says pages are Spec-generated
4. Optionally remove or archive `openapi/en/`

## Success criteria (phase 1)

- Agents reading `AGENTS.md` treat Chinese Specs as the daily API fact source
- Spec-driven work defaults to summary-then-confirm
- Glossary exists and is the required lookup for naming/translation
- No accidental full API Reference migration in phase 1
