import { ERROR_CODES, OcwtError } from "./errors.js"
import { canonicalizePath } from "./paths.js"

export interface SessionSummary {
  id: string
  directory: string
  title?: string
}

export interface SessionClient {
  listSessions(input: { directory: string }): Promise<SessionSummary[]>
  createSession(input: {
    directory: string
    title?: string
  }): Promise<SessionSummary>
  selectSession?(input: { sessionID: string }): Promise<void>
  promptSession?(input: {
    sessionID: string
    directory: string
    text: string
    agent?: string
  }): Promise<void>
}

export interface EnsureSessionOptions {
  interactive?: boolean
  title?: string
}

export interface EnsureSessionResult {
  sessionID: string
  created: boolean
  switchedSession: boolean
  headless: boolean
  directory: string
}

/**
 * Creates or reuses a session for a specific worktree directory and optionally switches the TUI to it.
 *
 * @param client - The session backend used to list, create, and optionally select sessions.
 * @param directory - The worktree directory the session should be bound to.
 * @param options - Controls whether TUI switching should be attempted and what title to use when creating.
 * @returns Metadata about the reused or created session.
 * @throws OcwtError When session creation or session switching fails.
 */
export async function ensureSessionForDirectory(
  client: SessionClient,
  directory: string,
  options: EnsureSessionOptions = {},
): Promise<EnsureSessionResult> {
  const canonicalDirectory = await canonicalizePath(directory)
  const existingSession = await findSessionByDirectory(
    client,
    canonicalDirectory,
  )

  const session =
    existingSession ??
    (await createSession(client, canonicalDirectory, options.title))
  const created = !existingSession
  const headless = !options.interactive

  if (options.interactive) {
    if (!client.selectSession) {
      throw new OcwtError(
        ERROR_CODES.sessionSwitchFailed,
        "Interactive session switching is not available for this session client",
      )
    }

    await switchSession(client, session.id)
  }

  return {
    sessionID: session.id,
    created,
    switchedSession: options.interactive === true,
    headless,
    directory: canonicalDirectory,
  }
}

/**
 * Finds the first session bound to the provided directory.
 *
 * @param client - The session backend used to query available sessions.
 * @param directory - The directory to match against session metadata.
 * @returns The first matching session, if one exists.
 */
export async function findSessionByDirectory(
  client: SessionClient,
  directory: string,
): Promise<SessionSummary | undefined> {
  const sessions = await listSessions(client, directory)
  return sessions[0]
}

/**
 * Lists sessions whose bound directory matches the target directory after canonical path comparison.
 *
 * @param client - The session backend used to query available sessions.
 * @param directory - The target worktree directory.
 * @returns The matching sessions for the directory.
 */
export async function listSessions(
  client: SessionClient,
  directory: string,
): Promise<SessionSummary[]> {
  const canonicalDirectory = await canonicalizePath(directory)
  const sessions = await client.listSessions({ directory: canonicalDirectory })
  const matches: SessionSummary[] = []

  for (const session of sessions) {
    if ((await canonicalizePath(session.directory)) === canonicalDirectory) {
      matches.push({
        ...session,
        directory: await canonicalizePath(session.directory),
      })
    }
  }

  return matches
}

async function createSession(
  client: SessionClient,
  directory: string,
  title?: string,
): Promise<SessionSummary> {
  try {
    const session = await client.createSession({
      directory,
      ...(title === undefined ? {} : { title }),
    })
    return {
      ...session,
      directory: await canonicalizePath(session.directory),
    }
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Failed to create worktree session"

    throw new OcwtError(ERROR_CODES.sessionCreateFailed, message)
  }
}

async function switchSession(
  client: SessionClient,
  sessionID: string,
): Promise<void> {
  try {
    await client.selectSession?.({ sessionID })
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Failed to switch to worktree session"

    throw new OcwtError(ERROR_CODES.sessionSwitchFailed, message)
  }
}
