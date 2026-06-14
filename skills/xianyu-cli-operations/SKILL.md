---
name: xianyu-cli-operations
description: Use this skill whenever the user is doing 即刻方案闲鱼店铺运营, product listing, product material preparation, account readiness checks, publishing, sync, logs, Docker health, or delivery-adjacent operational work in the forked xianyu-auto-reply-fix project. This skill should push agents to use the bundled CLI under `skills/xianyu-cli-operations/scripts/` for routine work and to follow a shop-operations SOP rather than editing databases, clicking the web UI, or inventing one-off scripts.
version: 1.1.0
author: OpenClaw Agent
license: MIT
metadata:
  openclaw:
    tags: [xianyu, shop-operations, cli, product-management, delivery-workflow]
---

# 闲鱼店铺 CLI 工作 SOP

## 定位

这个 skill 是“工作使用说明”，不是代码说明。它用于即刻方案的闲鱼店铺运营、商品管理、商品发布素材准备、账号状态检查、同步、日志排障和本地 Docker 服务维护。

默认原则：能用本 skill 打包的 CLI 完成的事情，就走 CLI；不要直接改 SQLite，不要直接点后台网页，不要临时写 curl 或散落脚本。

## 打包资源

CLI 实现随 skill 一起放在：

```bash
skills/xianyu-cli-operations/scripts/xianyu
skills/xianyu-cli-operations/scripts/xianyu_cli/
```

仓库根目录的 `./xianyu` 只是兼容入口，最终也会调用 skill 里的脚本。优先使用：

```bash
./xianyu --help
```

如果在 OpenClaw 只加载到 skill 目录，也可以直接运行：

```bash
python3 skills/xianyu-cli-operations/scripts/xianyu --help
```

## 工作前检查

进入 fork 仓库根目录：

```bash
cd /Users/bot/Documents/即刻方案
```

先确认本地服务健康：

```bash
./xianyu service health
```

再确认登录 token 是否存在：

```bash
./xianyu auth token
```

需要登录后台时再执行：

```bash
./xianyu auth login -u admin
```

不要把后台密码、闲鱼 cookie、token、买家信息、订单收货信息写入 git、skill、README、任务记录或长期知识库。

## 账号就绪判断

做商品同步、发布、发货、客服消息等动作前，先看账号：

```bash
./xianyu account list
./xianyu account status <account_id>
```

如果状态里出现 reconnecting、login backoff、missing token、session not ready、ws not ready 等情况，先向用户说明“账号会话未就绪”，不要直接发布或重试高风险动作。

启停账号要有明确意图：

```bash
./xianyu account enable <account_id>
./xianyu account disable <account_id>
```

## 商品管理流程

读本地商品：

```bash
./xianyu product all
./xianyu product list --account <account_id>
./xianyu product detail <account_id> <item_id>
```

搜索外部商品参考：

```bash
./xianyu product search "关键词" --page 1 --page-size 20
```

从账号同步商品到本地：

```bash
./xianyu product pull <account_id>
./xianyu product pull <account_id> --page 1 --page-size 20
```

更新本地商品详情：

```bash
./xianyu product update <account_id> <item_id> --detail "新的商品详情"
./xianyu product update <account_id> <item_id> --detail @/path/to/detail.txt
```

删除本地商品记录是破坏性动作，必须确认目标账号和商品 id：

```bash
./xianyu product delete <account_id> <item_id> --yes
```

## 商品素材流程

把待发布商品先沉淀成素材，便于复用、批量发布和复核：

```bash
./xianyu product materials list
./xianyu product materials create --title "素材标题" --description "描述" --price 19.9
./xianyu product materials detail <material_id>
./xianyu product materials update <material_id> --title "新标题"
./xianyu product materials delete <material_id> --yes
```

素材删除需要确认。素材创建和更新后，用 `detail` 读回，确认标题、价格、图片、发货方式无误。

## 发布流程

发布是真实店铺动作。执行前必须完成四件事：

1. `./xianyu service health` 为 healthy。
2. `./xianyu account status <account_id>` 显示账号会话可用。
3. 用户确认标题、价格、图片、描述、发货方式。
4. 明确这是要发布到真实闲鱼账号。

用图片文件发布：

```bash
./xianyu product publish \
  --account <account_id> \
  --title "标题" \
  --description "描述" \
  --price 19.9 \
  --image ./cover.jpg
```

用 JSON 发布：

```bash
./xianyu product publish-json ./payload.json
```

批量发布素材：

```bash
./xianyu product batch-publish --account <account_id> --material <material_id>
./xianyu product batch-status <batch_id>
./xianyu product publish-logs
```

遇到发布结果不明确时，不要盲目重试。先查 `publish-logs` 或 `batch-status`，再决定下一步。

## 服务运维

```bash
./xianyu service status
./xianyu service health
./xianyu service logs
./xianyu service restart
./xianyu service stop
./xianyu service start
```

优先用 `service health` 做快速确认。只有排障时才拉日志。重启服务前说明原因，避免打断正在运行的自动化任务。

## 输出规范

汇报给用户时，按这个结构：

```text
操作：
- 运行了哪些命令，隐藏密码/cookie/token

结果：
- 成功或失败
- 关键 id：account_id、item_id、material_id、batch_id

风险：
- 账号是否未就绪
- 是否涉及真实发布/删除/发货

下一步：
- 需要用户确认或需要继续执行的动作
```

默认保留 CLI 的 JSON 输出作为证据。需要人工扫描时可用：

```bash
./xianyu --output table product materials list
```

## 边界

- 不提供批量注册、规避风控、绕过平台规则、养号规避等建议。
- 不把隐私数据或凭据写入仓库。
- 不绕过 CLI 直接改库，除非 CLI 没有能力且用户明确要求。
- 不在账号未就绪时做发布、发货、客服发送等动作。
- 不对真实店铺执行破坏性或外部可见动作，除非用户目标明确。

## 完成前检查

- [ ] 服务健康已检查，或已明确报告服务不可用。
- [ ] 账号状态已检查，或该任务不需要账号。
- [ ] 没有输出或提交密码、cookie、token、买家隐私。
- [ ] 真实发布、删除、发货、启停账号等动作有明确确认。
- [ ] 用读回命令验证了结果。
