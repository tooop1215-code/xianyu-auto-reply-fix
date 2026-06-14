from __future__ import annotations

import argparse
import base64
import getpass
import json
import mimetypes
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from . import __version__
from .client import ApiClient, ApiError
from .config import CliConfig
from .output import render_response


CommandRunner = Callable[..., subprocess.CompletedProcess]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xianyu", description="闲鱼管理系统 CLI")
    parser.add_argument("--version", action="version", version=f"xianyu {__version__}")
    parser.add_argument("--config", help="配置文件路径，默认 ~/.config/xianyu-cli/config.json")
    parser.add_argument("--base-url", help="API 地址，默认 http://localhost:8000")
    parser.add_argument("--token", help="Bearer token；也可用 XIANYU_TOKEN")
    parser.add_argument("--output", choices=("json", "table"), default="json")

    subparsers = parser.add_subparsers(dest="group", required=True)
    _add_service_commands(subparsers)
    _add_auth_commands(subparsers)
    _add_account_commands(subparsers)
    _add_product_commands(subparsers)
    return parser


def run(
    argv: Optional[Sequence[str]] = None,
    *,
    client: Any = None,
    stdout: Any = None,
    stderr: Any = None,
    command_runner: Optional[CommandRunner] = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    parser = build_parser()
    args = parser.parse_args(argv)
    config = CliConfig.load(Path(args.config).expanduser() if args.config else None)
    if args.base_url:
        config.base_url = args.base_url
    if args.token:
        config.token = args.token
    api_client = client or ApiClient(config.base_url, token=config.token)
    runner = command_runner or subprocess.run

    try:
        result = args.handler(args, config, api_client, runner)
    except ApiError as exc:
        print(f"API error ({exc.status}): {exc}", file=stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted", file=stderr)
        return 130

    if result is not None:
        print(render_response(result, output=args.output), file=stdout)
    return 0


def main() -> None:
    raise SystemExit(run())


def _add_service_commands(subparsers: argparse._SubParsersAction) -> None:
    service = subparsers.add_parser("service", help="管理本地 Docker 服务")
    service_sub = service.add_subparsers(dest="service_cmd", required=True)
    for name in ("status", "start", "stop", "restart"):
        cmd = service_sub.add_parser(name)
        cmd.set_defaults(handler=_handle_service)
    logs = service_sub.add_parser("logs")
    logs.add_argument("-f", "--follow", action="store_true")
    logs.add_argument("service", nargs="?", default="xianyu-app")
    logs.set_defaults(handler=_handle_service)
    health = service_sub.add_parser("health")
    health.set_defaults(handler=lambda _args, _config, client, _runner: client.request("GET", "/health"))


def _add_auth_commands(subparsers: argparse._SubParsersAction) -> None:
    auth = subparsers.add_parser("auth", help="登录与 token 管理")
    auth_sub = auth.add_subparsers(dest="auth_cmd", required=True)
    login = auth_sub.add_parser("login")
    login.add_argument("-u", "--username")
    login.add_argument("-e", "--email")
    login.add_argument("-p", "--password")
    login.set_defaults(handler=_handle_auth_login)
    logout = auth_sub.add_parser("logout")
    logout.set_defaults(handler=_handle_auth_logout)
    token = auth_sub.add_parser("token")
    token.add_argument("--show", action="store_true")
    token.set_defaults(handler=_handle_auth_token)


def _add_account_commands(subparsers: argparse._SubParsersAction) -> None:
    account = subparsers.add_parser("account", help="闲鱼账号管理")
    account_sub = account.add_subparsers(dest="account_cmd", required=True)
    account_sub.add_parser("list").set_defaults(handler=lambda _args, _config, client, _runner: client.request("GET", "/cookies/details"))
    status = account_sub.add_parser("status")
    status.add_argument("account_id")
    status.set_defaults(handler=lambda args, _config, client, _runner: client.request("GET", f"/cookies/{args.account_id}/runtime-status"))
    enable = account_sub.add_parser("enable")
    enable.add_argument("account_id")
    enable.set_defaults(handler=lambda args, _config, client, _runner: client.request("PUT", f"/cookies/{args.account_id}/status", json_body={"enabled": True}))
    disable = account_sub.add_parser("disable")
    disable.add_argument("account_id")
    disable.set_defaults(handler=lambda args, _config, client, _runner: client.request("PUT", f"/cookies/{args.account_id}/status", json_body={"enabled": False}))


def _add_product_commands(subparsers: argparse._SubParsersAction) -> None:
    product = subparsers.add_parser("product", help="商品发布与管理")
    product_sub = product.add_subparsers(dest="product_cmd", required=True)

    product_sub.add_parser("all", help="列出全部本地商品").set_defaults(
        handler=lambda _args, _config, client, _runner: client.request("GET", "/items")
    )
    list_cmd = product_sub.add_parser("list", help="列出指定账号本地商品")
    list_cmd.add_argument("--account", required=True)
    list_cmd.add_argument("--sync", action="store_true", help="先从闲鱼账号同步远端商品，再读取本地列表")
    list_cmd.set_defaults(handler=_handle_product_list)

    detail = product_sub.add_parser("detail")
    detail.add_argument("account_id")
    detail.add_argument("item_id")
    detail.set_defaults(handler=lambda args, _config, client, _runner: client.request("GET", f"/items/{args.account_id}/{args.item_id}"))

    update = product_sub.add_parser("update")
    update.add_argument("account_id")
    update.add_argument("item_id")
    update.add_argument("--detail", required=True, help="详情文本，或 @path 从文件读取")
    update.set_defaults(handler=_handle_product_update)

    delete = product_sub.add_parser("delete")
    delete.add_argument("account_id")
    delete.add_argument("item_id")
    delete.add_argument("--yes", action="store_true")
    delete.set_defaults(handler=_handle_product_delete)

    search = product_sub.add_parser("search")
    search.add_argument("keyword")
    search.add_argument("--page", type=int, default=1)
    search.add_argument("--page-size", type=int, default=20)
    search.set_defaults(handler=_handle_product_search)

    pull = product_sub.add_parser("pull")
    pull.add_argument("account_id")
    pull.add_argument("--page", type=int)
    pull.add_argument("--page-size", type=int, default=20)
    pull.set_defaults(handler=_handle_product_pull)

    publish = product_sub.add_parser("publish", help="使用图片文件发布商品")
    publish.add_argument("--account", required=True)
    publish.add_argument("--title", required=True)
    publish.add_argument("--description", default="")
    publish.add_argument("--price", default="")
    publish.add_argument("--original-price", default="")
    publish.add_argument("--category", default="", help="类目名称或结构化类目 JSON，用于发布类目选择")
    publish.add_argument("--brand", default="")
    publish.add_argument("--condition", default="")
    publish.add_argument("--delivery", default="包邮")
    publish.add_argument("--postage", default="")
    publish.add_argument("--self-pickup", action="store_true")
    publish.add_argument("--image", action="append", required=True)
    publish.set_defaults(handler=_handle_product_publish)

    publish_json = product_sub.add_parser("publish-json", help="从 JSON 文件发布商品")
    publish_json.add_argument("file")
    publish_json.set_defaults(handler=_handle_product_publish_json)

    batch = product_sub.add_parser("batch-publish")
    batch.add_argument("--account", action="append", required=True)
    batch.add_argument("--material", action="append", type=int, required=True)
    batch.set_defaults(handler=lambda args, _config, client, _runner: client.request("POST", "/product-publish/batch", json_body={"account_ids": args.account, "material_ids": args.material}))

    batch_status = product_sub.add_parser("batch-status")
    batch_status.add_argument("batch_id")
    batch_status.set_defaults(handler=lambda args, _config, client, _runner: client.request("GET", f"/product-publish/batch/{args.batch_id}"))

    logs = product_sub.add_parser("publish-logs")
    logs.add_argument("--account")
    logs.add_argument("--status")
    logs.add_argument("--batch-id")
    logs.add_argument("--page", type=int, default=1)
    logs.add_argument("--page-size", type=int, default=20)
    logs.set_defaults(handler=_handle_publish_logs)

    _add_material_commands(product_sub)


def _add_material_commands(product_sub: argparse._SubParsersAction) -> None:
    materials = product_sub.add_parser("materials", help="商品发布素材")
    materials_sub = materials.add_subparsers(dest="materials_cmd", required=True)

    list_cmd = materials_sub.add_parser("list")
    list_cmd.add_argument("--page", type=int, default=1)
    list_cmd.add_argument("--page-size", type=int, default=20)
    list_cmd.set_defaults(handler=lambda args, _config, client, _runner: client.request("GET", "/product-materials", query={"page": args.page, "page_size": args.page_size}))

    create = materials_sub.add_parser("create")
    _add_material_fields(create, required=True)
    create.set_defaults(handler=_handle_material_create)

    detail = materials_sub.add_parser("detail")
    detail.add_argument("material_id", type=int)
    detail.set_defaults(handler=lambda args, _config, client, _runner: client.request("GET", f"/product-materials/{args.material_id}"))

    update = materials_sub.add_parser("update")
    update.add_argument("material_id", type=int)
    _add_material_fields(update, required=False)
    update.set_defaults(handler=_handle_material_update)

    delete = materials_sub.add_parser("delete")
    delete.add_argument("material_id", type=int)
    delete.add_argument("--yes", action="store_true")
    delete.set_defaults(handler=_handle_material_delete)


def _add_material_fields(parser: argparse.ArgumentParser, *, required: bool) -> None:
    parser.add_argument("--title", required=required)
    parser.add_argument("--description", required=required)
    parser.add_argument("--price", type=float)
    parser.add_argument("--original-price", type=float)
    parser.add_argument("--category")
    parser.add_argument("--image", action="append", dest="images")
    parser.add_argument("--delivery-method")
    parser.add_argument("--postage", type=float)
    parser.add_argument("--self-pickup", action="store_true", default=None)
    parser.add_argument("--brand")
    parser.add_argument("--condition")
    parser.add_argument("--remark")


def _handle_service(args: argparse.Namespace, config: CliConfig, _client: Any, runner: CommandRunner) -> Dict[str, Any]:
    compose = ["docker", "compose", "-f", config.compose_file]
    if args.service_cmd == "status":
        cmd = [*compose, "ps"]
    elif args.service_cmd == "start":
        cmd = [*compose, "up", "-d"]
    elif args.service_cmd == "stop":
        cmd = [*compose, "down"]
    elif args.service_cmd == "restart":
        cmd = [*compose, "restart"]
    elif args.service_cmd == "logs":
        cmd = [*compose, "logs"]
        if args.follow:
            cmd.append("-f")
        cmd.append(args.service)
    else:
        raise ValueError(f"unknown service command: {args.service_cmd}")

    completed = runner(cmd, cwd=config.workdir, text=True)
    return {"success": completed.returncode == 0, "command": cmd, "returncode": completed.returncode}


def _handle_auth_login(args: argparse.Namespace, config: CliConfig, client: Any, _runner: CommandRunner) -> Dict[str, Any]:
    password = args.password or getpass.getpass("Password: ")
    payload: Dict[str, Any] = {"password": password}
    if args.email:
        payload["email"] = args.email
    else:
        payload["username"] = args.username or input("Username: ")

    response = client.request("POST", "/login", json_body=payload)
    token = response.get("token") if isinstance(response, dict) else None
    if token:
        config.with_token(token).save()
        response = dict(response)
        response["token"] = _redact(token)
    return response


def _handle_auth_logout(_args: argparse.Namespace, config: CliConfig, _client: Any, _runner: CommandRunner) -> Dict[str, Any]:
    config.with_token(None).save()
    return {"success": True, "message": "token cleared"}


def _handle_auth_token(args: argparse.Namespace, config: CliConfig, _client: Any, _runner: CommandRunner) -> Dict[str, Any]:
    token = config.token
    if not token:
        return {"configured": False}
    return {"configured": True, "token": token if args.show else _redact(token)}


def _handle_product_update(args: argparse.Namespace, _config: CliConfig, client: Any, _runner: CommandRunner) -> Any:
    return client.request(
        "PUT",
        f"/items/{args.account_id}/{args.item_id}",
        json_body={"item_detail": _read_text_arg(args.detail)},
    )


def _handle_product_delete(args: argparse.Namespace, _config: CliConfig, client: Any, _runner: CommandRunner) -> Any:
    _confirm(args.yes, f"Delete item {args.item_id} from account {args.account_id}?")
    return client.request("DELETE", f"/items/{args.account_id}/{args.item_id}")


def _handle_product_search(args: argparse.Namespace, _config: CliConfig, client: Any, _runner: CommandRunner) -> Any:
    return client.request(
        "POST",
        "/items/search",
        json_body={"keyword": args.keyword, "page": args.page, "page_size": args.page_size},
    )


def _handle_product_list(args: argparse.Namespace, _config: CliConfig, client: Any, _runner: CommandRunner) -> Any:
    if args.sync:
        client.request("POST", "/items/get-all-from-account", json_body={"cookie_id": args.account})
    return client.request("GET", f"/items/{args.account}")


def _handle_product_pull(args: argparse.Namespace, _config: CliConfig, client: Any, _runner: CommandRunner) -> Any:
    if args.page is None:
        return client.request("POST", "/items/get-all-from-account", json_body={"cookie_id": args.account_id})
    return client.request(
        "POST",
        "/items/get-by-page",
        json_body={"cookie_id": args.account_id, "page_number": args.page, "page_size": args.page_size},
    )


def _handle_product_publish(args: argparse.Namespace, _config: CliConfig, client: Any, _runner: CommandRunner) -> Any:
    fields = {
        "cookie_id": args.account,
        "title": args.title,
        "description": args.description,
        "current_price": args.price,
        "original_price": args.original_price,
        "category": args.category,
        "brand": args.brand,
        "condition": args.condition,
        "delivery_choice": args.delivery,
        "post_price": args.postage,
        "can_self_pickup": "true" if args.self_pickup else "false",
    }
    files = []
    for image in args.image:
        path = Path(image)
        files.append(("images", str(path), path.read_bytes()))
    return client.multipart("/item-publish", fields=fields, files=files)


def _handle_product_publish_json(args: argparse.Namespace, _config: CliConfig, client: Any, _runner: CommandRunner) -> Any:
    return client.request("POST", "/product-publish", json_body=_read_json_file(args.file))


def _handle_publish_logs(args: argparse.Namespace, _config: CliConfig, client: Any, _runner: CommandRunner) -> Any:
    return client.request(
        "GET",
        "/publish-logs",
        query={
            "account_id": args.account,
            "status": args.status,
            "batch_id": args.batch_id,
            "page": args.page,
            "page_size": args.page_size,
        },
    )


def _handle_material_create(args: argparse.Namespace, _config: CliConfig, client: Any, _runner: CommandRunner) -> Any:
    return client.request("POST", "/product-materials", json_body=_material_payload(args, partial=False))


def _handle_material_update(args: argparse.Namespace, _config: CliConfig, client: Any, _runner: CommandRunner) -> Any:
    return client.request("PUT", f"/product-materials/{args.material_id}", json_body=_material_payload(args, partial=True))


def _handle_material_delete(args: argparse.Namespace, _config: CliConfig, client: Any, _runner: CommandRunner) -> Any:
    _confirm(args.yes, f"Delete material {args.material_id}?")
    return client.request("DELETE", f"/product-materials/{args.material_id}")


def _material_payload(args: argparse.Namespace, *, partial: bool) -> Dict[str, Any]:
    images = args.images
    if images is not None:
        images = _material_images_payload(images)

    candidates = {
        "title": args.title,
        "description": args.description,
        "price": args.price,
        "original_price": args.original_price,
        "category": args.category,
        "images": images,
        "delivery_method": args.delivery_method,
        "postage": args.postage,
        "can_self_pickup": args.self_pickup,
        "brand": args.brand,
        "condition": args.condition,
        "remark": args.remark,
    }
    if partial:
        return {key: value for key, value in candidates.items() if value is not None}
    return {key: value for key, value in candidates.items() if value is not None}


def _material_images_payload(images: Iterable[str]) -> List[Dict[str, Any]]:
    payload: List[Dict[str, Any]] = []
    for image in images:
        text = str(image or "").strip()
        if not text:
            continue
        if text.startswith(("http://", "https://")):
            payload.append({"url": text})
            continue
        if text.startswith("data:"):
            payload.append({"data": text})
            continue

        path = Path(text).expanduser()
        content = path.read_bytes()
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        payload.append(
            {
                "filename": path.name,
                "data": f"data:{mime_type};base64,{base64.b64encode(content).decode('ascii')}",
                "size": len(content),
                "type": mime_type,
            }
        )
    return payload


def _read_json_file(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_text_arg(value: str) -> str:
    if value.startswith("@"):
        return Path(value[1:]).read_text(encoding="utf-8")
    return value


def _confirm(yes: bool, prompt: str) -> None:
    if yes:
        return
    answer = input(f"{prompt} [y/N] ")
    if answer.lower() not in {"y", "yes"}:
        raise SystemExit(1)


def _redact(token: str) -> str:
    if len(token) <= 8:
        return "*" * len(token)
    return f"{token[:4]}...{token[-4:]}"


if __name__ == "__main__":
    main()
