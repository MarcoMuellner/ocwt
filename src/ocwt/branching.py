from __future__ import annotations

import re

VALID_PREFIXES = ("feat", "bugfix", "fix", "chore", "docs", "refactor", "test", "perf")
VALID_BRANCH_RE = re.compile(
    r"^(feat|bugfix|fix|chore|docs|refactor|test|perf)/[a-z0-9][a-z0-9.-]*$"
)


def trim(value: str) -> str:
    """Normalize free-form text before branch parsing.

    Args:
        value: Raw user or model text that may include leading/trailing whitespace.

    Returns:
        The same text without surrounding whitespace so downstream parsing is stable.
    """
    return value.strip()


def sanitize_branch(raw: str) -> str:
    """Convert loose branch-like text into a safe branch token.

    Args:
        raw: Branch candidate text from user input or model output.

    Returns:
        A normalized branch token that is safe to validate and use as a fallback seed.
    """
    value = raw.splitlines()[0] if raw else ""
    value = trim(value)

    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        value = value[1:-1]

    value = value.replace("```", "")
    value = trim(value)
    value = value.lower()
    value = value.replace(" ", "-").replace("_", "-")
    value = re.sub(r"[^a-z0-9/.-]", "", value)
    value = re.sub(r"/+", "/", value)
    value = re.sub(r"-+", "-", value)

    value = value.strip("/")
    value = value.strip("-")
    return value


def is_valid_prefixed_branch(value: str) -> bool:
    """Validate branch names against the accepted semantic prefix contract.

    Args:
        value: Branch name candidate to validate.

    Returns:
        ``True`` when the branch matches the enforced prefix and suffix format.
    """
    return bool(VALID_BRANCH_RE.match(value))


def fallback_branch(seed: str) -> str:
    """Guarantee a usable semantic branch name when generation fails.

    Args:
        seed: Human-readable fallback seed, usually intent or file-derived context.

    Returns:
        A ``feat/`` branch that preserves as much meaningful context as possible.
    """
    sanitized = sanitize_branch(seed).replace("/", "-")
    sanitized = sanitized.strip("-")
    if not sanitized:
        sanitized = "worktree"
    return f"feat/{sanitized}"
