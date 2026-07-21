#!/usr/bin/env python3
"""Polish ZH OpenAPI tags, strip codeKey enums, generate error-codes pages."""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPENAPI = ROOT / "openapi"
ENUM_JAVA = Path(
    "/Users/conorkang/IdeaProjects/MC/mc-common-core/src/main/java/com/mc/base/utils/error/ExceptionTypeEnum.java"
)

TAG_MAP = {
    "App综合搜索": "App 全局搜索",
    "MLP账户": "MLP 账户",
    "成交订单服务": "成交订单",
    "资金费历史记录": "资金费历史",
    "行情数据接口": "行情数据",
    "业务前端-交易": "交易",
    "开放接口-资金费率": "资金费率",
}

CODEKEY_DESC_EN = (
    "Business error key (`ExceptionTypeEnum` name). Full list: Error codes."
)
CODEKEY_DESC_ZH = "业务错误键（`ExceptionTypeEnum` 名称）。完整列表见错误码文档。"

SEC_ZH = {
    "Common (1000xxx)": "通用平台错误（1000xxx）",
    "General (1100xxx)": "通用业务错误（1100xxx）",
    "Account (2000xxx)": "账户服务（2000xxx）",
    "Trade (2100xxx)": "交易服务（2100xxx）",
    "Notify (2200xxx)": "通知服务（2200xxx）",
    "Auth (2300xxx)": "认证服务（2300xxx）",
    "Aggregator (2400xxx)": "行情聚合（2400xxx）",
}


def rewrite_tags(obj, stats: dict) -> None:
    if isinstance(obj, dict):
        if "tags" in obj and isinstance(obj["tags"], list):
            new = []
            for t in obj["tags"]:
                if isinstance(t, str) and t in TAG_MAP:
                    stats[t] = stats.get(t, 0) + 1
                    new.append(TAG_MAP[t])
                elif (
                    isinstance(t, dict)
                    and isinstance(t.get("name"), str)
                    and t["name"] in TAG_MAP
                ):
                    stats[t["name"]] = stats.get(t["name"], 0) + 1
                    new.append({**t, "name": TAG_MAP[t["name"]]})
                else:
                    new.append(t)
            obj["tags"] = new
        for v in obj.values():
            rewrite_tags(v, stats)
    elif isinstance(obj, list):
        for v in obj:
            rewrite_tags(v, stats)


def strip_codekey(obj, is_en: bool, stats: dict) -> None:
    if isinstance(obj, dict):
        props = obj.get("properties")
        if isinstance(props, dict) and isinstance(props.get("codeKey"), dict):
            ck = props["codeKey"]
            if "enum" in ck:
                stats["enums_removed"] = stats.get("enums_removed", 0) + 1
                stats["enum_values"] = stats.get("enum_values", 0) + len(
                    ck.get("enum") or []
                )
                ck.pop("enum", None)
            ck["type"] = "string"
            ck["description"] = CODEKEY_DESC_EN if is_en else CODEKEY_DESC_ZH
            props["codeKey"] = ck
        for v in obj.values():
            strip_codekey(v, is_en, stats)
    elif isinstance(obj, list):
        for v in obj:
            strip_codekey(v, is_en, stats)


def count_codekey_enums(obj) -> int:
    n = 0
    if isinstance(obj, dict):
        ck = (obj.get("properties") or {}).get("codeKey")
        if isinstance(ck, dict) and "enum" in ck:
            n += 1
        for v in obj.values():
            n += count_codekey_enums(v)
    elif isinstance(obj, list):
        for v in obj:
            n += count_codekey_enums(v)
    return n


def parse_exception_enum(java_text: str):
    entries = []
    section = "Common (1000xxx)"
    subsection = "Platform"

    for line in java_text.splitlines():
        m_sec = re.search(r"/\* =+\s*(.+?)\s*=+\s*\*/", line)
        if m_sec:
            title = m_sec.group(1).strip()
            if "结束" in title:
                continue
            low = title.lower()
            if "通用" in title or "1100" in title:
                section = "General (1100xxx)"
            elif "account" in low or "2000" in title:
                section = "Account (2000xxx)"
            elif "trade" in low or "2100" in title:
                section = "Trade (2100xxx)"
            elif "notify" in low or "2200" in title:
                section = "Notify (2200xxx)"
            elif "auth" in low or "2300" in title:
                section = "Auth (2300xxx)"
            elif "aggregate" in low or "2400" in title:
                section = "Aggregator (2400xxx)"
            else:
                section = title
            subsection = "General"
            continue

        if re.match(r"\s*//", line) and (
            "相关" in line or "模块" in line or "xxx" in line
        ):
            if "MT_RET" not in line:
                subsection = re.sub(r"^\s*//\s*", "", line).strip()
                continue

        m = re.match(
            r'\s*([A-Z][A-Z0-9_]*)\((?:(\d+),\s*)?"(\d{7})",\s*"([^"]*)"',
            line,
        )
        if m:
            name, http, code, msg = m.group(1), m.group(2), m.group(3), m.group(4)
            http_status = int(http) if http else 500
            sec, sub = section, subsection
            if code.startswith("1000"):
                sec = "Common (1000xxx)"
                sub = "Platform"
            entries.append((sec, sub, name, code, msg, http_status))
    return entries


def esc(s: str) -> str:
    return s.replace("|", "\\|")


def render_page(grouped: OrderedDict, lang: str) -> str:
    zh = lang == "zh"
    lines: list[str] = []
    if zh:
        lines += [
            "---",
            'title: "错误码"',
            'sidebarTitle: "错误码"',
            'description: "MC OpenAPI 业务错误码（`code` / `codeKey`），整理自 ExceptionTypeEnum。"',
            "---",
            "",
            "多数 OpenAPI 响应使用统一 JSON 信封，同时返回数字 `code` 与字符串 `codeKey`。",
            "业务分支请使用 `code` / `codeKey`；`msg` 仅作可读说明，不要依赖其精确文案。",
            "",
            "```json",
            "{",
            '  "code": 1000005,',
            '  "codeKey": "PARAM_ERROR",',
            '  "msg": "Invalid request parameter",',
            '  "success": false,',
            '  "data": null',
            "}",
            "```",
            "",
            "## 编码规则",
            "",
            "错误码为 **7 位**（部分 schema 中以数字返回）：",
            "",
            "| 段 | 位数 | 含义 |",
            "| --- | --- | --- |",
            "| `SS` | 2 | 场景 / 平台模块 |",
            "| `BB` | 2 | 业务域 |",
            "| `EEE` | 3 | 具体错误 |",
            "",
            "权威定义见 `mc-common-core` 中的 `ExceptionTypeEnum`。",
            "",
            "<Note>",
            "  各接口文档不再内联完整 `codeKey` 枚举，请以本页为目录。",
            "</Note>",
            "",
        ]
    else:
        lines += [
            "---",
            'title: "Error codes"',
            'sidebarTitle: "Error codes"',
            'description: "MC OpenAPI business error codes (`code` / `codeKey`) from ExceptionTypeEnum."',
            "---",
            "",
            "Most OpenAPI responses use a JSON envelope with both a numeric `code` and a string `codeKey`.",
            "Use `code` / `codeKey` for branching; treat `msg` as a human-readable hint only.",
            "",
            "```json",
            "{",
            '  "code": 1000005,',
            '  "codeKey": "PARAM_ERROR",',
            '  "msg": "Invalid request parameter",',
            '  "success": false,',
            '  "data": null',
            "}",
            "```",
            "",
            "## Code layout",
            "",
            "Error codes are **7-digit** values (returned as numbers in some schemas):",
            "",
            "| Part | Digits | Meaning |",
            "| --- | --- | --- |",
            "| `SS` | 2 | Scene / platform module |",
            "| `BB` | 2 | Business domain |",
            "| `EEE` | 3 | Specific error |",
            "",
            "Source of truth: `ExceptionTypeEnum` in `mc-common-core`.",
            "",
            "<Note>",
            "  Endpoint pages no longer inline the full `codeKey` enum. Use this page as the catalog.",
            "</Note>",
            "",
        ]

    for sec, subs in grouped.items():
        title = SEC_ZH.get(sec, sec) if zh else sec
        lines.append(f"## {title}")
        lines.append("")
        for sub, rows in subs.items():
            lines.append(f"### {sub}")
            lines.append("")
            if zh:
                lines.append("| `codeKey` | `code` | 说明 | HTTP |")
            else:
                lines.append("| `codeKey` | `code` | Message | HTTP |")
            lines.append("| --- | --- | --- | --- |")
            for name, code, msg, http in rows:
                lines.append(f"| `{name}` | `{code}` | {esc(msg)} | `{http}` |")
            lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    print("=== ZH tags ===")
    for f in sorted(OPENAPI.glob("*.json")):
        data = json.loads(f.read_text())
        stats: dict = {}
        rewrite_tags(data, stats)
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        print(f.name, stats or "(no changes)")

    print("\n=== strip codeKey enums ===")
    files = list(OPENAPI.glob("*.json")) + list((OPENAPI / "en").glob("*.json"))
    for f in files:
        data = json.loads(f.read_text())
        is_en = f.parent.name == "en"
        stats = {}
        strip_codekey(data, is_en, stats)
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        print(f.relative_to(ROOT), stats)

    entries = parse_exception_enum(ENUM_JAVA.read_text())
    print("\nparsed entries", len(entries))
    grouped: OrderedDict = OrderedDict()
    for sec, sub, name, code, msg, http in entries:
        grouped.setdefault(sec, OrderedDict()).setdefault(sub, []).append(
            (name, code, msg, http)
        )

    en_path = ROOT / "api-reference" / "error-codes.mdx"
    zh_path = ROOT / "zh" / "api-reference" / "error-codes.mdx"
    en_path.write_text(render_page(grouped, "en"))
    zh_path.write_text(render_page(grouped, "zh"))
    print("wrote", en_path)
    print("wrote", zh_path)

    print("\n=== verify tags ===")
    for f in sorted(OPENAPI.glob("*.json")):
        data = json.loads(f.read_text())
        tags = set()
        for item in data.get("paths", {}).values():
            for method, op in item.items():
                if method in ("get", "post", "put", "patch", "delete"):
                    tags.update(op.get("tags") or [])
        print(f.name, sorted(tags))

    print("\n=== verify codeKey enums left ===")
    for f in files:
        data = json.loads(f.read_text())
        left = count_codekey_enums(data)
        print(
            f.relative_to(ROOT),
            "enums_left",
            left,
            "size_kb",
            round(f.stat().st_size / 1024, 1),
        )


if __name__ == "__main__":
    main()
