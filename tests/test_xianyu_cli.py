import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS_DIR = ROOT_DIR / "skills" / "xianyu-cli-operations" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS_DIR))

from xianyu_cli.client import ApiClient
from xianyu_cli.config import CliConfig
from xianyu_cli.main import run
from xianyu_cli.output import render_table


class FakeClient:
    def __init__(self):
        self.calls = []

    def request(self, method, path, *, json_body=None, query=None):
        self.calls.append(
            {
                "kind": "json",
                "method": method,
                "path": path,
                "json_body": json_body,
                "query": query,
            }
        )
        return {"success": True, "data": [{"id": "item-1", "title": "测试商品"}]}

    def multipart(self, path, *, fields, files):
        self.calls.append(
            {
                "kind": "multipart",
                "method": "POST",
                "path": path,
                "fields": fields,
                "files": [(field, Path(filename).name) for field, filename, _content in files],
            }
        )
        return {"success": True, "message": "published"}


class XianyuCliTest(unittest.TestCase):
    def test_config_uses_env_over_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(
                json.dumps({"base_url": "http://file", "token": "file-token"}),
                encoding="utf-8",
            )

            with mock.patch.dict(
                os.environ,
                {"XIANYU_BASE_URL": "http://env", "XIANYU_TOKEN": "env-token"},
                clear=False,
            ):
                config = CliConfig.load(config_path)

        self.assertEqual(config.base_url, "http://env")
        self.assertEqual(config.token, "env-token")

    def test_api_client_adds_bearer_token_and_json_body(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"ok": true}'

            @property
            def headers(self):
                return {"Content-Type": "application/json"}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["method"] = request.get_method()
            captured["body"] = request.data
            captured["auth"] = request.headers.get("Authorization")
            captured["content_type"] = request.headers.get("Content-type")
            captured["timeout"] = timeout
            return FakeResponse()

        client = ApiClient("http://localhost:8000", token="secret", opener=fake_urlopen)
        result = client.request("POST", "/product-publish", json_body={"title": "A"})

        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["url"], "http://localhost:8000/product-publish")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["auth"], "Bearer secret")
        self.assertEqual(json.loads(captured["body"].decode("utf-8")), {"title": "A"})
        self.assertIn("application/json", captured["content_type"])
        self.assertEqual(captured["timeout"], 60)

    def test_api_client_builds_multipart_request_for_image_publish(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"success": true}'

            @property
            def headers(self):
                return {"Content-Type": "application/json"}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["method"] = request.get_method()
            captured["body"] = request.data
            captured["content_type"] = request.headers.get("Content-type")
            captured["auth"] = request.headers.get("Authorization")
            return FakeResponse()

        client = ApiClient("http://localhost:8000", token="secret", opener=fake_urlopen)
        result = client.multipart(
            "/item-publish",
            fields={"cookie_id": "acc-1", "title": "标题"},
            files=[("images", "cover.jpg", b"image-bytes")],
        )

        self.assertEqual(result, {"success": True})
        body = captured["body"]
        self.assertEqual(captured["url"], "http://localhost:8000/item-publish")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["auth"], "Bearer secret")
        self.assertIn("multipart/form-data", captured["content_type"])
        self.assertIn(b'name="cookie_id"', body)
        self.assertIn(b"acc-1", body)
        self.assertIn(b'filename="cover.jpg"', body)
        self.assertIn(b"image-bytes", body)

    def test_auth_login_saves_token_but_redacts_output(self):
        class LoginClient:
            def request(self, method, path, *, json_body=None, query=None):
                self.call = {
                    "method": method,
                    "path": path,
                    "json_body": json_body,
                    "query": query,
                }
                return {"success": True, "token": "dummy-redaction-token", "username": "admin"}

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            client = LoginClient()
            stdout = io.StringIO()
            code = run(
                [
                    "--config",
                    str(config_path),
                    "auth",
                    "login",
                    "-u",
                    "admin",
                    "-p",
                    "password",
                ],
                client=client,
                stdout=stdout,
            )
            saved = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(client.call["method"], "POST")
        self.assertEqual(client.call["path"], "/login")
        self.assertEqual(client.call["json_body"], {"password": "password", "username": "admin"})
        self.assertEqual(saved["token"], "dummy-redaction-token")
        self.assertNotIn("dummy-redaction-token", stdout.getvalue())
        self.assertIn("dumm...oken", stdout.getvalue())

    def test_product_publish_json_command_posts_file_payload(self):
        fake_client = FakeClient()
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            payload_path = Path(tmpdir) / "payload.json"
            payload_path.write_text(
                json.dumps(
                    {
                        "account_id": "acc-1",
                        "title": "测试商品",
                        "description": "描述",
                        "images": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            code = run(
                ["product", "publish-json", str(payload_path)],
                client=fake_client,
                stdout=stdout,
            )

        self.assertEqual(code, 0)
        self.assertEqual(fake_client.calls[0]["method"], "POST")
        self.assertEqual(fake_client.calls[0]["path"], "/product-publish")
        self.assertEqual(fake_client.calls[0]["json_body"]["account_id"], "acc-1")
        self.assertIn("success", stdout.getvalue())

    def test_product_publish_with_images_uses_multipart_endpoint(self):
        fake_client = FakeClient()
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "cover.jpg"
            image_path.write_bytes(b"image-bytes")
            code = run(
                [
                    "product",
                    "publish",
                    "--account",
                    "acc-1",
                    "--title",
                    "测试商品",
                    "--category",
                    "手机",
                    "--description",
                    "描述",
                    "--price",
                    "19.9",
                    "--image",
                    str(image_path),
                ],
                client=fake_client,
                stdout=stdout,
            )

        self.assertEqual(code, 0)
        self.assertEqual(fake_client.calls[0]["kind"], "multipart")
        self.assertEqual(fake_client.calls[0]["path"], "/item-publish")
        self.assertEqual(fake_client.calls[0]["fields"]["cookie_id"], "acc-1")
        self.assertEqual(fake_client.calls[0]["fields"]["category"], "手机")
        self.assertEqual(fake_client.calls[0]["fields"]["current_price"], "19.9")
        self.assertEqual(fake_client.calls[0]["files"], [("images", "cover.jpg")])

    def test_product_management_commands_map_to_expected_endpoints(self):
        fake_client = FakeClient()
        commands = [
            (["product", "list", "--account", "acc-1"], "GET", "/items/acc-1", None),
            (["product", "all"], "GET", "/items", None),
            (["product", "detail", "acc-1", "item-1"], "GET", "/items/acc-1/item-1", None),
            (
                ["product", "update", "acc-1", "item-1", "--detail", "新详情"],
                "PUT",
                "/items/acc-1/item-1",
                {"item_detail": "新详情"},
            ),
            (["product", "delete", "acc-1", "item-1", "--yes"], "DELETE", "/items/acc-1/item-1", None),
            (
                ["product", "search", "手机", "--page", "2", "--page-size", "10"],
                "POST",
                "/items/search",
                {"keyword": "手机", "page": 2, "page_size": 10},
            ),
            (
                ["product", "pull", "acc-1", "--page", "3", "--page-size", "30"],
                "POST",
                "/items/get-by-page",
                {"cookie_id": "acc-1", "page_number": 3, "page_size": 30},
            ),
        ]

        for argv, method, path, body in commands:
            fake_client.calls.clear()
            code = run(argv, client=fake_client, stdout=io.StringIO())
            self.assertEqual(code, 0, argv)
            self.assertEqual(fake_client.calls[0]["method"], method, argv)
            self.assertEqual(fake_client.calls[0]["path"], path, argv)
            self.assertEqual(fake_client.calls[0]["json_body"], body, argv)

    def test_product_list_with_sync_pulls_remote_items_before_reading_local_list(self):
        fake_client = FakeClient()
        code = run(
            ["product", "list", "--account", "acc-1", "--sync"],
            client=fake_client,
            stdout=io.StringIO(),
        )

        self.assertEqual(code, 0)
        self.assertEqual(
            fake_client.calls,
            [
                {
                    "kind": "json",
                    "method": "POST",
                    "path": "/items/get-all-from-account",
                    "json_body": {"cookie_id": "acc-1"},
                    "query": None,
                },
                {
                    "kind": "json",
                    "method": "GET",
                    "path": "/items/acc-1",
                    "json_body": None,
                    "query": None,
                },
            ],
        )

    def test_material_commands_map_to_expected_endpoints(self):
        fake_client = FakeClient()
        commands = [
            (["product", "materials", "list", "--page", "2"], "GET", "/product-materials", None, {"page": 2, "page_size": 20}),
            (
                ["product", "materials", "create", "--title", "素材", "--description", "描述", "--price", "9.9"],
                "POST",
                "/product-materials",
                {"title": "素材", "description": "描述", "price": 9.9},
                None,
            ),
            (["product", "materials", "detail", "7"], "GET", "/product-materials/7", None, None),
            (
                ["product", "materials", "update", "7", "--title", "新素材"],
                "PUT",
                "/product-materials/7",
                {"title": "新素材"},
                None,
            ),
            (["product", "materials", "delete", "7", "--yes"], "DELETE", "/product-materials/7", None, None),
        ]

        for argv, method, path, body, query in commands:
            fake_client.calls.clear()
            code = run(argv, client=fake_client, stdout=io.StringIO())
            self.assertEqual(code, 0, argv)
            self.assertEqual(fake_client.calls[0]["method"], method, argv)
            self.assertEqual(fake_client.calls[0]["path"], path, argv)
            self.assertEqual(fake_client.calls[0]["json_body"], body, argv)
            self.assertEqual(fake_client.calls[0]["query"], query, argv)

    def test_material_create_embeds_image_file_payload(self):
        fake_client = FakeClient()
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "cover.png"
            image_path.write_bytes(b"fake-png-bytes")

            code = run(
                [
                    "product",
                    "materials",
                    "create",
                    "--title",
                    "素材",
                    "--description",
                    "描述",
                    "--image",
                    str(image_path),
                ],
                client=fake_client,
                stdout=io.StringIO(),
            )

        self.assertEqual(code, 0)
        image_payload = fake_client.calls[0]["json_body"]["images"][0]
        self.assertEqual(image_payload["filename"], "cover.png")
        self.assertEqual(image_payload["size"], len(b"fake-png-bytes"))
        self.assertEqual(image_payload["type"], "image/png")
        self.assertTrue(image_payload["data"].startswith("data:image/png;base64,"))

    def test_render_table_uses_selected_columns(self):
        text = render_table(
            [{"id": "1", "title": "短标题", "price": 19.9}],
            columns=["id", "title"],
        )

        self.assertIn("id", text)
        self.assertIn("title", text)
        self.assertIn("短标题", text)
        self.assertNotIn("19.9", text)


if __name__ == "__main__":
    unittest.main()
