import unittest
import importlib
import sys
import types


_INSTALLED_STUBS = []


def _install_stub(name, module):
    if name in sys.modules:
        return
    try:
        importlib.import_module(name)
        return
    except ImportError:
        pass
    sys.modules[name] = module
    _INSTALLED_STUBS.append(name)


_install_stub(
    "aiohttp",
    types.SimpleNamespace(
        BasicAuth=object,
        BaseConnector=object,
        ClientResponse=object,
        ClientSession=object,
        ClientTimeout=lambda *args, **kwargs: object(),
        FormData=lambda *args, **kwargs: object(),
    ),
)
_install_stub(
    "loguru",
    types.SimpleNamespace(
        logger=types.SimpleNamespace(
            info=lambda *args, **kwargs: None,
            warning=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
            debug=lambda *args, **kwargs: None,
        )
    ),
)
_install_stub(
    "utils.xianyu_utils",
    types.SimpleNamespace(
        generate_sign=lambda *args, **kwargs: "sign",
        trans_cookies=lambda cookies: {},
    ),
)
from utils.item_publisher import ItemPublisher

for _module_name in _INSTALLED_STUBS:
    sys.modules.pop(_module_name, None)


class ItemPublisherCategoryTest(unittest.TestCase):
    def _publisher(self):
        return object.__new__(ItemPublisher)

    def _base_payload_args(self):
        return {
            "title": "测试商品",
            "description": "测试描述",
            "uploaded_images": [{"url": "https://example.com/a.jpg", "width": 800, "height": 800}],
            "channel_res": {
                "data": {
                    "categoryPredictResult": {
                        "catId": "old-cat",
                        "catName": "旧类目",
                        "channelCatId": "old-channel",
                        "tbCatId": "old-tb",
                    },
                    "cardList": [],
                }
            },
            "location": {
                "area": "测试区",
                "city": "测试市",
                "divisionId": 1,
                "longitude": 118,
                "latitude": 31,
                "poiId": "poi",
                "poi": "测试地址",
                "prov": "测试省",
            },
            "current_price": 19.9,
            "original_price": None,
            "delivery_choice": "包邮",
            "post_price": None,
            "can_self_pickup": False,
        }

    def test_build_publish_payload_uses_structured_category_hint(self):
        publisher = self._publisher()
        args = self._base_payload_args()

        payload = publisher._build_publish_payload(
            **args,
            category_hint={
                "catId": "50024400",
                "catName": "手机",
                "channelCatId": "1001",
                "tbCatId": "150704",
            },
        )

        self.assertEqual(
            payload["itemCatDTO"],
            {
                "catId": "50024400",
                "catName": "手机",
                "channelCatId": "1001",
                "tbCatId": "150704",
            },
        )

    def test_build_publish_payload_matches_string_category_hint_against_card_values(self):
        publisher = self._publisher()
        args = self._base_payload_args()
        args["channel_res"] = {
            "data": {
                "categoryPredictResult": {},
                "cardList": [
                    {
                        "cardData": {
                            "propertyId": "category",
                            "propertyName": "类目",
                            "valuesList": [
                                {
                                    "catName": "图书",
                                    "channelCatId": "book-channel",
                                    "tbCatId": "book-tb",
                                },
                                {
                                    "catName": "手机",
                                    "channelCatId": "phone-channel",
                                    "tbCatId": "phone-tb",
                                },
                            ],
                        }
                    }
                ],
            }
        }

        payload = publisher._build_publish_payload(**args, category_hint="手机")

        self.assertEqual(payload["itemCatDTO"]["catName"], "手机")
        self.assertEqual(payload["itemCatDTO"]["catId"], "phone-channel")
        self.assertEqual(payload["itemCatDTO"]["channelCatId"], "phone-channel")
        self.assertEqual(payload["itemCatDTO"]["tbCatId"], "phone-tb")
        self.assertEqual(payload["itemLabelExtList"][0]["text"], "手机")


if __name__ == "__main__":
    unittest.main()
