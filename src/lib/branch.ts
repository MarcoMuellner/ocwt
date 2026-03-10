import { BRANCH_PREFIXES, type BranchPrefix } from "./types.js"

/**
 * Returns true when a branch name already uses one of the supported semantic prefixes.
 *
 * @param value - The branch name to inspect.
 * @returns True when the branch starts with an allowed `prefix/` segment.
 */
export function hasAllowedPrefix(
  value: string,
): value is `${BranchPrefix}/${string}` {
  return BRANCH_PREFIXES.some((prefix) => value.startsWith(`${prefix}/`))
}

/**
 * Rewrites free-form branch text into a normalized git-safe segment.
 *
 * @param value - The raw user or model supplied branch text.
 * @returns A lowercase, separator-normalized branch segment.
 */
export function sanitizeBranchSegment(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9/._-]+/g, "-")
    .replace(/\/+/g, "/")
    .replace(/\/\/+/, "/")
    .replace(/-{2,}/g, "-")
    .replace(/^[-./]+|[-./]+$/g, "")
}

/**
 * Normalizes a branch name while preserving any semantic prefix already present.
 *
 * @param value - The raw branch input to normalize.
 * @returns A normalized branch string with repeated separators collapsed.
 */
export function normalizeBranchName(value: string): string {
  const sanitized = sanitizeBranchSegment(value)
  return sanitized.replace(/\/{2,}/g, "/")
}

/**
 * Builds a deterministic fallback branch name when direct input cannot be trusted as-is.
 *
 * @param seed - The user input used to derive a stable fallback.
 * @returns A `chore/` branch with a deterministic normalized suffix.
 */
export function toDeterministicFallback(seed: string): string {
  const normalized = normalizeBranchName(seed)
  const compact = normalized.replace(/[^a-z0-9]+/g, "-").slice(0, 32)
  return `chore/${compact || "worktree"}`
}
