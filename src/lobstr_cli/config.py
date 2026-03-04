from __future__ import annotations

import os
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
import tomli_w


def get_config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        base = Path(xdg)
    else:
        base = Path.home() / ".config"
    return base / "lobstr"


def get_config_path() -> Path:
    return get_config_dir() / "config.toml"


def load_config() -> dict:
    path = get_config_path()
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def _save_config(cfg: dict) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        tomli_w.dump(cfg, f)


def save_token(token: str) -> None:
    cfg = load_config()
    cfg.setdefault("auth", {})["token"] = token
    _save_config(cfg)


def get_token(override: str | None = None) -> str | None:
    if override:
        return override
    env = os.environ.get("LOBSTR_TOKEN")
    if env:
        return env
    cfg = load_config()
    return cfg.get("auth", {}).get("token")


def save_alias(name: str, hash_value: str) -> None:
    cfg = load_config()
    cfg.setdefault("aliases", {})[name] = hash_value
    _save_config(cfg)


def resolve_alias(value: str) -> str:
    if not value.startswith("@"):
        return value
    name = value[1:]
    cfg = load_config()
    aliases = cfg.get("aliases", {})
    if name in aliases:
        return aliases[name]
    return value
