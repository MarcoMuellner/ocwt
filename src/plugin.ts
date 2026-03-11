import type { Plugin, PluginInput } from "@opencode-ai/plugin"
import { tool, type ToolContext } from "@opencode-ai/plugin/tool"

import { INJECTED_COMMANDS } from "./plugin-commands.js"
import {
  createPluginSessionClient,
  selectPluginSession,
} from "./plugin-runtime.js"
import { ocwtClose } from "./tools/ocwt-close.js"
import { ocwtList } from "./tools/ocwt-list.js"
import { ocwtOpen } from "./tools/ocwt-open.js"

export const plugin: Plugin = async (input: PluginInput) => {
  const sessionClient = createPluginSessionClient(input)
  const pendingSessionSwitches = new Map<string, string>()

  return {
    config: async (input) => {
      input.command ??= {}

      for (const [name, command] of Object.entries(INJECTED_COMMANDS)) {
        input.command[name] = {
          description: command.description,
          template: command.template,
          agent: command.agent,
        }
      }
    },
    tool: {
      ocwt_open: tool({
        description: "Open or reuse an ocwt worktree",
        args: {
          intentOrBranch: tool.schema.string().optional(),
          files: tool.schema.array(tool.schema.string()).optional(),
          plan: tool.schema.boolean().optional(),
          agent: tool.schema.string().optional(),
          reuseOnly: tool.schema.boolean().optional(),
        },
        async execute(
          args: {
            intentOrBranch?: string
            files?: string[]
            plan?: boolean
            agent?: string
            reuseOnly?: boolean
          },
          context: ToolContext,
        ) {
          const result = await ocwtOpen(args, {
            cwd: context.directory,
            sessionClient,
            interactive: false,
          })

          captureOpenToolMetadata(result, context, pendingSessionSwitches)
          return result
        },
      }),
      ocwt_close: tool({
        description: "Close an ocwt worktree safely",
        args: {
          branchOrPath: tool.schema.string().optional(),
          force: tool.schema.boolean().optional(),
        },
        async execute(
          args: {
            branchOrPath?: string
            force?: boolean
          },
          context: ToolContext,
        ) {
          return await ocwtClose(args, {
            cwd: context.directory,
          })
        },
      }),
      ocwt_list: tool({
        description: "List ocwt-managed worktrees",
        args: {
          includeSessions: tool.schema.boolean().optional(),
        },
        async execute(
          args: {
            includeSessions?: boolean
          },
          context: ToolContext,
        ) {
          return await ocwtList(args, {
            cwd: context.directory,
            sessionClient,
          })
        },
      }),
    },
    event: async ({ event }) => {
      if (event.type !== "command.executed") return

      const sessionID = pendingSessionSwitches.get(event.properties.sessionID)
      if (!sessionID) return

      pendingSessionSwitches.delete(event.properties.sessionID)
      await selectPluginSession(input, sessionID)
    },
  }
}

export default plugin

function captureOpenToolMetadata(
  result: string,
  context: ToolContext,
  pendingSessionSwitches: Map<string, string>,
) {
  const targetSessionID = extractTargetSessionID(result)
  if (!targetSessionID) return

  pendingSessionSwitches.set(context.sessionID, targetSessionID)
}

function extractTargetSessionID(result: string): string | undefined {
  try {
    const parsed = JSON.parse(result) as {
      ok?: boolean
      data?: {
        sessionID?: string
      }
    }

    if (parsed.ok !== true) return undefined
    return parsed.data?.sessionID
  } catch {
    return undefined
  }
}
