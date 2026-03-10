import { BRANCH_PREFIXES, type BranchPrefix } from "./types.js"

export function hasAllowedPrefix(
  value: string,
): value is `${BranchPrefix}/${string}` {
  return BRANCH_PREFIXES.some((prefix) => value.startsWith(`${prefix}/`))
}

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

export function normalizeBranchName(value: string): string {
  const sanitized = sanitizeBranchSegment(value)
  return sanitized.replace(/\/{2,}/g, "/")
}

export function toDeterministicFallback(seed: string): string {
  const normalized = normalizeBranchName(seed)
  const compact = normalized.replace(/[^a-z0-9]+/g, "-").slice(0, 32)
  return `chore/${compact || "worktree"}`
}
