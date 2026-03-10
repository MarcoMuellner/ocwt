import path from "node:path"
import os from "node:os"
import { promises as fs } from "node:fs"

import { afterEach, describe, expect, it } from "vitest"

import { runGit } from "../src/lib/git.js"
import { canonicalizePath } from "../src/lib/paths.js"
import {
  applySharedStateSymlinks,
  backupExistingPath,
  ensureEnvSymlinks,
  ensureSharedPathSymlink,
} from "../src/lib/symlink.js"
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
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-symlink-"))
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

describe("symlink helpers", () => {
  it("creates deterministic backup names", async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-symlink-"))
    tempDirectories.push(directory)
    const targetPath = path.join(directory, ".opencode")

    await fs.writeFile(`${targetPath}.backup-1`, "old\n", "utf8")

    await expect(backupExistingPath(targetPath)).resolves.toBe(
      `${targetPath}.backup-2`,
    )
  })

  it("backs up conflicting targets before linking shared paths", async () => {
    const repo = await createRepo()
    const worktree = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-worktree-"))
    tempDirectories.push(worktree)

    await fs.mkdir(path.join(repo, ".opencode"))
    await fs.writeFile(path.join(worktree, ".opencode"), "conflict\n", "utf8")

    const message = await ensureSharedPathSymlink(repo, worktree, ".opencode")
    const stats = await fs.lstat(path.join(worktree, ".opencode"))

    expect(message).toContain("backup")
    expect(stats.isSymbolicLink()).toBe(true)
    await expect(
      fs.access(path.join(worktree, ".opencode.backup-1")),
    ).resolves.toBeUndefined()
  })

  it("skips tracked env files and links untracked env files", async () => {
    const repo = await createRepo()
    const worktree = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-worktree-"))
    tempDirectories.push(worktree)

    await fs.writeFile(path.join(repo, ".env"), "TRACKED=1\n", "utf8")
    await runGit(repo, ["add", ".env"])
    await runGit(repo, ["commit", "-m", "track env"])
    await fs.writeFile(path.join(repo, ".env.local"), "LOCAL=1\n", "utf8")

    const messages = await ensureEnvSymlinks(repo, worktree)

    expect(messages).toContain("Skipped .env: tracked files are not symlinked")
    expect(
      messages.some((message) => message.startsWith("Linked .env.local")),
    ).toBe(true)
    await expect(
      fs.lstat(path.join(worktree, ".env.local")),
    ).resolves.toMatchObject({
      isSymbolicLink: expect.any(Function),
    })
  })

  it("applies the configured shared-state policy", async () => {
    const repo = await createRepo()
    const worktree = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-worktree-"))
    tempDirectories.push(worktree)

    await fs.mkdir(path.join(repo, ".opencode"))
    await fs.mkdir(path.join(repo, ".idea"))
    await fs.writeFile(path.join(repo, ".env.local"), "LOCAL=1\n", "utf8")

    const messages = await applySharedStateSymlinks(repo, worktree, {
      symlinkOpencode: true,
      symlinkIdea: true,
      symlinkEnv: true,
    })

    expect(
      messages.some((message) => message.startsWith("Linked .opencode")),
    ).toBe(true)
    expect(messages.some((message) => message.startsWith("Linked .idea"))).toBe(
      true,
    )
    expect(
      messages.some((message) => message.startsWith("Linked .env.local")),
    ).toBe(true)
  })

  it("does nothing when the worktree is the primary repo root", async () => {
    const repo = await createRepo()

    await fs.mkdir(path.join(repo, ".opencode"))
    await fs.writeFile(path.join(repo, ".env.local"), "LOCAL=1\n", "utf8")

    await expect(
      applySharedStateSymlinks(repo, repo, {
        symlinkOpencode: true,
        symlinkIdea: true,
        symlinkEnv: true,
      }),
    ).resolves.toEqual([])

    await expect(fs.lstat(path.join(repo, ".opencode"))).resolves.toMatchObject(
      {
        isDirectory: expect.any(Function),
      },
    )
    await expect(
      fs.lstat(path.join(repo, ".env.local")),
    ).resolves.toMatchObject({
      isFile: expect.any(Function),
    })
  })
})

describe("open integration", () => {
  it("applies symlink config during worktree open", async () => {
    const repo = await createRepo()
    const configDirectory = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-symlink-config-"),
    )
    tempDirectories.push(configDirectory)
    const configPath = path.join(configDirectory, "config.json")

    await fs.mkdir(path.join(repo, ".opencode"))
    await fs.writeFile(path.join(repo, ".env.local"), "LOCAL=1\n", "utf8")
    await fs.writeFile(
      configPath,
      JSON.stringify({ symlink_opencode: true, symlink_env: true }),
      "utf8",
    )

    const result = parseEnvelope(
      await ocwtOpen(
        { intentOrBranch: "feat/symlink-open" },
        { cwd: repo, configPath },
      ),
    )

    expect(result.ok).toBe(true)
    expect(result.data?.symlinkMessages).toEqual(
      expect.arrayContaining([
        expect.stringMatching(/^Linked \.opencode/),
        expect.stringMatching(/^Linked \.env\.local/),
      ]),
    )

    const worktreeDir = String(result.data?.worktreeDir)
    const opencodeStats = await fs.lstat(path.join(worktreeDir, ".opencode"))
    const envStats = await fs.lstat(path.join(worktreeDir, ".env.local"))

    expect(opencodeStats.isSymbolicLink()).toBe(true)
    expect(envStats.isSymbolicLink()).toBe(true)
  })

  it("does not mutate shared paths when reusing the primary branch worktree", async () => {
    const repo = await createRepo()
    const configDirectory = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-symlink-config-"),
    )
    tempDirectories.push(configDirectory)
    const configPath = path.join(configDirectory, "config.json")

    await fs.mkdir(path.join(repo, ".opencode"))
    await fs.writeFile(path.join(repo, ".env.local"), "LOCAL=1\n", "utf8")
    await fs.writeFile(
      configPath,
      JSON.stringify({ symlink_opencode: true, symlink_env: true }),
      "utf8",
    )

    const result = parseEnvelope(
      await ocwtOpen({ intentOrBranch: "main" }, { cwd: repo, configPath }),
    )

    expect(result.ok).toBe(true)
    expect(result.data).toMatchObject({
      branch: "main",
      reused: true,
      worktreeDir: await canonicalizePath(repo),
      symlinkMessages: [],
    })

    const opencodeStats = await fs.lstat(path.join(repo, ".opencode"))
    const envStats = await fs.lstat(path.join(repo, ".env.local"))

    expect(opencodeStats.isDirectory()).toBe(true)
    expect(envStats.isFile()).toBe(true)
  })
})
