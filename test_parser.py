import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from douyin_creator_tracker import extract_metadata_from_json


class ParserTest(unittest.TestCase):
    def test_extracts_anchor_extra_product(self):
        payloads = [
            (
                "https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id=7644168958324866981",
                {
                    "aweme_detail": {
                        "aweme_id": "7644168958324866981",
                        "desc": "video title",
                        "create_time": 1770000000,
                        "anchorInfo": {
                            "extra": '[{"promotion_id":"7644481648544827146","product_id":"7644481649031317286","product_name":"孕妇夏季外穿凉感阔腿裤宽松显瘦不勒肚子休闲长裤"}]'
                        },
                    }
                },
            )
        ]
        title, publish_time, products = extract_metadata_from_json("7644168958324866981", payloads)
        self.assertEqual(title, "video title")
        self.assertTrue(publish_time)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].product_id, "7644481649031317286")
        self.assertIn("孕妇夏季", products[0].product_name)

    def test_extracts_ecom_product_detail(self):
        payloads = [
            (
                "https://www.douyin.com/ecom/product/detail/saas/pc/",
                {
                    "data": {
                        "product": {
                            "productId": "7644481649031317286",
                            "title": "冰丝阔腿裤",
                            "detailUrl": "https://www.douyin.com/product/7644481649031317286",
                        }
                    }
                },
            )
        ]
        _title, _publish_time, products = extract_metadata_from_json("", payloads)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].product_id, "7644481649031317286")
        self.assertEqual(products[0].product_name, "冰丝阔腿裤")


if __name__ == "__main__":
    unittest.main()
