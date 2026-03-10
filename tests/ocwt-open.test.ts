import path from "node:path"
import os from "node:os"
import { promises as fs } from "node:fs"

import { afterEach, describe, expect, it } from "vitest"

import { runGit } from "../src/lib/git.js"
import { canonicalizePath } from "../src/lib/paths.js"
import type { SessionClient } from "../src/lib/session.js"
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
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-open-"))
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

describe("ocwtOpen", () => {
  it("creates a new worktree from a valid direct branch", async () => {
    const repo = await createRepo()
    const worktreeParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    tempDirectories.push(worktreeParent)

    const result = parseEnvelope(
      await ocwtOpen(
        { intentOrBranch: "feat/native-open" },
        { cwd: repo, worktreeParent },
      ),
    )

    expect(result.ok).toBe(true)
    expect(result.data).toMatchObject({
      branch: "feat/native-open",
      created: true,
      reused: false,
      baseBranch: "main",
      repoRoot: await canonicalizePath(repo),
    })
    expect(result.data?.worktreeDir).toBe(
      path.join(worktreeParent, "feat__native-open"),
    )
  })

  it("reuses an existing branch worktree instead of creating a duplicate", async () => {
    const repo = await createRepo()
    const worktreeParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    tempDirectories.push(worktreeParent)

    await ocwtOpen(
      { intentOrBranch: "feat/native-open" },
      { cwd: repo, worktreeParent },
    )
    const second = parseEnvelope(
      await ocwtOpen(
        { intentOrBranch: "feat/native-open" },
        { cwd: repo, worktreeParent },
      ),
    )

    expect(second.ok).toBe(true)
    expect(second.data).toMatchObject({
      branch: "feat/native-open",
      created: false,
      reused: true,
    })
  })

  it("generates a prefixed branch from free-form intent", async () => {
    const repo = await createRepo()
    const worktreeParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    tempDirectories.push(worktreeParent)

    const result = parseEnvelope(
      await ocwtOpen(
        { intentOrBranch: "Add native open flow" },
        { cwd: repo, worktreeParent },
      ),
    )

    expect(result.ok).toBe(true)
    expect(result.data?.branch).toBe("feat/add-native-open-flow")
  })

  it("fails when reuseOnly is set and no worktree exists", async () => {
    const repo = await createRepo()

    const result = parseEnvelope(
      await ocwtOpen(
        { intentOrBranch: "feat/native-open", reuseOnly: true },
        { cwd: repo },
      ),
    )

    expect(result.ok).toBe(false)
    expect(result.code).toBe("INVALID_INPUT")
  })

  it("fails when an attached file does not exist", async () => {
    const repo = await createRepo()

    const result = parseEnvelope(
      await ocwtOpen({ files: ["missing-file.ts"] }, { cwd: repo }),
    )

    expect(result.ok).toBe(false)
    expect(result.code).toBe("FILE_NOT_FOUND")
  })

  it("fails when no branch seed or files are provided", async () => {
    const repo = await createRepo()

    const result = parseEnvelope(await ocwtOpen({}, { cwd: repo }))

    expect(result.ok).toBe(false)
    expect(result.code).toBe("INVALID_INPUT")
  })

  it("creates and returns a worktree-bound session when a session client is provided", async () => {
    const repo = await createRepo()
    const worktreeParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    tempDirectories.push(worktreeParent)

    const selected: string[] = []
    const client: SessionClient = {
      async listSessions() {
        return []
      },
      async createSession(input) {
        return {
          id: "session-1",
          directory: input.directory,
          ...(input.title === undefined ? {} : { title: input.title }),
        }
      },
      async selectSession(input) {
        selected.push(input.sessionID)
      },
    }

    const result = parseEnvelope(
      await ocwtOpen(
        { intentOrBranch: "feat/native-open" },
        {
          cwd: repo,
          worktreeParent,
          sessionClient: client,
          interactive: true,
        },
      ),
    )

    expect(result.ok).toBe(true)
    expect(result.data).toMatchObject({
      sessionID: "session-1",
      switchedSession: true,
    })
    expect(selected).toEqual(["session-1"])
  })

  it("returns failure metadata when session creation fails after the worktree is created", async () => {
    const repo = await createRepo()
    const worktreeParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    tempDirectories.push(worktreeParent)

    const client: SessionClient = {
      async listSessions() {
        return []
      },
      async createSession() {
        throw new Error("session backend unavailable")
      },
    }

    const result = parseEnvelope(
      await ocwtOpen(
        { intentOrBranch: "feat/native-open" },
        { cwd: repo, worktreeParent, sessionClient: client },
      ),
    )

    expect(result.ok).toBe(false)
    expect(result.code).toBe("SESSION_CREATE_FAILED")
    expect(result.data).toMatchObject({
      branch: "feat/native-open",
      created: true,
      reused: false,
      worktreeDir: path.join(worktreeParent, "feat__native-open"),
    })
  })

  it("returns failure metadata when session switching fails after worktree reuse", async () => {
    const repo = await createRepo()
    const worktreeParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    tempDirectories.push(worktreeParent)

    await ocwtOpen(
      { intentOrBranch: "feat/native-open" },
      { cwd: repo, worktreeParent },
    )

    const client: SessionClient = {
      async listSessions() {
        return [
          {
            id: "session-1",
            directory: path.join(worktreeParent, "feat__native-open"),
          },
        ]
      },
      async createSession() {
        throw new Error("should not create")
      },
      async selectSession() {
        throw new Error("switch failed")
      },
    }

    const result = parseEnvelope(
      await ocwtOpen(
        { intentOrBranch: "feat/native-open" },
        {
          cwd: repo,
          worktreeParent,
          sessionClient: client,
          interactive: true,
        },
      ),
    )

    expect(result.ok).toBe(false)
    expect(result.code).toBe("SESSION_SWITCH_FAILED")
    expect(result.data).toMatchObject({
      branch: "feat/native-open",
      created: false,
      reused: true,
      worktreeDir: await canonicalizePath(
        path.join(worktreeParent, "feat__native-open"),
      ),
    })
  })
})
