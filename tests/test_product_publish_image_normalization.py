import unittest

import reply_server


class ProductPublishImageNormalizationTest(unittest.TestCase):
    def test_validate_publish_images_accepts_string_urls_and_data_urls(self):
        images = reply_server._validate_publish_images(
            [
                "https://example.com/cover.jpg",
                "data:image/png;base64,ZmFrZQ==",
            ]
        )

        self.assertEqual(images[0], {"url": "https://example.com/cover.jpg"})
        self.assertEqual(images[1], {"data": "data:image/png;base64,ZmFrZQ=="})


if __name__ == "__main__":
    unittest.main()
