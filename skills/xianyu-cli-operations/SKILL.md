---
name: xianyu-cli-operations
description: Use this skill whenever working in the xianyu-auto-reply-fix fork or 即刻方案 Xianyu operations and the user asks to manage accounts, products, product materials, publishing, logs, service health, Docker deployment, or shop operations. Prefer the project-local `./xianyu` CLI for all routine operations instead of editing the database, poking the web UI, or calling ad hoc curl commands.
version: 1.0.0
author: OpenClaw Agent
license: MIT
metadata:
  openclaw:
    tags: [xianyu, cli, shop-operations, product-management, docker]
---

# Xianyu CLI Operations

## Purpose

This skill is the operating guide for the forked `xianyu-auto-reply-fix` project used by the 即刻方案 workspace. It keeps agents on the safer path: use the repository's built-in `./xianyu` CLI as the main control plane, verify before acting, and avoid direct database or browser manipulation unless the CLI lacks the needed operation.

## Canonical Entry Point

Run commands from the repository root:

```bash
cd /Users/bot/Documents/即刻方案
./xianyu --help
```

For another clone, use that clone's root and keep the same `./xianyu` command shape.

The CLI defaults to:

- API base URL: `http://localhost:8000`
- Docker Compose file: `docker-compose-cn.yml`
- token config: `~/.config/xianyu-cli/config.json`

Supported overrides:

```bash
XIANYU_BASE_URL=http://localhost:8000 ./xianyu service health
XIANYU_TOKEN=<token> ./xianyu account list
XIANYU_CONFIG=/path/to/config.json ./xianyu auth token
```

Do not write passwords, cookies, tokens, or buyer data into project docs, git commits, task notes, or skill files.

## Default Workflow

1. Confirm you are in the fork repository root with `pwd` and `git remote -v`.
2. Check service health before operational work:

   ```bash
   ./xianyu service health
   ```

3. If an authenticated command fails, check token state:

   ```bash
   ./xianyu auth token
   ```

   Login only when needed:

   ```bash
   ./xianyu auth login -u admin
   ```

4. Prefer read-only discovery before mutating state.
5. For destructive or real marketplace actions, explain the target account/item/material and require explicit user confirmation unless the user already provided a clear instruction and the CLI command includes `--yes`.
6. After changes, run a read-back command that proves the expected state.

## Service Commands

Use these for local Docker service operations:

```bash
./xianyu service status
./xianyu service health
./xianyu service logs
./xianyu service restart
./xianyu service stop
./xianyu service start
```

Prefer `service health` for quick checks. Use logs only when investigating failures or startup behavior.

## Account Commands

Use these to inspect and control configured Xianyu accounts:

```bash
./xianyu account list
./xianyu account status <account_id>
./xianyu account enable <account_id>
./xianyu account disable <account_id>
```

Before publishing, syncing, sending messages, or delivery actions, inspect the account. If the runtime status reports reconnecting, login backoff, missing token, or no ready session, report that the account session must be repaired before live operations.

## Product Management

Read local product data:

```bash
./xianyu product all
./xianyu product list --account <account_id>
./xianyu product detail <account_id> <item_id>
```

Search public Xianyu items:

```bash
./xianyu product search "关键词" --page 1 --page-size 20
```

Sync products from an account into the local database:

```bash
./xianyu product pull <account_id>
./xianyu product pull <account_id> --page 1 --page-size 20
```

Update or remove local item records:

```bash
./xianyu product update <account_id> <item_id> --detail "新的商品详情"
./xianyu product update <account_id> <item_id> --detail @/path/to/detail.txt
./xianyu product delete <account_id> <item_id> --yes
```

Treat delete as destructive. Confirm the exact account and item id first when the user's instruction is not already explicit.

## Product Publishing

Publish with local image files:

```bash
./xianyu product publish \
  --account <account_id> \
  --title "标题" \
  --description "描述" \
  --price 19.9 \
  --image ./cover.jpg
```

Publish with a JSON payload:

```bash
./xianyu product publish-json ./payload.json
```

JSON payload shape:

```json
{
  "account_id": "account-id",
  "title": "商品标题",
  "description": "商品描述",
  "price": 19.9,
  "original_price": 29.9,
  "images": ["https://example.com/image.jpg"],
  "delivery_method": "包邮",
  "postage": 0,
  "can_self_pickup": false,
  "category": "虚拟商品",
  "brand": null,
  "condition": "全新"
}
```

Publishing is a live marketplace action. Before running publish commands:

1. Check `./xianyu account status <account_id>`.
2. Confirm the item title, price, images, and delivery method.
3. Confirm the user intends to publish to the live Xianyu account.
4. Run the command once; do not retry blindly after ambiguous failures.

## Product Materials And Batch Publishing

Manage reusable product material records:

```bash
./xianyu product materials list
./xianyu product materials create --title "素材标题" --description "描述" --price 19.9
./xianyu product materials detail <material_id>
./xianyu product materials update <material_id> --title "新标题"
./xianyu product materials delete <material_id> --yes
```

Batch publish existing materials to one or more accounts:

```bash
./xianyu product batch-publish --account <account_id> --material <material_id>
./xianyu product batch-status <batch_id>
./xianyu product publish-logs
```

Batch publish is also a live marketplace action. Confirm account ids, material ids, and total job count before starting.

## Output And Evidence

Use JSON output by default because it is durable and easy to quote back accurately. Use table output only for human scanning:

```bash
./xianyu --output table product materials list
```

When reporting results, include:

- command run, with secrets omitted
- success/failure state
- important ids such as account id, item id, material id, or batch id
- any non-blocking runtime warnings, such as account reconnecting or login backoff

## Boundaries

- Do not bypass the CLI with direct SQLite edits for routine operations.
- Do not scrape or automate the web UI when the CLI exposes the operation.
- Do not print, commit, or store raw cookies, passwords, tokens, buyer identities, addresses, payment details, or chat content unless the user explicitly asks and it is necessary for the task.
- Do not provide ban-evasion, mass-registration, or platform-rule circumvention advice.
- Do not trigger live publish, delivery, chat-send, account disable, or deletion commands without clear intent and a verification/read-back plan.

## Verification Checklist

Before claiming completion:

- [ ] `./xianyu service health` passed or the service issue was reported.
- [ ] Authenticated commands used an existing token or a fresh `auth login`.
- [ ] No secrets were printed or written to tracked files.
- [ ] For mutating commands, the target account/item/material was confirmed.
- [ ] A read-back command verified the resulting state.
