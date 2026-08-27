import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def endpoint_section(path: Path, endpoint: str) -> str:
    text = path.read_text()
    return next(
        part
        for part in re.split(r"(?=^## )", text, flags=re.M)
        if f"`GET {endpoint}`" in part
    )


class ApiContractBoundariesTest(unittest.TestCase):
    def test_documented_parameter_and_missing_symbol_boundaries(self):
        zh_recent = endpoint_section(
            ROOT / "zh" / "api-reference" / "trade" / "deals.mdx",
            "/openapi/v1/mc-trade/trade/deals/history/recent",
        )
        en_recent = endpoint_section(
            ROOT / "api-reference" / "trade" / "deals.mdx",
            "/openapi/v1/mc-trade/trade/deals/history/recent",
        )
        self.assertIn("范围为 1～100", zh_recent)
        self.assertIn("不存在时返回空数组", zh_recent)
        self.assertIn("range is 1 to 100", en_recent)
        self.assertIn("returns an empty array", en_recent)

        zh_static = endpoint_section(
            ROOT / "zh" / "api-reference" / "trade" / "trading.mdx",
            "/openapi/v1/mc-trade/trade/symbol/staticConfig",
        )
        en_static = endpoint_section(
            ROOT / "api-reference" / "trade" / "trading.mdx",
            "/openapi/v1/mc-trade/trade/symbol/staticConfig",
        )
        self.assertIn("不存在的 `symbol` 可能不出现在响应数组中", zh_static)
        self.assertIn("`mt5` 和 `risk` 为 `null`", zh_static)
        self.assertIn("An unknown symbol may be omitted from the response array", en_static)
        self.assertIn("`mt5` and `risk` are `null`", en_static)

        account_endpoints = [
            (
                "/openapi/v1/mc-trade/account/contract-volume-by-symbol",
                "longVolume` 和 `shortVolume` 均返回 `0`",
                "`longVolume` and `shortVolume` are both `0`",
            ),
            (
                "/openapi/v1/mc-trade/account/contract-notional-by-symbol",
                "longNotional` 和 `shortNotional` 均返回 `0`",
                "`longNotional` and `shortNotional` are both `0`",
            ),
        ]
        for endpoint, zh_copy, en_copy in account_endpoints:
            zh_section = endpoint_section(
                ROOT / "zh" / "api-reference" / "trade" / "trading-account.mdx",
                endpoint,
            )
            en_section = endpoint_section(
                ROOT / "api-reference" / "trade" / "trading-account.mdx",
                endpoint,
            )
            self.assertIn(zh_copy, zh_section)
            self.assertIn(en_copy, en_section)

        zh_market = (ROOT / "zh" / "api-reference" / "aggregator" / "market-data.mdx").read_text()
        en_market = (ROOT / "api-reference" / "aggregator" / "market-data.mdx").read_text()
        self.assertIn("| pageSize | integer | 否 | 每页条数，最大 100 |", zh_market)
        self.assertIn("| limit | integer | 否 | 单次最大返回条数，最大 500 |", zh_market)
        self.assertIn("| pageSize | integer | No | Page size; maximum 100 |", en_market)
        self.assertIn("| limit | integer | No | Max rows per response; maximum 500 |", en_market)

    def test_historical_deal_identifiers_are_strings_in_spec_and_docs(self):
        spec = json.loads((ROOT / "openapi" / "mc-trade.json").read_text())
        properties = spec["components"]["schemas"]["UserDealsRspV2"]["properties"]
        identifiers = ("order", "deal", "positionID", "login")
        for name in identifiers:
            self.assertEqual("string", properties[name].get("type"), name)
            self.assertNotEqual("int64", properties[name].get("format"), name)

        for page in (
            ROOT / "zh" / "api-reference" / "trade" / "deals.mdx",
            ROOT / "api-reference" / "trade" / "deals.mdx",
        ):
            section = endpoint_section(
                page,
                "/openapi/v1/mc-trade/trade/deals/history/v3",
            )
            for name in identifiers:
                row = next(line for line in section.splitlines() if line.startswith(f"| {name} |"))
                self.assertIn("| string |", row, f"{page.name}:{name}")


if __name__ == "__main__":
    unittest.main()
