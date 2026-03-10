import { stringifyEnvelope, ok } from "../lib/json.js"

export function ocwtOpenScaffold(): string {
  return stringifyEnvelope(
    ok("NOT_IMPLEMENTED", "ocwt_open scaffold created", {
      tool: "ocwt_open",
    }),
  )
}
