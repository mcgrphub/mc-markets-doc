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

Document **only** HTTP endpoints whose controllers/methods are annotated with `@OpenApiPermission` in sibling backend repos.

- Sibling repos live under the same parent directory as this repo, named with the `mc-` prefix (for example `../mc-account`, `../mc-trade`, `../mc-risk`, `../mc-aggregator-service`)
- Annotation definition: `com.mc.account.api.openapi.annotation.OpenApiPermission` (in `mc-account`)
- Typical locations: `**/web/openapi/**` controllers under `mc-*-service` modules
- Before adding or updating an endpoint page, search those repos for `@OpenApiPermission` and confirm method, path, and required permission (`value` / `publicAccess`)
- Do **not** document controllers, admin APIs, or internal routes that lack `@OpenApiPermission`

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
2. Sync the English counterpart at the mirrored path (for example `zh/authentication.mdx` → `authentication.mdx`)
3. Keep structure, examples, and endpoint facts aligned; only prose/locale differs
4. Internal links:
   - English pages: `/authentication`, `/api-reference/overview`
   - Chinese pages: `/zh/authentication`, `/zh/api-reference/overview`
5. When adding a page, register both language entries in `docs.json` navigation
6. Do not flip the site default language away from `en`

## Content boundaries

**Document**

- Public OpenAPI endpoints marked with `@OpenApiPermission`
- Gateway base URL already published in this repo (production `gateway.mcconnects.com`)
- Signing, permissions, pagination, error envelope, and integration guides for those APIs

**Do not document**

- Internal admin, ops, CRM, or unpublished services
- Endpoints without `@OpenApiPermission`
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

- [ ] Endpoint is backed by `@OpenApiPermission` in a sibling `mc-*` repo (or the change is non-endpoint prose)
- [ ] Chinese page updated first; English page synced when both exist
- [ ] Frontmatter has `title` and `description`
- [ ] Code blocks have language tags; no real secrets
- [ ] Internal links are root-relative and locale-correct (`/zh/...` vs `/...`)
- [ ] New pages added to both language trees in `docs.json` when applicable
- [ ] Site default language remains `en`
