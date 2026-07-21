#!/usr/bin/env python3
"""Sync API Reference response `data` field tables from OpenAPI Specs.

Path-level 200 schemas in this repo are often fully inlined and drop
`title` / `$ref` metadata that still exists under `components.schemas`
(e.g. FundingRateDto). This script:

1. Prefers matching `components.schemas` (exact property-key match) when
   they carry richer docs or nested `$ref`s
2. Reads field copy from `description` or `title`
3. Splits pagination envelopes (`records` / `items` + page meta) into
   two tables
4. Updates zh + en API Reference MDX pages in place
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {"overview.mdx", "base-url.mdx", "versioning.mdx", "error-codes.mdx"}
PAGE_META = {"total", "size", "current", "pages", "hasPrevious", "hasNext"}

PAGE_DESC = {
    "zh": {
        "records": "当前页记录列表",
        "items": "当前页条目列表",
        "list": "当前页列表",
        "total": "总记录数",
        "size": "每页条数",
        "current": "当前页码",
        "pages": "总页数",
        "hasPrevious": "是否有上一页",
        "hasNext": "是否有下一页",
        "page": "当前页码",
        "pageSize": "每页条数",
        "snapshotVersion": "快照版本号",
    },
    "en": {
        "records": "Records on the current page",
        "items": "Items on the current page",
        "list": "List on the current page",
        "total": "Total number of records",
        "size": "Page size",
        "current": "Current page number",
        "pages": "Total number of pages",
        "hasPrevious": "Whether a previous page exists",
        "hasNext": "Whether a next page exists",
        "page": "Current page number",
        "pageSize": "Page size",
        "snapshotVersion": "Snapshot version",
    },
}

ENDPOINT_RE = re.compile(r"`(GET|POST|PUT|DELETE|PATCH)\s+(/openapi/[^`\s]+)`")
RESP_START_RE = re.compile(
    r"^### (?:响应 `data` 字段|Response `data` fields)\s*$",
    re.M,
)


def load_specs(locale: str) -> list[dict]:
    names = [
        "mc-account.json",
        "mc-trade.json",
        "mc-risk.json",
        "mc-aggregator.json",
    ]
    base = ROOT / "openapi" if locale == "zh" else ROOT / "openapi" / "en"
    specs: list[dict] = []
    for name in names:
        path = base / name
        if not path.exists():
            path = ROOT / "openapi" / name
        specs.append(json.loads(path.read_text()))
    return specs


def resolve(spec: dict, sch: dict | None, stack: list[str] | None = None) -> dict:
    if not isinstance(sch, dict):
        return {}
    stack = stack or []
    if "$ref" in sch:
        ref = sch["$ref"]
        if ref in stack:
            return {"type": "object", "description": sch.get("description") or ""}
        name = ref.split("/")[-1]
        target = ((spec.get("components") or {}).get("schemas") or {}).get(name)
        if not isinstance(target, dict):
            return {"type": "object"}
        resolved = resolve(spec, target, stack + [ref])
        out = dict(resolved)
        for key in ("description", "title"):
            if sch.get(key) and not out.get(key):
                out[key] = sch[key]
        return out
    if "allOf" in sch:
        merged: dict = {"type": "object", "properties": {}}
        for part in sch["allOf"]:
            p = resolve(spec, part, stack)
            merged["properties"].update(p.get("properties") or {})
            for key in (
                "type",
                "format",
                "items",
                "additionalProperties",
                "description",
                "title",
            ):
                if key in p and not merged.get(key):
                    merged[key] = p[key]
        for key in ("description", "title"):
            if sch.get(key):
                merged[key] = sch[key]
        return merged
    if "oneOf" in sch or "anyOf" in sch:
        for variant in sch.get("oneOf") or sch.get("anyOf") or []:
            resolved = resolve(spec, variant, stack)
            if resolved.get("type") != "null" and resolved:
                out = dict(resolved)
                for key in ("description", "title"):
                    if sch.get(key):
                        out[key] = sch[key]
                return out
        return {"type": "object"}
    return sch


def prop_keys(sch: dict) -> frozenset[str]:
    return frozenset((sch.get("properties") or {}).keys())


def doc_score(spec: dict, sch: dict, depth: int = 0) -> int:
    """Higher when schema carries title/description or nested $ref."""
    if depth > 8 or not isinstance(sch, dict):
        return 0
    score = 0
    raw_has_ref = "$ref" in json.dumps(sch, ensure_ascii=False)
    if raw_has_ref:
        score += 40
    resolved = resolve(spec, sch)
    if resolved.get("title") or resolved.get("description"):
        score += 1
    for value in (resolved.get("properties") or {}).values():
        if not isinstance(value, dict):
            continue
        if "$ref" in value:
            score += 20
        leaf = resolve(spec, value)
        if leaf.get("title") or leaf.get("description"):
            score += 2
        if leaf.get("type") == "array" and isinstance(leaf.get("items"), dict):
            score += doc_score(spec, leaf["items"], depth + 1)
        elif leaf.get("properties"):
            score += doc_score(spec, leaf, depth + 1)
    if resolved.get("type") == "array" and isinstance(resolved.get("items"), dict):
        score += doc_score(spec, resolved["items"], depth + 1)
    return score


def find_matching_component(spec: dict, inline: dict) -> dict | None:
    """Return a components schema with the same property keys and richer docs."""
    keys = prop_keys(inline)
    if len(keys) < 2:
        return None
    inline_score = doc_score(spec, inline)
    best_name = None
    best_score = inline_score
    schemas = (spec.get("components") or {}).get("schemas") or {}
    for name, candidate in schemas.items():
        if not isinstance(candidate, dict):
            continue
        resolved = resolve(spec, candidate)
        if prop_keys(resolved) != keys:
            continue
        score = doc_score(spec, candidate)
        # Prefer component schemas that keep $ref children.
        if score > best_score:
            best_score = score
            best_name = name
    if not best_name:
        return None
    return resolve(spec, {"$ref": f"#/components/schemas/{best_name}"})


def enrich(spec: dict, sch: dict | None, stack: list[str] | None = None) -> dict:
    """Resolve refs and replace inlined objects with richer component matches."""
    if not isinstance(sch, dict):
        return {}
    stack = stack or []
    if "$ref" in sch:
        ref = sch["$ref"]
        if ref in stack:
            return {"type": "object"}
        return enrich(spec, resolve(spec, sch, stack), stack + [ref])

    if "allOf" in sch or "oneOf" in sch or "anyOf" in sch:
        return enrich(spec, resolve(spec, sch, stack), stack)

    out = dict(sch)
    props = out.get("properties")
    if isinstance(props, dict) and props:
        matched = find_matching_component(spec, out)
        if matched is not None and matched is not out:
            # Re-enter with the component schema so nested $refs resolve.
            return enrich(spec, matched, stack)
        new_props = {}
        for key, value in props.items():
            new_props[key] = enrich(spec, value, stack) if isinstance(value, dict) else value
        out["properties"] = new_props

    if out.get("type") == "array" and isinstance(out.get("items"), dict):
        out["items"] = enrich(spec, out["items"], stack)

    if isinstance(out.get("additionalProperties"), dict):
        out["additionalProperties"] = enrich(spec, out["additionalProperties"], stack)

    return out


def norm_type(sch: dict) -> str:
    t = sch.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), t[0] if t else "")
    return t or "—"


def esc(text: str) -> str:
    return (text or "").replace("\n", " ").replace("|", "\\|").strip()


def field_copy(name: str, sch: dict, locale: str, *, page_context: bool = False) -> str:
    text = esc(sch.get("description") or sch.get("title") or "")
    if text:
        return text[:240]
    if page_context and name in PAGE_DESC[locale]:
        return PAGE_DESC[locale][name]
    if name in PAGE_DESC[locale]:
        return PAGE_DESC[locale][name]
    return ""


def walk_fields(
    spec: dict,
    sch: dict,
    *,
    prefix: str = "",
    depth: int = 0,
    max_depth: int = 12,
    rows: list[tuple[str, str, str]] | None = None,
    seen: set[str] | None = None,
    locale: str = "zh",
) -> list[tuple[str, str, str]]:
    rows = rows if rows is not None else []
    seen = seen if seen is not None else set()
    if prefix in seen or depth > max_depth:
        return rows
    if prefix:
        seen.add(prefix)

    sch = enrich(spec, sch)
    t = sch.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), t[0] if t else None)
    props = sch.get("properties") or {}
    addl = sch.get("additionalProperties")

    if props:
        for key, value in props.items():
            value = enrich(spec, value)
            path = f"{prefix}.{key}" if prefix else key
            rows.append((path, norm_type(value), field_copy(key, value, locale)))
            vt = value.get("type")
            if isinstance(vt, list):
                vt = next((x for x in vt if x != "null"), None)
            if vt == "array":
                items = enrich(spec, value.get("items") or {})
                it = items.get("type")
                if isinstance(it, list):
                    it = next((x for x in it if x != "null"), None)
                if (
                    items.get("properties")
                    or it in ("object", "array")
                    or isinstance(items.get("additionalProperties"), dict)
                ):
                    walk_fields(
                        spec,
                        items,
                        prefix=path + "[]",
                        depth=depth + 1,
                        max_depth=max_depth,
                        rows=rows,
                        seen=seen,
                        locale=locale,
                    )
            elif (
                vt == "object"
                or value.get("properties")
                or isinstance(value.get("additionalProperties"), dict)
            ):
                walk_fields(
                    spec,
                    value,
                    prefix=path,
                    depth=depth + 1,
                    max_depth=max_depth,
                    rows=rows,
                    seen=seen,
                    locale=locale,
                )
        return rows

    if t == "array":
        items = enrich(spec, sch.get("items") or {})
        if not prefix:
            rows.append(
                (
                    "data",
                    "array",
                    (
                        "`data` 为对象数组，元素字段见 `[]...`"
                        if locale == "zh"
                        else "`data` is an array of objects; element fields use `[]...`"
                    ),
                )
            )
            item_prefix = "[]"
        else:
            item_prefix = prefix + "[]"
        if (
            items.get("properties")
            or items.get("type") in ("object", "array")
            or isinstance(items.get("additionalProperties"), dict)
            or items.get("items")
        ):
            walk_fields(
                spec,
                items,
                prefix=item_prefix,
                depth=depth + 1,
                max_depth=max_depth,
                rows=rows,
                seen=seen,
                locale=locale,
            )
        else:
            rows.append((item_prefix, norm_type(items), field_copy("item", items, locale)))
        return rows

    if isinstance(addl, dict):
        addl = enrich(spec, addl)
        path = f"{prefix}.<key>" if prefix else "<key>"
        rows.append(
            (
                path,
                norm_type(addl),
                field_copy("value", addl, locale)
                or ("映射值" if locale == "zh" else "Map value"),
            )
        )
        walk_fields(
            spec,
            addl,
            prefix=path,
            depth=depth + 1,
            max_depth=max_depth,
            rows=rows,
            seen=seen,
            locale=locale,
        )
        return rows

    if not prefix:
        rows.append(
            (
                "data",
                norm_type(sch),
                field_copy("data", sch, locale)
                or (
                    "`data` 为该类型标量"
                    if locale == "zh"
                    else "`data` is a scalar of this type"
                ),
            )
        )
    return rows


def detect_page_list_key(props: dict) -> str | None:
    keys = set(props)
    if (
        "records" in props
        and props["records"].get("type") == "array"
        and len(keys & PAGE_META) >= 2
    ):
        return "records"
    if (
        "items" in props
        and props["items"].get("type") == "array"
        and ({"page", "pageSize", "total"} & keys)
    ):
        return "items"
    if (
        "list" in props
        and props["list"].get("type") == "array"
        and len(keys & PAGE_META) >= 2
    ):
        return "list"
    return None


def render_table(headers: tuple[str, str, str], rows: list[tuple[str, str, str]]) -> str:
    h1, h2, h3 = headers
    lines = [f"| {h1} | {h2} | {h3} |", "| --- | --- | --- |"]
    for name, typ, desc in rows:
        lines.append(f"| {name} | {typ or '—'} | {desc} |")
    return "\n".join(lines)


def render_response_block(spec: dict, data_sch: dict, locale: str) -> str:
    data_sch = enrich(spec, data_sch)
    props = data_sch.get("properties") or {}
    list_key = detect_page_list_key(props) if props else None

    if locale == "zh":
        headers = ("字段", "类型", "说明")
        title = "### 响应 `data` 字段"
        item_label = f"`{list_key}[]` 元素：" if list_key else None
    else:
        headers = ("Field", "Type", "Description")
        title = "### Response `data` fields"
        item_label = f"`{list_key}[]` items:" if list_key else None

    parts = [title, ""]
    if list_key:
        page_rows = []
        for key, value in props.items():
            value = enrich(spec, value)
            page_rows.append(
                (key, norm_type(value), field_copy(key, value, locale, page_context=True))
            )
        parts.append(render_table(headers, page_rows))
        parts.append("")
        parts.append(item_label or "")
        parts.append("")
        items = enrich(spec, (props[list_key].get("items") or {}))
        item_rows: list[tuple[str, str, str]] = []
        walk_fields(spec, items, rows=item_rows, locale=locale)
        if item_rows:
            parts.append(render_table(headers, item_rows))
        else:
            empty = (
                "（无元素字段声明）"
                if locale == "zh"
                else "(No item fields declared)"
            )
            parts.append(render_table(headers, [("—", "—", empty)]))
        parts.append("")
        return "\n".join(parts)

    rows: list[tuple[str, str, str]] = []
    walk_fields(spec, data_sch, rows=rows, locale=locale)
    if not rows:
        empty = (
            "（Spec 未声明 `data` 字段结构）"
            if locale == "zh"
            else "(No `data` field schema in Spec)"
        )
        rows = [("—", "—", empty)]
    parts.append(render_table(headers, rows))
    parts.append("")
    return "\n".join(parts)


def find_data_schema(specs: list[dict], method: str, path: str):
    method = method.lower()
    path = (
        path.replace("&#123;", "{")
        .replace("&#125;", "}")
        .replace("&amp;", "&")
    )
    for spec in specs:
        ops = (spec.get("paths") or {}).get(path)
        if not ops:
            continue
        op = ops.get(method)
        if not isinstance(op, dict):
            continue
        resp = (op.get("responses") or {}).get("200") or {}
        for content in (resp.get("content") or {}).values():
            sch = enrich(spec, content.get("schema") or {})
            props = sch.get("properties") or {}
            if "data" in props:
                return spec, enrich(spec, props["data"])
            return spec, sch
    return None, None


def replace_response_sections(
    text: str, specs: list[dict], locale: str
) -> tuple[str, int]:
    parts = re.split(r"(?=^## )", text, flags=re.M)
    out: list[str] = []
    replaced = 0
    for part in parts:
        match = ENDPOINT_RE.search(part)
        if not match:
            out.append(part)
            continue
        method, path = match.group(1), match.group(2)
        spec, data_sch = find_data_schema(specs, method, path)
        if data_sch is None:
            out.append(part)
            continue

        block = render_response_block(spec, data_sch, locale)
        start_match = RESP_START_RE.search(part)
        if start_match:
            start = start_match.start()
            rest = part[start_match.end() :]
            lines = rest.splitlines(keepends=True)
            index = 0
            while index < len(lines):
                stripped = lines[index].strip()
                if (
                    stripped.startswith("```")
                    or stripped == "---"
                    or stripped.startswith("## ")
                ):
                    break
                if stripped.startswith("### ") and not stripped.startswith(
                    ("### 响应", "### Response")
                ):
                    break
                if (
                    stripped == ""
                    or stripped.startswith("|")
                    or (
                        stripped.startswith("`")
                        and ("元素" in stripped or "items" in stripped or "[]" in stripped)
                    )
                    or stripped.startswith("### 响应")
                    or stripped.startswith("### Response")
                ):
                    index += 1
                    continue
                break
            new_part = part[:start] + block + "".join(lines[index:])
            new_part = re.sub(r"(\|[^\n]*)\n```", r"\1\n\n```", new_part)
            out.append(new_part)
            replaced += 1
            continue

        fence = re.search(r"\n```", part)
        if fence:
            new_part = part[: fence.start()] + "\n" + block + part[fence.start() + 1 :]
        else:
            trailing = re.search(r"\n---\s*$", part)
            if trailing:
                new_part = (
                    part[: trailing.start()] + "\n" + block + part[trailing.start() :]
                )
            else:
                new_part = part.rstrip() + "\n\n" + block
        new_part = re.sub(r"(\|[^\n]*)\n```", r"\1\n\n```", new_part)
        out.append(new_part)
        replaced += 1
    return "".join(out), replaced


def main() -> None:
    stats: list[tuple[str, int]] = []
    for locale, specs in (("zh", load_specs("zh")), ("en", load_specs("en"))):
        root = ROOT / "zh" / "api-reference" if locale == "zh" else ROOT / "api-reference"
        for path in sorted(root.rglob("*.mdx")):
            if path.name in SKIP:
                continue
            text = path.read_text()
            if "/openapi/" not in text:
                continue
            new_text, count = replace_response_sections(text, specs, locale)
            new_text = re.sub(r"\n{4,}", "\n\n\n", new_text)
            if new_text != text:
                path.write_text(new_text)
            stats.append((str(path.relative_to(ROOT)), count))

    # Prove FundingRateDto titles flow through enrich().
    zh_specs = load_specs("zh")
    risk = next(s for s in zh_specs if "FundingRateDto" in ((s.get("components") or {}).get("schemas") or {}))
    _, data = find_data_schema(
        zh_specs, "GET", "/openapi/v1/mc-risk/funding-rate"
    )
    assert data is not None
    items = enrich(risk, (data.get("properties") or {})["records"].get("items") or {})
    symbol = (items.get("properties") or {})["symbol"]
    assert symbol.get("title") == "币种", symbol
    print("OK: funding-rate records resolved via FundingRateDto title=", symbol.get("title"))
    for path, count in stats:
        if count:
            print(f"{path}: {count}")


if __name__ == "__main__":
    main()
