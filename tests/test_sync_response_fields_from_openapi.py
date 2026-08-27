import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sync_response_fields_from_openapi.py"
SPEC = importlib.util.spec_from_file_location("sync_response_fields", SCRIPT)
sync = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(sync)


class SyncResponseFieldsTest(unittest.TestCase):
    def test_finance_holding_keeps_its_record_item_schema(self):
        specs = sync.load_specs("zh")
        spec, data = sync.find_data_schema(
            specs,
            "GET",
            "/openapi/v1/mc-account/finance/account/positions/holding",
        )

        self.assertIsNotNone(spec)
        self.assertIsNotNone(data)
        rendered = sync.render_response_block(spec, data, "zh")

        self.assertIn("| positionId | integer |", rendered)
        self.assertIn("| productCode | string |", rendered)
        self.assertIn("| couponId | string |", rendered)
        self.assertIn("| pauseRedeem | boolean |", rendered)
        self.assertNotIn("| transactionId | string |", rendered)

    def test_english_structure_uses_chinese_specs(self):
        zh_specs = sync.load_specs("zh")
        en_specs = sync.load_specs("en")

        self.assertEqual(zh_specs, en_specs)

    def test_string_enum_values_are_rendered_with_field_copy(self):
        specs = sync.load_specs("zh")
        spec, data = sync.find_data_schema(
            specs,
            "GET",
            "/openapi/v1/mc-account/finance/products/catalog",
        )

        rendered = sync.render_response_block(spec, data, "zh")

        self.assertIn("`CURRENT`", rendered)
        self.assertIn("`FIXED`", rendered)

    def test_map_placeholder_is_mdx_safe(self):
        schema = {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {"amount": {"type": "number"}},
            },
        }

        rendered = sync.render_response_block({}, schema, "zh")

        self.assertIn("`<key>`", rendered)
        self.assertNotIn("| <key> |", rendered)

    def test_inlined_map_is_enriched_without_cross_matching_page_records(self):
        specs = sync.load_specs("zh")
        spec, data = sync.find_data_schema(
            specs,
            "GET",
            "/openapi/v1/mc-account/fund/account/spot/positions/v2",
        )

        self.assertIsNotNone(spec)
        self.assertIsNotNone(data)
        rendered = sync.render_response_block(spec, data, "zh")

        self.assertIn("`symbolInfo.<key>`", rendered)
        self.assertIn("| contractSize | number |", rendered)


if __name__ == "__main__":
    unittest.main()
