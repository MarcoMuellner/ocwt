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

          captureOpenToolMetadata(result, context)
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
    "tool.execute.after": async (event, output) => {
      if (event.tool !== "ocwt_open") return

      const sessionID = readTargetSessionID(output.metadata)
      if (!sessionID) return

      await selectPluginSession(input, sessionID)
    },
  }
}

export default plugin

function captureOpenToolMetadata(result: string, context: ToolContext) {
  const targetSessionID = extractTargetSessionID(result)
  if (!targetSessionID) return

  context.metadata({
    metadata: {
      ocwt: {
        targetSessionID,
      },
    },
  })
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

function readTargetSessionID(metadata: unknown): string | undefined {
  if (typeof metadata !== "object" || metadata === null) return undefined
  const ocwt = Reflect.get(metadata, "ocwt")
  if (typeof ocwt !== "object" || ocwt === null) return undefined

  const targetSessionID = Reflect.get(ocwt, "targetSessionID")
  return typeof targetSessionID === "string" ? targetSessionID : undefined
}
