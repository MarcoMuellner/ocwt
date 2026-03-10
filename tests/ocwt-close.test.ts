import path from "node:path"
import os from "node:os"
import { promises as fs } from "node:fs"

import { afterEach, describe, expect, it } from "vitest"

import { findWorktreeByBranch, runGit } from "../src/lib/git.js"
import { canonicalizePath } from "../src/lib/paths.js"
import { ocwtClose } from "../src/tools/ocwt-close.js"
import { ocwtOpen } from "../src/tools/ocwt-open.js"
import type { ResultEnvelope } from "../src/lib/types.js"

const tempDirectories: string[] = []

afterEach(async () => {
  await Promise.all(
    tempDirectories
      .splice(0)
      .map((directory) => fs.rm(directory, { recursive: true, force: true })),
  )
})

async function createRepo(): Promise<string> {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-close-"))
  tempDirectories.push(directory)

  await runGit(directory, ["init", "-b", "main"])
  await runGit(directory, ["config", "user.name", "ocwt test"])
  await runGit(directory, ["config", "user.email", "ocwt@example.com"])
  await fs.writeFile(path.join(directory, "README.md"), "seed\n", "utf8")
  await runGit(directory, ["add", "README.md"])
  await runGit(directory, ["commit", "-m", "init"])

  return directory
}

function parseEnvelope(input: string): ResultEnvelope<Record<string, unknown>> {
  return JSON.parse(input) as ResultEnvelope<Record<string, unknown>>
}

describe("ocwtClose", () => {
  it("closes a worktree by branch name", async () => {
    const repo = await createRepo()
    const worktreeParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    tempDirectories.push(worktreeParent)

    const opened = parseEnvelope(
      await ocwtOpen(
        { intentOrBranch: "feat/native-close" },
        { cwd: repo, worktreeParent },
      ),
    )

    expect(opened.ok).toBe(true)
    const expectedWorktreeDir = await canonicalizePath(
      String(opened.data?.worktreeDir),
    )

    const result = parseEnvelope(
      await ocwtClose(
        { branchOrPath: "feat/native-close" },
        { cwd: repo, worktreeParent },
      ),
    )

    expect(result.ok).toBe(true)
    expect(result.data).toMatchObject({
      branch: "feat/native-close",
      removedWorktree: true,
      deletedBranch: true,
      worktreeDir: expectedWorktreeDir,
    })
    await expect(
      findWorktreeByBranch(repo, "feat/native-close"),
    ).resolves.toBeUndefined()
  })

  it("closes a worktree by path", async () => {
    const repo = await createRepo()
    const worktreeParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    tempDirectories.push(worktreeParent)

    const opened = parseEnvelope(
      await ocwtOpen(
        { intentOrBranch: "feat/native-close-path" },
        { cwd: repo, worktreeParent },
      ),
    )

    const result = parseEnvelope(
      await ocwtClose(
        { branchOrPath: String(opened.data?.worktreeDir) },
        { cwd: repo, worktreeParent },
      ),
    )

    expect(result.ok).toBe(true)
    expect(result.data).toMatchObject({
      branch: "feat/native-close-path",
      removedWorktree: true,
      deletedBranch: true,
    })
  })

  it("refuses to close a protected primary worktree", async () => {
    const repo = await createRepo()

    const result = parseEnvelope(await ocwtClose({}, { cwd: repo }))

    expect(result.ok).toBe(false)
    expect(result.code).toBe("PROTECTED_BRANCH")
    expect(result.data).toMatchObject({
      branch: "main",
      removedWorktree: false,
      deletedBranch: false,
    })
  })

  it("refuses to close a path outside the configured worktree parent", async () => {
    const repo = await createRepo()
    const allowedParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    const otherParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-other-parent-"),
    )
    tempDirectories.push(allowedParent, otherParent)

    const opened = parseEnvelope(
      await ocwtOpen(
        { intentOrBranch: "feat/outside-parent" },
        { cwd: repo, worktreeParent: otherParent },
      ),
    )

    const result = parseEnvelope(
      await ocwtClose(
        { branchOrPath: String(opened.data?.worktreeDir) },
        { cwd: repo, worktreeParent: allowedParent },
      ),
    )

    expect(result.ok).toBe(false)
    expect(result.code).toBe("TARGET_NOT_FOUND")
  })

  it("returns target not found for an unknown branch", async () => {
    const repo = await createRepo()

    const result = parseEnvelope(
      await ocwtClose({ branchOrPath: "feat/missing" }, { cwd: repo }),
    )

    expect(result.ok).toBe(false)
    expect(result.code).toBe("TARGET_NOT_FOUND")
  })

  it("closes the current worktree when run from a nested subdirectory", async () => {
    const repo = await createRepo()
    const worktreeParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    tempDirectories.push(worktreeParent)

    const opened = parseEnvelope(
      await ocwtOpen(
        { intentOrBranch: "feat/from-subdir" },
        { cwd: repo, worktreeParent },
      ),
    )
    const worktreeDir = String(opened.data?.worktreeDir)
    const nestedDirectory = path.join(worktreeDir, "src", "nested")
    await fs.mkdir(nestedDirectory, { recursive: true })

    const result = parseEnvelope(
      await ocwtClose({}, { cwd: nestedDirectory, worktreeParent }),
    )

    expect(result.ok).toBe(true)
    expect(result.data).toMatchObject({
      branch: "feat/from-subdir",
      removedWorktree: true,
      deletedBranch: true,
    })
  })

  it("refuses branch-based close when the resolved worktree is outside the managed parent", async () => {
    const repo = await createRepo()
    const allowedParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    const otherParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-other-parent-"),
    )
    tempDirectories.push(allowedParent, otherParent)

    await ocwtOpen(
      { intentOrBranch: "feat/outside-parent-branch" },
      { cwd: repo, worktreeParent: otherParent },
    )

    const result = parseEnvelope(
      await ocwtClose(
        { branchOrPath: "feat/outside-parent-branch" },
        { cwd: repo, worktreeParent: allowedParent },
      ),
    )

    expect(result.ok).toBe(false)
    expect(result.code).toBe("TARGET_NOT_FOUND")
  })
})
