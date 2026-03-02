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
    auto_pull: bool
    prompt_file: str | None
    branch_prompt_file: str | None
    worktree_parent: str
    symlink_opencode: bool
    symlink_idea: bool
    symlink_env: bool

    def to_json_dict(self) -> dict[str, object]:
        """Provide a stable serialization view for persistence operations.

        Args:
            None.

        Returns:
            A plain dictionary representation ready for JSON encoding.
        """
        return asdict(self)


VALID_CONFIG_KEYS = {
    "editor",
    "open_editor",
    "agent",
    "auto_plan",
    "auto_pull",
    "prompt_file",
    "branch_prompt_file",
    "worktree_parent",
    "symlink_opencode",
    "symlink_idea",
    "symlink_env",
}

BOOL_KEYS = {
    "open_editor",
    "auto_plan",
    "auto_pull",
    "symlink_opencode",
    "symlink_idea",
    "symlink_env",
}
OPTIONAL_PATH_KEYS = {"prompt_file", "branch_prompt_file"}


def config_path() -> Path:
    """Resolve the canonical config file path.

    Args:
        None.

    Returns:
        Absolute path for ``ocwt`` user configuration storage.
    """
    return Path.home() / ".config" / "ocwt" / "config.json"


def default_config() -> OcwtConfig:
    """Define baseline behavior when no user config exists.

    Args:
        None.

    Returns:
        Fully populated configuration with safe defaults.
    """
    default_editor = "cursor" if shutil.which("cursor") else "none"
    return OcwtConfig(
        editor=default_editor,
        open_editor=False,
        agent="build",
        auto_plan=False,
        auto_pull=False,
        prompt_file=None,
        branch_prompt_file=None,
        worktree_parent=".worktrees",
        symlink_opencode=True,
        symlink_idea=True,
        symlink_env=True,
    )


def _require_bool(key: str, value: object) -> bool:
    """Validate boolean config fields with key-aware errors.

    Args:
        key: Config key being validated.
        value: Untrusted value loaded from user input or disk.

    Returns:
        Parsed boolean value when validation succeeds.
    """
    if isinstance(value, bool):
        return value
    raise ValueError(f"{key} must be a boolean")


def _require_str(key: str, value: object) -> str:
    """Validate required string config fields.

    Args:
        key: Config key being validated.
        value: Untrusted value loaded from user input or disk.

    Returns:
        Trimmed non-empty string for persisted config use.
    """
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError(f"{key} must be a non-empty string")


def _optional_str(key: str, value: object) -> str | None:
    """Validate nullable string fields while preserving explicit nulls.

    Args:
        key: Config key being validated.
        value: Untrusted value loaded from user input or disk.

    Returns:
        ``None`` for null values, otherwise a validated string.
    """
    if value is None:
        return None
    return _require_str(key, value)


def normalize_bool_text(raw: str) -> bool:
    """Map CLI-friendly boolean text to strict boolean values.

    Args:
        raw: User-provided boolean text.

    Returns:
        Parsed boolean value accepted by config validation.
    """
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {raw!r}")


def parse_value_for_key(key: str, raw_value: str) -> object:
    """Parse a string CLI value into the expected config value type.

    Args:
        key: Config key being set.
        raw_value: Raw text provided through the CLI.

    Returns:
        Parsed scalar value compatible with config validation.
    """
    if key in BOOL_KEYS:
        return normalize_bool_text(raw_value)

    if key in OPTIONAL_PATH_KEYS:
        normalized = raw_value.strip()
        if normalized.lower() == "default":
            return None
        return _require_str(key, normalized)

    return _require_str(key, raw_value)


def validate_config(data: dict[str, object]) -> OcwtConfig:
    """Normalize and validate persisted config payloads.

    Args:
        data: Partial or full config payload loaded from disk.

    Returns:
        Validated ``OcwtConfig`` instance with defaults applied.
    """
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
        auto_pull=_require_bool("auto_pull", merged["auto_pull"]),
        prompt_file=_optional_str("prompt_file", merged["prompt_file"]),
        branch_prompt_file=_optional_str("branch_prompt_file", merged["branch_prompt_file"]),
        worktree_parent=_require_str("worktree_parent", merged["worktree_parent"]),
        symlink_opencode=_require_bool("symlink_opencode", merged["symlink_opencode"]),
        symlink_idea=_require_bool("symlink_idea", merged["symlink_idea"]),
        symlink_env=_require_bool("symlink_env", merged["symlink_env"]),
    )


def load_config() -> OcwtConfig:
    """Load user config while keeping invalid states explicit.

    Args:
        None.

    Returns:
        Effective configuration for runtime command behavior.
    """
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
    """Persist config updates atomically to the canonical path.

    Args:
        config: Validated configuration object to persist.

    Returns:
        Path where config was written, used for user feedback.
    """
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config.to_json_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def set_config_value(config: OcwtConfig, key: str, value: object) -> OcwtConfig:
    """Apply a single key update through full-schema validation.

    Args:
        config: Existing validated config.
        key: Config key to change.
        value: Parsed value to store.

    Returns:
        Updated validated config object.
    """
    if key not in VALID_CONFIG_KEYS:
        raise ValueError(f"Unknown config key: {key}")
    data = config.to_json_dict()
    data[key] = value
    return validate_config(data)


def reset_config_key(config: OcwtConfig, key: str) -> OcwtConfig:
    """Reset one config key back to its default value.

    Args:
        config: Existing validated config.
        key: Config key to reset.

    Returns:
        Updated validated config object with that key restored.
    """
    if key not in VALID_CONFIG_KEYS:
        raise ValueError(f"Unknown config key: {key}")
    data = config.to_json_dict()
    data[key] = default_config().to_json_dict()[key]
    return validate_config(data)
