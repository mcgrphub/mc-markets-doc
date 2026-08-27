import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUERY_WITHOUT_CONTINUATION = re.compile(
    r'X-Nonce:[^\n]*"\n\s+--data-urlencode'
)
JSON_BODY = re.compile(r"-d '(\{.*?\})'", re.S)
CURL_URL_PLACEHOLDER = re.compile(r'curl[^\n]*https://[^"\n]*\{[A-Za-z][A-Za-z0-9]*\}')


class ApiReferenceExamplesTest(unittest.TestCase):
    def api_pages(self):
        yield from sorted((ROOT / "zh" / "api-reference").rglob("*.mdx"))
        yield from sorted((ROOT / "api-reference").rglob("*.mdx"))

    def test_query_curl_lines_have_shell_continuations(self):
        offenders = []
        for path in self.api_pages():
            if QUERY_WITHOUT_CONTINUATION.search(path.read_text()):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual([], offenders)

    def test_curl_urls_do_not_leave_path_placeholders(self):
        offenders = []
        for path in self.api_pages():
            if CURL_URL_PLACEHOLDER.search(path.read_text()):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual([], offenders)

    def test_inline_json_request_bodies_are_valid_and_not_generic(self):
        offenders = []
        for path in self.api_pages():
            text = path.read_text()
            if "see fields above" in text:
                offenders.append(f"{path.relative_to(ROOT)}: generic body")
            for body in JSON_BODY.findall(text):
                try:
                    json.loads(body)
                except json.JSONDecodeError as exc:
                    offenders.append(f"{path.relative_to(ROOT)}: {exc}")
        self.assertEqual([], offenders)

    def test_required_trade_history_end_time_is_in_examples(self):
        targets = [
            (
                "trade/deals.mdx",
                "`GET /openapi/v1/mc-trade/trade/deals/history/v3`",
            ),
            (
                "trade/trading-account.mdx",
                "`GET /openapi/v1/mc-trade/account/positions`",
            ),
            (
                "trade/orders.mdx",
                "`GET /openapi/v1/mc-trade/trade/orders/history/v3`",
            ),
        ]
        for locale_root in (ROOT / "zh" / "api-reference", ROOT / "api-reference"):
            for relative_path, endpoint_marker in targets:
                text = (locale_root / relative_path).read_text()
                section = next(
                    part
                    for part in re.split(r"(?=^## )", text, flags=re.M)
                    if endpoint_marker in part
                )
                self.assertIn('--data-urlencode "to=', section)


if __name__ == "__main__":
    unittest.main()
