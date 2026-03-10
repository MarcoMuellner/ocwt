import path from "node:path"
import os from "node:os"
import { promises as fs } from "node:fs"

import { afterEach, describe, expect, it } from "vitest"

import { runGit } from "../src/lib/git.js"
import type { SessionClient } from "../src/lib/session.js"
import { ocwtList } from "../src/tools/ocwt-list.js"
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
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-list-"))
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

describe("ocwtList", () => {
  it("lists the primary worktree and managed feature worktrees", async () => {
    const repo = await createRepo()
    const worktreeParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    tempDirectories.push(worktreeParent)

    await ocwtOpen(
      { intentOrBranch: "feat/list-one" },
      { cwd: repo, worktreeParent },
    )
    await ocwtOpen(
      { intentOrBranch: "feat/list-two" },
      { cwd: repo, worktreeParent },
    )

    const result = parseEnvelope(
      await ocwtList({}, { cwd: repo, worktreeParent }),
    )

    expect(result.ok).toBe(true)
    expect(result.data).toMatchObject({
      repoRoot: expect.any(String),
      baseBranch: "main",
    })
    expect(result.data?.entries).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ branch: "main", protected: true }),
        expect.objectContaining({ branch: "feat/list-one", protected: false }),
        expect.objectContaining({ branch: "feat/list-two", protected: false }),
      ]),
    )
  })

  it("filters non-primary worktrees outside the configured parent", async () => {
    const repo = await createRepo()
    const allowedParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    const otherParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-other-parent-"),
    )
    tempDirectories.push(allowedParent, otherParent)

    await ocwtOpen(
      { intentOrBranch: "feat/included" },
      { cwd: repo, worktreeParent: allowedParent },
    )
    await ocwtOpen(
      { intentOrBranch: "feat/excluded" },
      { cwd: repo, worktreeParent: otherParent },
    )

    const result = parseEnvelope(
      await ocwtList({}, { cwd: repo, worktreeParent: allowedParent }),
    )

    const entries = result.data?.entries as
      | Array<{ branch: string }>
      | undefined
    expect(entries).toBeDefined()
    const branches = entries?.map((entry) => entry.branch) ?? []
    expect(branches).toContain("main")
    expect(branches).toContain("feat/included")
    expect(branches).not.toContain("feat/excluded")
  })

  it("adds session IDs when includeSessions is enabled", async () => {
    const repo = await createRepo()
    const worktreeParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    tempDirectories.push(worktreeParent)

    const opened = parseEnvelope(
      await ocwtOpen(
        { intentOrBranch: "feat/list-session" },
        { cwd: repo, worktreeParent },
      ),
    )

    const client: SessionClient = {
      async listSessions() {
        return [
          {
            id: "session-1",
            directory: String(opened.data?.worktreeDir),
          },
        ]
      },
      async createSession() {
        throw new Error("should not create")
      },
    }

    const result = parseEnvelope(
      await ocwtList(
        { includeSessions: true },
        { cwd: repo, worktreeParent, sessionClient: client },
      ),
    )

    expect(result.ok).toBe(true)
    expect(result.data?.entries).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          branch: "feat/list-session",
          sessionID: "session-1",
        }),
      ]),
    )
  })

  it("excludes unrelated manual worktrees when using the default managed parent", async () => {
    const repo = await createRepo()
    const manualParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-manual-parent-"),
    )
    const configDirectory = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-list-config-"),
    )
    tempDirectories.push(manualParent, configDirectory)
    const missingConfigPath = path.join(configDirectory, "missing-config.json")

    await ocwtOpen(
      { intentOrBranch: "feat/default-managed" },
      { cwd: repo, configPath: missingConfigPath },
    )
    await runGit(repo, [
      "worktree",
      "add",
      "-b",
      "feat/manual-outside",
      path.join(manualParent, "manual-outside"),
      "main",
    ])

    const result = parseEnvelope(
      await ocwtList({}, { cwd: repo, configPath: missingConfigPath }),
    )
    const entries = result.data?.entries as
      | Array<{ branch: string }>
      | undefined

    expect(result.ok).toBe(true)
    expect(entries).toBeDefined()
    const branches = entries?.map((entry) => entry.branch) ?? []
    expect(branches).toContain("main")
    expect(branches).toContain("feat/default-managed")
    expect(branches).not.toContain("feat/manual-outside")
  })
})
