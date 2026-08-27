import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = re.compile(r"`(GET|POST|PUT|DELETE|PATCH)\s+(/openapi/[^`\s]+)`")
TABLE_ROW = re.compile(r"^\| ([^|]+?) \| ([^|]+?) \|", re.M)


def response_fields(path: Path, locale: str) -> dict[tuple[str, str], list[str]]:
    heading = (
        "### 响应 `data` 字段"
        if locale == "zh"
        else "### Response `data` fields"
    )
    endpoints = {}
    for section in re.split(r"(?=^## )", path.read_text(), flags=re.M):
        match = ENDPOINT.search(section)
        if not match or heading not in section:
            continue
        response = section.split(heading, 1)[1].split("```", 1)[0]
        fields = []
        for name, _field_type in TABLE_ROW.findall(response):
            if name.strip() not in {"字段", "Field", "---"}:
                fields.append(name.strip(" `"))
        endpoints[(match.group(1), match.group(2))] = fields
    return endpoints


class BilingualApiReferenceTest(unittest.TestCase):
    def test_response_field_names_match_between_chinese_and_english(self):
        mismatches = []
        for zh_path in sorted((ROOT / "zh" / "api-reference").rglob("*.mdx")):
            en_path = ROOT / zh_path.relative_to(ROOT / "zh")
            if not en_path.exists():
                continue
            zh_fields = response_fields(zh_path, "zh")
            en_fields = response_fields(en_path, "en")
            for endpoint in sorted(set(zh_fields) | set(en_fields)):
                if sorted(zh_fields.get(endpoint, [])) != sorted(
                    en_fields.get(endpoint, [])
                ):
                    mismatches.append(
                        f"{zh_path.relative_to(ROOT)} {endpoint}: "
                        f"zh={zh_fields.get(endpoint)} en={en_fields.get(endpoint)}"
                    )

        self.assertEqual([], mismatches, "\n".join(mismatches))


if __name__ == "__main__":
    unittest.main()
