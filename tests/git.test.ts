import path from "node:path"
import os from "node:os"
import { promises as fs } from "node:fs"

import { afterEach, describe, expect, it } from "vitest"

import {
  createWorktree,
  deleteLocalBranch,
  findRepoRoot,
  findWorktreeByBranch,
  findWorktreeContainingPath,
  findWorktreeByPath,
  getBaseBranch,
  getCurrentBranch,
  isProtectedBranch,
  isTrackedPath,
  listWorktrees,
  removeWorktree,
  runGit,
} from "../src/lib/git.js"
import { ERROR_CODES, OcwtError } from "../src/lib/errors.js"
import { canonicalizePath } from "../src/lib/paths.js"

const tempDirectories: string[] = []

afterEach(async () => {
  await Promise.all(
    tempDirectories
      .splice(0)
      .map((directory) => fs.rm(directory, { recursive: true, force: true })),
  )
})

async function createRepo(): Promise<string> {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-git-"))
  tempDirectories.push(directory)

  await expect(
    runGit(directory, ["init", "-b", "main"]),
  ).resolves.toMatchObject({
    exitCode: 0,
  })
  await expect(
    runGit(directory, ["config", "user.name", "ocwt test"]),
  ).resolves.toMatchObject({ exitCode: 0 })
  await expect(
    runGit(directory, ["config", "user.email", "ocwt@example.com"]),
  ).resolves.toMatchObject({ exitCode: 0 })

  await fs.writeFile(path.join(directory, "README.md"), "seed\n", "utf8")
  await expect(runGit(directory, ["add", "README.md"])).resolves.toMatchObject({
    exitCode: 0,
  })
  await expect(
    runGit(directory, ["commit", "-m", "init"]),
  ).resolves.toMatchObject({ exitCode: 0 })

  return directory
}

async function createMasterRepo(): Promise<string> {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-git-master-"))
  tempDirectories.push(directory)

  await expect(
    runGit(directory, ["init", "-b", "master"]),
  ).resolves.toMatchObject({
    exitCode: 0,
  })
  await expect(
    runGit(directory, ["config", "user.name", "ocwt test"]),
  ).resolves.toMatchObject({ exitCode: 0 })
  await expect(
    runGit(directory, ["config", "user.email", "ocwt@example.com"]),
  ).resolves.toMatchObject({ exitCode: 0 })

  await fs.writeFile(path.join(directory, "README.md"), "seed\n", "utf8")
  await expect(runGit(directory, ["add", "README.md"])).resolves.toMatchObject({
    exitCode: 0,
  })
  await expect(
    runGit(directory, ["commit", "-m", "init"]),
  ).resolves.toMatchObject({ exitCode: 0 })

  return directory
}

describe("git helpers", () => {
  it("finds the repository root and current branch", async () => {
    const repo = await createRepo()

    await expect(findRepoRoot(repo)).resolves.toBe(await canonicalizePath(repo))
    await expect(getCurrentBranch(repo)).resolves.toBe("main")
  })

  it("detects the base branch from local defaults", async () => {
    const repo = await createRepo()

    await expect(getBaseBranch(repo)).resolves.toBe("main")
  })

  it("falls back to master when main does not exist", async () => {
    const repo = await createMasterRepo()

    await expect(getBaseBranch(repo)).resolves.toBe("master")
  })

  it("returns undefined for the current branch when HEAD is detached", async () => {
    const repo = await createRepo()

    await expect(runGit(repo, ["checkout", "HEAD~0"])).resolves.toMatchObject({
      exitCode: 0,
    })
    await expect(getCurrentBranch(repo)).resolves.toBeUndefined()
  })

  it("creates, lists, finds, removes, and deletes worktree branches", async () => {
    const repo = await createRepo()
    const worktreeParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-worktree-"),
    )
    tempDirectories.push(worktreeParent)
    const worktreeDirectory = path.join(worktreeParent, "feat-native-open")

    await expect(
      createWorktree(repo, {
        branch: "feat/native-open",
        directory: worktreeDirectory,
        startPoint: "main",
      }),
    ).resolves.toBeUndefined()

    await expect(
      findWorktreeByBranch(repo, "feat/native-open"),
    ).resolves.toMatchObject({
      branch: "feat/native-open",
    })
    await expect(
      findWorktreeByPath(repo, worktreeDirectory),
    ).resolves.toMatchObject({
      directory: await canonicalizePath(worktreeDirectory),
    })

    const worktrees = await listWorktrees(repo)
    expect(worktrees.some((entry) => entry.branch === "feat/native-open")).toBe(
      true,
    )

    await expect(
      removeWorktree(repo, worktreeDirectory, true),
    ).resolves.toBeUndefined()
    await expect(
      deleteLocalBranch(repo, "feat/native-open"),
    ).resolves.toBeUndefined()
    await expect(
      findWorktreeByBranch(repo, "feat/native-open"),
    ).resolves.toBeUndefined()
  })

  it("returns undefined when a worktree path is not registered", async () => {
    const repo = await createRepo()
    const missingWorktree = path.join(repo, "..", "missing-worktree")

    await expect(
      findWorktreeByPath(repo, missingWorktree),
    ).resolves.toBeUndefined()
  })

  it("finds a containing worktree from a nested path", async () => {
    const repo = await createRepo()
    const worktreeParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-worktree-"),
    )
    tempDirectories.push(worktreeParent)
    const worktreeDirectory = path.join(worktreeParent, "feat-native-open")

    await expect(
      createWorktree(repo, {
        branch: "feat/native-open",
        directory: worktreeDirectory,
        startPoint: "main",
      }),
    ).resolves.toBeUndefined()

    const nestedDirectory = path.join(worktreeDirectory, "src", "nested")
    await fs.mkdir(nestedDirectory, { recursive: true })

    await expect(
      findWorktreeContainingPath(repo, nestedDirectory),
    ).resolves.toMatchObject({
      branch: "feat/native-open",
    })
  })

  it("detects tracked paths", async () => {
    const repo = await createRepo()
    const trackedPath = path.join(repo, "README.md")
    const untrackedPath = path.join(repo, ".env")

    await fs.writeFile(untrackedPath, "TOKEN=secret\n", "utf8")

    await expect(isTrackedPath(repo, trackedPath)).resolves.toBe(true)
    await expect(isTrackedPath(repo, untrackedPath)).resolves.toBe(false)
  })

  it("classifies protected branches", () => {
    expect(isProtectedBranch("main", "main")).toBe(true)
    expect(isProtectedBranch("master", "main")).toBe(true)
    expect(isProtectedBranch("develop", "develop")).toBe(true)
    expect(isProtectedBranch("feat/native-open", "main")).toBe(false)
  })

  it("fails closed when asked to inspect a non-git directory", async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-not-git-"))
    tempDirectories.push(directory)

    await expect(findRepoRoot(directory)).rejects.toMatchObject({
      code: ERROR_CODES.notGitRepo,
    } satisfies Partial<OcwtError>)
  })

  it("fails closed when deleting a branch that does not exist", async () => {
    const repo = await createRepo()

    await expect(
      deleteLocalBranch(repo, "feat/missing-branch"),
    ).rejects.toMatchObject({
      code: ERROR_CODES.deleteBranchFailed,
    } satisfies Partial<OcwtError>)
  })
})
