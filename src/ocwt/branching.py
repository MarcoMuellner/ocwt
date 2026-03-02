from __future__ import annotations

import re

VALID_PREFIXES = ("feat", "bugfix", "fix", "chore", "docs", "refactor", "test", "perf")
VALID_BRANCH_RE = re.compile(
    r"^(feat|bugfix|fix|chore|docs|refactor|test|perf)/[a-z0-9][a-z0-9.-]*$"
)


def trim(value: str) -> str:
    return value.strip()


def sanitize_branch(raw: str) -> str:
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
    return bool(VALID_BRANCH_RE.match(value))


def fallback_branch(seed: str) -> str:
    sanitized = sanitize_branch(seed).replace("/", "-")
    sanitized = sanitized.strip("-")
    if not sanitized:
        sanitized = "worktree"
    return f"feat/{sanitized}"
