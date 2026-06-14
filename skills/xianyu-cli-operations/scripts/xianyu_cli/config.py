from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_COMPOSE_FILE = "docker-compose-cn.yml"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "xianyu-cli" / "config.json"


@dataclass
class CliConfig:
    base_url: str = DEFAULT_BASE_URL
    token: Optional[str] = None
    compose_file: str = DEFAULT_COMPOSE_FILE
    workdir: str = "."
    config_path: Path = DEFAULT_CONFIG_PATH

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "CliConfig":
        config_path = Path(
            path
            or os.environ.get("XIANYU_CONFIG")
            or DEFAULT_CONFIG_PATH
        ).expanduser()
        data: Dict[str, Any] = {}
        if config_path.exists():
            data = json.loads(config_path.read_text(encoding="utf-8") or "{}")

        return cls(
            base_url=os.environ.get("XIANYU_BASE_URL") or data.get("base_url") or DEFAULT_BASE_URL,
            token=os.environ.get("XIANYU_TOKEN") or data.get("token"),
            compose_file=os.environ.get("XIANYU_COMPOSE_FILE") or data.get("compose_file") or DEFAULT_COMPOSE_FILE,
            workdir=os.environ.get("XIANYU_WORKDIR") or data.get("workdir") or ".",
            config_path=config_path,
        )

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "base_url": self.base_url,
            "compose_file": self.compose_file,
            "workdir": self.workdir,
        }
        if self.token:
            data["token"] = self.token
        return data

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        try:
            self.config_path.chmod(0o600)
        except OSError:
            pass

    def with_token(self, token: Optional[str]) -> "CliConfig":
        self.token = token
        return self
