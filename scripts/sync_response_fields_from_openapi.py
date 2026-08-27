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
4. Updates Chinese API Reference MDX pages in place; English pages are synced
   from Chinese MDX through the project glossary workflow
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {"overview.mdx", "base-url.mdx", "versioning.mdx", "error-codes.mdx"}
PAGE_META = {"total", "size", "current", "pages", "hasPrevious", "hasNext"}

# Temporary response-schema supplements verified against mc-account
# release/v3.9.0 at e3aa92d177aea72855e8a0a4c69e26ba4d987b77. Remove each
# supplement after a newly exported Chinese Spec contains the same field.
RESPONSE_FIELD_OVERRIDES = {
    "/openapi/v1/mc-account/finance/products/catalog": {
        "target": ("items", "properties"),
        "fields": {
            "maxAnnualRate": {
                "type": "number",
                "description": "最高年化%=基础+（仅活期超额）+登录最高券面",
            },
            "couponSupported": {
                "type": "boolean",
                "description": "是否支持加息券",
            },
            "couponNominalAnnualRate": {
                "type": "number",
                "description": "最高可用券面年化%",
            },
            "rewardMinHoldingDays": {
                "type": "integer",
                "format": "int32",
                "description": "奖励需连续持有满（天）；定期为空或 0",
            },
            "rewardMinPosition": {
                "type": "number",
                "description": "超额奖励持仓本金门槛；定期为空或 0",
            },
        },
    },
    "/openapi/v1/mc-account/finance/account/positions/holding": {
        "target": ("properties", "records", "items", "properties"),
        "fields": {
            "couponId": {"type": "string", "description": "绑定加息券 ID"},
            "couponNominalAnnualRate": {
                "type": "number",
                "description": "券面年化%",
            },
            "couponBoostAmountUsdc": {
                "type": "number",
                "description": "加息金额 USDC",
            },
            "couponQuoteUsdcPerProduct": {
                "type": "number",
                "description": "锁定时产品币兑 USDC",
            },
            "couponQuoteTimeMs": {
                "type": "integer",
                "format": "int64",
                "description": "报价时刻毫秒",
            },
            "pauseRedeem": {
                "type": "boolean",
                "description": "是否暂停赎回",
            },
        },
    },
    "/openapi/v1/mc-account/finance/account/positions/history": {
        "target": ("properties", "records", "items", "properties"),
        "fields": {
            "subscribeTimeTimestamp": {
                "type": "integer",
                "format": "int64",
                "description": "申购时间毫秒；持仓 create_time / start_time",
            },
            "subscribeTime": {
                "type": "string",
                "format": "date-time",
                "description": "关联持仓申购时间",
            },
            "currentRewardAmount": {
                "type": "number",
                "description": "当前持有利息（赎回后为 0 或持仓快照）",
            },
            "cumulativeRewardAmount": {
                "type": "number",
                "description": "累计利息",
            },
            "status": {"type": "string", "description": "本列表固定 REDEEMED"},
        },
    },
    "/openapi/v1/mc-account/finance/account/overview": {
        "target": ("properties", "products", "items", "properties"),
        "fields": {
            "totalAnnualRate": {
                "type": "number",
                "description": "总年化%=基础+奖励+登录券面（展示用）",
            },
            "couponSupported": {
                "type": "boolean",
                "description": "是否支持加息券",
            },
            "couponNominalAnnualRate": {
                "type": "number",
                "description": "最高可用券面年化%",
            },
        },
    },
}

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


def load_specs(locale: str = "zh") -> list[dict]:
    names = [
        "mc-account.json",
        "mc-trade.json",
        "mc-risk.json",
        "mc-aggregator.json",
    ]
    # Chinese Specs are the only structural source of truth. `openapi/en/` is
    # deprecated and must not introduce fields that do not exist in Chinese
    # Specs. The locale argument remains for compatibility with older callers.
    base = ROOT / "openapi"
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


def schema_compatible(spec: dict, inline: dict, candidate: dict, depth: int = 0) -> bool:
    """Whether a richer component can safely fill gaps in an inline schema.

    Springdoc can inline an object while dropping nested ``$ref`` details. A
    component may therefore be richer than the inline shape. Existing nested
    properties, especially paginated ``records[]`` items, must still match.
    """
    if depth > 12:
        return True
    inline = resolve(spec, inline)
    candidate = resolve(spec, candidate)
    inline_type = norm_type(inline)
    candidate_type = norm_type(candidate)
    if inline_type != candidate_type:
        return False

    inline_props = inline.get("properties") or {}
    candidate_props = candidate.get("properties") or {}
    if inline_props:
        if set(inline_props) != set(candidate_props):
            return False
        for key, inline_value in inline_props.items():
            candidate_value = candidate_props[key]
            if norm_type(resolve(spec, inline_value)) != norm_type(
                resolve(spec, candidate_value)
            ):
                return False
            resolved_inline = resolve(spec, inline_value)
            has_known_children = bool(
                resolved_inline.get("properties")
                or isinstance(resolved_inline.get("additionalProperties"), dict)
                or (
                    norm_type(resolved_inline) == "array"
                    and isinstance(resolved_inline.get("items"), dict)
                    and (
                        resolve(spec, resolved_inline["items"]).get("properties")
                        or isinstance(
                            resolve(spec, resolved_inline["items"]).get(
                                "additionalProperties"
                            ),
                            dict,
                        )
                    )
                )
            )
            if has_known_children and not schema_compatible(
                spec, inline_value, candidate_value, depth + 1
            ):
                return False

    if inline_type == "array":
        inline_items = inline.get("items") or {}
        candidate_items = candidate.get("items") or {}
        resolved_items = resolve(spec, inline_items)
        if resolved_items.get("properties") or isinstance(
            resolved_items.get("additionalProperties"), dict
        ):
            return schema_compatible(spec, inline_items, candidate_items, depth + 1)

    inline_addl = inline.get("additionalProperties")
    if isinstance(inline_addl, dict):
        candidate_addl = candidate.get("additionalProperties")
        return isinstance(candidate_addl, dict) and schema_compatible(
            spec, inline_addl, candidate_addl, depth + 1
        )
    return True


def find_matching_component(spec: dict, inline: dict) -> dict | None:
    """Return a components schema with the same shape and richer docs.

    Important: many RetResult* wrappers share identical top-level keys
    (status/message/code/data/...). Matching on those keys alone wrongly
    replaces every endpoint with the richest wrapper (e.g. staticConfig).
    Require a full structural fingerprint, including `data` shape.
    """
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
        if not schema_compatible(spec, inline, candidate):
            continue
        score = doc_score(spec, candidate)
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
    enum_values = sch.get("enum") or []
    if norm_type(sch) == "string" and enum_values:
        rendered_values = "、".join(f"`{value}`" for value in enum_values)
        enum_copy = (
            f"可选值：{rendered_values}"
            if locale == "zh"
            else f"Allowed values: {rendered_values}"
        )
        if not all(str(value) in text for value in enum_values):
            separator = "；" if locale == "zh" else "; "
            text = f"{text}{separator}{enum_copy}" if text else enum_copy
    if text:
        return text[:480]
    if page_context and name in PAGE_DESC[locale]:
        return PAGE_DESC[locale][name]
    if name in PAGE_DESC[locale]:
        return PAGE_DESC[locale][name]
    return ""


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
        if "<" in name or ">" in name:
            name = f"`{name}`"
        lines.append(f"| {name} | {typ or '—'} | {desc} |")
    return "\n".join(lines)


def join_path(parent: str, child: str) -> str:
    if not parent:
        return child
    if not child:
        return parent
    return f"{parent}.{child}"


def section_label(path: str, kind: str, locale: str) -> str:
    """kind: object | array-item | map-value"""
    if locale == "zh":
        if kind == "array-item":
            return f"`{path}` 元素："
        if kind == "map-value":
            return f"`{path}` 映射值字段："
        return f"`{path}` 字段："
    if kind == "array-item":
        return f"`{path}` items:"
    if kind == "map-value":
        return f"`{path}` map value fields:"
    return f"`{path}` fields:"


def is_expandable_object(sch: dict) -> bool:
    return bool(
        sch.get("properties")
        or (
            isinstance(sch.get("additionalProperties"), dict)
            and sch.get("additionalProperties") is not True
        )
    )


def is_expandable_array_items(items: dict) -> bool:
    it = items.get("type")
    if isinstance(it, list):
        it = next((x for x in it if x != "null"), None)
    return bool(
        items.get("properties")
        or it in ("object", "array")
        or isinstance(items.get("additionalProperties"), dict)
        or items.get("items")
    )


def collect_nested_sections(
    spec: dict,
    sch: dict,
    *,
    path: str,
    locale: str,
    headers: tuple[str, str, str],
    depth: int = 0,
    max_depth: int = 12,
    seen: set[str] | None = None,
) -> list[str]:
    """Render one schema level as its own table; nest deeper levels as follow-up tables."""
    seen = seen if seen is not None else set()
    if path in seen or depth > max_depth:
        return []
    if path:
        seen.add(path)

    sch = enrich(spec, sch)
    parts: list[str] = []
    t = sch.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), t[0] if t else None)

    props = sch.get("properties") or {}
    addl = sch.get("additionalProperties")
    nested: list[tuple[str, dict, str]] = []

    if props:
        rows: list[tuple[str, str, str]] = []
        for key, value in props.items():
            value = enrich(spec, value)
            rows.append((key, norm_type(value), field_copy(key, value, locale)))
            vt = value.get("type")
            if isinstance(vt, list):
                vt = next((x for x in vt if x != "null"), None)
            child_path = join_path(path, key)
            if vt == "array":
                items = enrich(spec, value.get("items") or {})
                if is_expandable_array_items(items):
                    nested.append((f"{child_path}[]", items, "array-item"))
            elif is_expandable_object(value):
                nested.append((child_path, value, "object"))
        if path:
            # Root `data` object table is introduced by the ### heading.
            kind = "array-item" if path.endswith("[]") else "object"
            if "<key>" in path:
                kind = "map-value"
            parts.append(section_label(path, kind, locale))
            parts.append("")
        parts.append(render_table(headers, rows))
        parts.append("")
        for child_path, child_sch, _kind in nested:
            parts.extend(
                collect_nested_sections(
                    spec,
                    child_sch,
                    path=child_path,
                    locale=locale,
                    headers=headers,
                    depth=depth + 1,
                    max_depth=max_depth,
                    seen=seen,
                )
            )
        return parts

    if t == "array":
        items = enrich(spec, sch.get("items") or {})
        item_path = f"{path}[]" if path else "data[]"
        if path in ("", "data"):
            note = (
                "`data` 为对象数组。元素字段见下表。"
                if locale == "zh"
                else "`data` is an array of objects. Element fields follow."
            )
            parts.append(note)
            parts.append("")
        if is_expandable_array_items(items):
            parts.extend(
                collect_nested_sections(
                    spec,
                    items,
                    path=item_path,
                    locale=locale,
                    headers=headers,
                    depth=depth + 1,
                    max_depth=max_depth,
                    seen=seen,
                )
            )
        else:
            parts.append(section_label(item_path, "array-item", locale))
            parts.append("")
            parts.append(
                render_table(
                    headers,
                    [(item_path, norm_type(items), field_copy("item", items, locale))],
                )
            )
            parts.append("")
        return parts

    if isinstance(addl, dict) and addl is not True:
        addl = enrich(spec, addl)
        map_path = join_path(path, "<key>") if path else "<key>"
        rows = [
            (
                "<key>",
                norm_type(addl),
                field_copy("value", addl, locale)
                or ("映射值" if locale == "zh" else "Map value"),
            )
        ]
        if path:
            parts.append(section_label(path, "object", locale))
            parts.append("")
        parts.append(render_table(headers, rows))
        parts.append("")
        if is_expandable_object(addl) or addl.get("type") == "array":
            parts.extend(
                collect_nested_sections(
                    spec,
                    addl,
                    path=map_path,
                    locale=locale,
                    headers=headers,
                    depth=depth + 1,
                    max_depth=max_depth,
                    seen=seen,
                )
            )
        return parts

    # Scalar / opaque `data`
    rows = [
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
    ]
    parts.append(render_table(headers, rows))
    parts.append("")
    return parts


def render_response_block(spec: dict, data_sch: dict, locale: str) -> str:
    data_sch = enrich(spec, data_sch)
    props = data_sch.get("properties") or {}
    list_key = detect_page_list_key(props) if props else None

    if locale == "zh":
        headers = ("字段", "类型", "说明")
        title = "### 响应 `data` 字段"
    else:
        headers = ("Field", "Type", "Description")
        title = "### Response `data` fields"

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
        items = enrich(spec, (props[list_key].get("items") or {}))
        parts.extend(
            collect_nested_sections(
                spec,
                items,
                path=f"{list_key}[]",
                locale=locale,
                headers=headers,
            )
        )
        return "\n".join(parts).rstrip() + "\n\n"

    nested = collect_nested_sections(
        spec,
        data_sch,
        path="data" if (data_sch.get("type") == "array" or not props) else "",
        locale=locale,
        headers=headers,
    )
    if not nested:
        empty = (
            "（Spec 未声明 `data` 字段结构）"
            if locale == "zh"
            else "(No `data` field schema in Spec)"
        )
        nested = [render_table(headers, [("—", "—", empty)]), ""]
    parts.extend(nested)
    return "\n".join(parts).rstrip() + "\n\n"


def apply_response_field_overrides(path: str, data_sch: dict) -> dict:
    override = RESPONSE_FIELD_OVERRIDES.get(path)
    if not override:
        return data_sch
    out = deepcopy(data_sch)
    target = out
    try:
        for key in override["target"]:
            target = target[key]
    except (KeyError, TypeError):
        return out
    for name, field in override["fields"].items():
        if name not in target:
            target[name] = deepcopy(field)
        elif field.get("description"):
            target[name]["description"] = field["description"]
    return out


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
            # Do NOT enrich the RetResult envelope first — many wrappers share
            # the same top-level keys and would cross-match. Enrich only `data`.
            sch = resolve(spec, content.get("schema") or {})
            props = sch.get("properties") or {}
            if "data" in props:
                data_sch = enrich(spec, props["data"])
                return spec, apply_response_field_overrides(path, data_sch)
            data_sch = enrich(spec, sch)
            return spec, apply_response_field_overrides(path, data_sch)
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
                        and (
                            "元素" in stripped
                            or "字段" in stripped
                            or "items" in stripped
                            or "fields" in stripped
                            or "[]" in stripped
                            or "映射" in stripped
                            or "map value" in stripped
                        )
                    )
                    or stripped.startswith("`data` 为")
                    or stripped.startswith("`data` is an array")
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
    for locale, specs in (("zh", load_specs("zh")),):
        root = ROOT / "zh" / "api-reference"
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
    risk = next(
        s
        for s in zh_specs
        if "FundingRateDto" in ((s.get("components") or {}).get("schemas") or {})
    )
    _, data = find_data_schema(zh_specs, "GET", "/openapi/v1/mc-risk/funding-rate")
    assert data is not None
    items = enrich(risk, (data.get("properties") or {})["records"].get("items") or {})
    symbol = (items.get("properties") or {})["symbol"]
    assert symbol.get("title") == "币种", symbol
    print(
        "OK: funding-rate records resolved via FundingRateDto title=",
        symbol.get("title"),
    )

    # Prove RetResult wrappers are not cross-matched to staticConfig.
    _, modify_data = find_data_schema(
        zh_specs, "PUT", "/openapi/v1/mc-trade/trade/positions/modify"
    )
    assert modify_data is not None
    modify_props = set((modify_data.get("properties") or {}).keys())
    assert modify_props == {"code", "orderId", "params"}, modify_props
    modify_block = render_response_block(
        next(s for s in zh_specs if "paths" in s and "/openapi/v1/mc-trade/trade/positions/modify" in s["paths"]),
        modify_data,
        "zh",
    )
    assert "SessionTrade" not in modify_block
    assert "| code | string |" in modify_block
    print("OK: positions/modify data not cross-matched to staticConfig")

    for path, count in stats:
        if count:
            print(f"{path}: {count}")


if __name__ == "__main__":
    main()
