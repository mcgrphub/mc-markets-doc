# MC Markets OpenAPI documentation

## About this project

- Documentation site for **MC Markets OpenAPI** (MC OpenAPI), built on [Mintlify](https://mintlify.com)
- Audience: developers integrating with the multi-account REST API via the MC API Gateway
- Pages are MDX with YAML frontmatter; site config lives in `docs.json`
- Bilingual: English (`/` and root MDX) and Chinese (`zh/`)
- Site default language is **English** (`docs.json`: `en` with `default: true`) — do not change this unless explicitly asked
- Agent writing default is **Chinese first**: edit `zh/` pages first, then sync the matching English pages
- Prefer Mintlify docs MCP (`https://www.mintlify.com/docs/mcp`) over training data for Mintlify product questions
- Prefer project skills under `.agents/skills/mintlify*` when editing docs structure or components

## Source of truth for APIs

Daily fact source for endpoint docs: the **Chinese** OpenAPI Specs in this repo:

- `openapi/mc-account.json`
- `openapi/mc-trade.json`
- `openapi/mc-risk.json`
- `openapi/mc-aggregator.json`

These Specs are the `@OpenApiPermission`-filtered public subset. Prefer them over scanning sibling `mc-*` repos for routine edits.

`openapi/en/` is optional backup only — non-required and deprecated for daily agent workflow. English pages are translated from Chinese MDX via [`glossary.zh-en.md`](glossary.zh-en.md), not from `openapi/en/`.

Hand-written MDX is the reader-facing deliverable. Target state: API Reference pages are hand-written and `docs.json` does **not** embed Specs via `"openapi"`. Until that migration ships, `docs.json` may still temporarily reference Spec files — follow the repo as it is; do not remove those entries unless the user asks to start migration.

Sibling-repo / `@OpenApiPermission` checks are reserved for:

- Suspicious or incomplete Specs
- Explicit export validation requests

Annotation definition (for validation only): `com.mc.account.api.openapi.annotation.OpenApiPermission` in `mc-account`. Typical controller locations: `**/web/openapi/**` under `mc-*-service` modules.

## OpenAPI Spec → docs workflow

When Chinese Specs under `openapi/` are updated (or the maintainer confirms they were):

1. **Export** — Maintainer overwrites the latest Chinese Spec into `openapi/mc-*.json`.
2. **Diff and summarize** — Agent compares Specs and writes a **change summary** before any MDX or navigation edits. The summary must include:
   - **Scope** — which Spec files changed
   - **Path list** by service — added / changed / deleted (note method, path, tag, permission, notable param/schema changes)
   - **External mapping** — Spec tag → glossary external name; mark missing entries as 待确认
   - **Suggested MDX targets** using target paths even if files do not exist yet (for example `zh/api-reference/account/finance-account.mdx` and its English mirror)
   - **Glossary updates needed** — new terms, tags, slugs
   - **Risks** — breaking changes, permission changes, renames, description-only diffs
3. **Confirm** — Do **not** edit MDX or `docs.json` navigation until the user confirms the summary.
4. **After confirmation** — Update [`glossary.zh-en.md`](glossary.zh-en.md) if needed → edit `zh/` MDX → sync English via the glossary → then run the Quality checklist.
5. **Response field tables** — When endpoint response shapes or DTO field copy change, run `python3 scripts/sync_response_fields_from_openapi.py`. Path-level 200 schemas are often fully inlined and drop `title` / nested `$ref`; the script matches `components.schemas` by property keys (e.g. `FundingRateDto`) and reads `description` or `title`. Paginated `data` is split into page meta + `records[]` / `items[]` model tables.

### Target page split

- **Sidebar (reader-facing):** top-level groups are **行情 / Market data**, **交易 / Trading**, **理财 / Finance** — not Spec service names (Account / Trade / Risk / Aggregator).
- Second-level pages: one page per **external** tag (after glossary internal→external mapping).
- **File paths:** still `zh/api-reference/{service}/{slug}.mdx` ↔ English mirror without `zh/` (service = account / trade / risk / aggregator). Register pages under the correct sidebar group in `docs.json`; do not move files unless the user asks.

### Phase 1 limits

Tag pages may not exist yet. Unless the user asks to migrate, limit post-confirmation edits to applicable prose (overview, changelog, etc.) and note that full tag-page migration is pending. Do **not** remove `docs.json` `"openapi"` entries or bulk-create tag MDX pages in phase 1.

### Naming and glossary

Consult [`glossary.zh-en.md`](glossary.zh-en.md) for zh↔en terms, Spec internal→external tag mappings, and page title/slug registry. Reader-facing MDX titles, sidebar labels, and body copy must use **external** names only — never raw internal Spec tags (for example `业务前端-交易`). Change summaries may still mention the original Spec tag for verification.

## Terminology

| Prefer | Avoid / notes |
| --- | --- |
| MC Markets OpenAPI / MC OpenAPI | Generic "the API" without product name on first mention |
| Access Key / Secret Key (AK/SK) | API token, Bearer token (except when warning not to mix Bearer with AK/SK) |
| API Gateway / API 网关 | Calling backend services directly |
| `READ` / `TRADE` / `WITHDRAW` | Informal permission names |
| Finance account / 理财账户 | Confusing with fund account |
| Fund account / 资金账户 | Confusing with finance account |
| Flash conversion / 闪兑 | Vague "swap" unless quoting UI copy |
| Proof of Reserves / 储备金证明 (PoR) | Informal "reserve check" |
| Symbol / 币种 | Prefer consistency with existing endpoint pages |

Fuller zh↔en and internal→external mappings live in [`glossary.zh-en.md`](glossary.zh-en.md).

Keep English technical identifiers (`X-Access-Key`, path prefixes, enum names) unchanged in Chinese pages.

## Style preferences

- Use active voice and second person ("you" / "你")
- Keep sentences concise — one idea per sentence
- Use sentence case for English headings; Chinese headings follow existing `zh/` pages
- Bold UI elements: Click **API Key Management** / 点击 **API Key 管理**
- Code formatting for file names, commands, paths, headers, and code references
- No marketing fluff ("powerful", "seamless", "robust")
- Prefer present tense; state expected outcomes after major steps
- Example credentials must be clearly fake; never paste real Secret Keys

## Bilingual workflow

1. Write or update the Chinese page under `zh/` first
2. Before translating, consult [`glossary.zh-en.md`](glossary.zh-en.md); write new renderings back to the glossary; keep technical identifiers untranslated (headers, paths, enum names)
3. Sync the English counterpart at the mirrored path (for example `zh/authentication.mdx` → `authentication.mdx`)
4. Keep structure, examples, and endpoint facts aligned; only prose/locale differs
5. Internal links:
   - English pages: `/authentication`, `/api-reference/overview`
   - Chinese pages: `/zh/authentication`, `/zh/api-reference/overview`
6. When adding a page, register both language entries in `docs.json` navigation
7. Do not flip the site default language away from `en`

## Content boundaries

**Document**

- Public OpenAPI endpoints in the Chinese Specs under `openapi/` (the `@OpenApiPermission`-filtered subset)
- Gateway base URL already published in this repo (production `gateway.mcconnects.com`)
- Signing, permissions, pagination, error envelope, and integration guides for those APIs

**Do not document**

- Endpoints not present in those Chinese Specs (internal admin, ops, CRM, or unpublished services)
- Real secrets, production credentials, or private/internal hostnames
- Implementation details that are not needed for successful integration (unless explicitly requested)

## Required page structure

Every MDX page starts with frontmatter:

```yaml
---
title: "Clear, specific title"
description: "Concise description for SEO and navigation."
---
```

Optional: `sidebarTitle` when the nav label should differ from `title`.

## Mintlify components

### docs.json

- Refer to the [docs.json schema](https://mintlify.com/docs.json) when changing navigation or site settings

### Callouts

- `<Note>` — supplementary help
- `<Warning>` — cautions, secrets, breaking behavior
- `<Tip>` — best practices
- `<Info>` — neutral context
- `<Check>` — success confirmation

### Code and API examples

- Language tags on every fenced block
- `<CodeGroup>` for the same sample in multiple languages
- Realistic sample payloads; placeholder secrets only (`YOUR_SECRET_KEY`)
- Prefer gateway URLs from [Base URL](/api-reference/base-url)

### Procedures and layout

- `<Steps>` / `<Step>` for sequential instructions
- `<Tabs>` for platform-specific variants
- `<Accordion>` / `<AccordionGroup>` for progressive disclosure
- `<Card>` / `<CardGroup>` for navigation hubs
- Wrap images in `<Frame>` with descriptive alt text

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
