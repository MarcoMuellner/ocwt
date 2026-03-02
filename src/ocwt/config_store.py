from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class OcwtConfig:
    editor: str
    open_editor: bool
    agent: str
    auto_plan: bool
    prompt_file: str | None
    branch_prompt_file: str | None
    worktree_parent: str
    symlink_opencode: bool
    symlink_idea: bool
    symlink_env: bool

    def to_json_dict(self) -> dict[str, object]:
        return asdict(self)


VALID_CONFIG_KEYS = {
    "editor",
    "open_editor",
    "agent",
    "auto_plan",
    "prompt_file",
    "branch_prompt_file",
    "worktree_parent",
    "symlink_opencode",
    "symlink_idea",
    "symlink_env",
}

BOOL_KEYS = {"open_editor", "auto_plan", "symlink_opencode", "symlink_idea", "symlink_env"}
OPTIONAL_PATH_KEYS = {"prompt_file", "branch_prompt_file"}


def config_path() -> Path:
    return Path.home() / ".config" / "ocwt" / "config.json"


def default_config() -> OcwtConfig:
    default_editor = "cursor" if shutil.which("cursor") else "none"
    return OcwtConfig(
        editor=default_editor,
        open_editor=False,
        agent="build",
        auto_plan=False,
        prompt_file=None,
        branch_prompt_file=None,
        worktree_parent=".worktrees",
        symlink_opencode=True,
        symlink_idea=True,
        symlink_env=True,
    )


def _require_bool(key: str, value: object) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"{key} must be a boolean")


def _require_str(key: str, value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError(f"{key} must be a non-empty string")


def _optional_str(key: str, value: object) -> str | None:
    if value is None:
        return None
    return _require_str(key, value)


def normalize_bool_text(raw: str) -> bool:
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {raw!r}")


def parse_value_for_key(key: str, raw_value: str) -> object:
    if key in BOOL_KEYS:
        return normalize_bool_text(raw_value)

    if key in OPTIONAL_PATH_KEYS:
        normalized = raw_value.strip()
        if normalized.lower() == "default":
            return None
        return _require_str(key, normalized)

    return _require_str(key, raw_value)


def validate_config(data: dict[str, object]) -> OcwtConfig:
    defaults = default_config().to_json_dict()
    merged: dict[str, object] = {**defaults, **data}

    unknown = set(merged) - VALID_CONFIG_KEYS
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"Unknown config keys: {names}")

    return OcwtConfig(
        editor=_require_str("editor", merged["editor"]),
        open_editor=_require_bool("open_editor", merged["open_editor"]),
        agent=_require_str("agent", merged["agent"]),
        auto_plan=_require_bool("auto_plan", merged["auto_plan"]),
        prompt_file=_optional_str("prompt_file", merged["prompt_file"]),
        branch_prompt_file=_optional_str("branch_prompt_file", merged["branch_prompt_file"]),
        worktree_parent=_require_str("worktree_parent", merged["worktree_parent"]),
        symlink_opencode=_require_bool("symlink_opencode", merged["symlink_opencode"]),
        symlink_idea=_require_bool("symlink_idea", merged["symlink_idea"]),
        symlink_env=_require_bool("symlink_env", merged["symlink_env"]),
    )


def load_config() -> OcwtConfig:
    path = config_path()
    if not path.exists():
        return default_config()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid config JSON in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError(f"Invalid config structure in {path}: expected JSON object")

    return validate_config(raw)


def save_config(config: OcwtConfig) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config.to_json_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def set_config_value(config: OcwtConfig, key: str, value: object) -> OcwtConfig:
    if key not in VALID_CONFIG_KEYS:
        raise ValueError(f"Unknown config key: {key}")
    data = config.to_json_dict()
    data[key] = value
    return validate_config(data)


def reset_config_key(config: OcwtConfig, key: str) -> OcwtConfig:
    if key not in VALID_CONFIG_KEYS:
        raise ValueError(f"Unknown config key: {key}")
    data = config.to_json_dict()
    data[key] = default_config().to_json_dict()[key]
    return validate_config(data)
