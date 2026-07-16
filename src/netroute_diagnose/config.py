from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib.resources import files

import yaml


class ConfigError(ValueError):
    """Raised when a diagnostic configuration is invalid."""


def bundled_config_path() -> Path:
    return Path(str(files("netroute_diagnose").joinpath("profiles/default.yaml")))


def load_yaml(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"File not found: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {config_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Top-level YAML value must be a mapping: {config_path}")
    return data


def load_diagnostic_config(path: str | Path) -> dict[str, Any]:
    data = load_yaml(path)
    apps = data.get("apps")
    if not isinstance(apps, list) or not apps:
        raise ConfigError("The diagnostic config requires a non-empty 'apps' list")

    for app in apps:
        if not isinstance(app, dict) or not app.get("name"):
            raise ConfigError("Each app entry requires a name")
        domains = app.get("domains")
        if not isinstance(domains, list) or not domains:
            raise ConfigError(f"App '{app['name']}' requires a non-empty domains list")
        for item in domains:
            if not isinstance(item, dict) or not item.get("domain"):
                raise ConfigError(f"App '{app['name']}' has an invalid domain entry")
            expected = str(item.get("expected", "UNKNOWN")).upper()
            if expected not in {"DIRECT", "PROXY", "REJECT", "UNKNOWN"}:
                raise ConfigError(
                    f"Unsupported expectation '{expected}' for {item['domain']}"
                )
            item["expected"] = expected
    return data
