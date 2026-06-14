# Xianyu CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a project-local `xianyu` command line interface for service control, authentication, and immediate product publishing/management workflows.

**Architecture:** Add a small Python package under `xianyu_cli/` that talks to the existing FastAPI server over HTTP and shells out to Docker Compose only for service lifecycle commands. Keep credentials in local config/Keychain-adjacent storage by default and never write secrets to repo docs. Add a root executable script `xianyu` so the CLI works from this checkout without packaging first.

**Tech Stack:** Python 3 standard library `argparse`, `json`, `urllib`, `subprocess`, `pathlib`; optional existing runtime only. Unit tests use `unittest` and mocked HTTP/command runners.

---

### Task 1: CLI Core

**Files:**
- Create: `xianyu_cli/__init__.py`
- Create: `xianyu_cli/client.py`
- Create: `xianyu_cli/config.py`
- Create: `xianyu_cli/output.py`
- Create: `xianyu_cli/main.py`
- Create: `xianyu`
- Test: `tests/test_xianyu_cli.py`

- [ ] Write failing tests for config loading, auth header construction, JSON body requests, multipart image requests, and table rendering.
- [ ] Run `python3 -m unittest tests.test_xianyu_cli -v` and verify failures are due to missing CLI modules.
- [ ] Implement the minimal CLI core.
- [ ] Re-run `python3 -m unittest tests.test_xianyu_cli -v` and verify it passes.

### Task 2: Product Commands

**Commands:**
- `xianyu product list --account ID`
- `xianyu product all`
- `xianyu product detail ACCOUNT_ID ITEM_ID`
- `xianyu product update ACCOUNT_ID ITEM_ID --detail TEXT_OR_FILE`
- `xianyu product delete ACCOUNT_ID ITEM_ID --yes`
- `xianyu product search KEYWORD --page N --page-size N`
- `xianyu product pull ACCOUNT_ID`
- `xianyu product publish --account ID --title TEXT --description TEXT --price N --image PATH...`
- `xianyu product publish-json FILE`
- `xianyu product materials list/create/detail/update/delete`
- `xianyu product batch-publish --account ID... --material ID...`
- `xianyu product publish-logs`

- [ ] Write tests proving each command maps to the expected FastAPI endpoint, method, body, and query parameters.
- [ ] Implement command handlers as thin wrappers around `ApiClient`.
- [ ] Verify command help renders and tests pass.

### Task 3: Service And Auth Commands

**Commands:**
- `xianyu service status/start/stop/restart/logs/health`
- `xianyu auth login/logout/token`
- `xianyu account list/status/enable/disable`

- [ ] Write tests for command routing and confirmation guards.
- [ ] Implement handlers.
- [ ] Verify local smoke commands against `http://localhost:8000`.

### Task 4: Documentation And Verification

- [ ] Add a short CLI usage section to `README.md`.
- [ ] Run unit tests.
- [ ] Run smoke checks: `./xianyu --help`, `./xianyu service health`, `./xianyu product --help`.
- [ ] Report remaining risks around live product publishing requiring a valid logged-in Xianyu account.
