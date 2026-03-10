import { describe, expect, it } from "vitest"

import {
  hasAllowedPrefix,
  normalizeBranchName,
  toDeterministicFallback,
} from "../src/lib/branch.js"

describe("branch helpers", () => {
  it("accepts supported semantic prefixes", () => {
    expect(hasAllowedPrefix("feat/native-open")).toBe(true)
    expect(hasAllowedPrefix("docs/plan")).toBe(true)
    expect(hasAllowedPrefix("unknown/plan")).toBe(false)
  })

  it("normalizes branch text into safe lowercase output", () => {
    expect(normalizeBranchName("  Feat/My Cool Thing  ")).toBe(
      "feat/my-cool-thing",
    )
  })

  it("creates deterministic fallback branches", () => {
    expect(toDeterministicFallback("@@@ broken input ###")).toBe(
      "chore/broken-input",
    )
    expect(toDeterministicFallback("@@@ broken input ###")).toBe(
      "chore/broken-input",
    )
  })
})
