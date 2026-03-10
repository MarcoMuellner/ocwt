import { stringifyEnvelope, ok } from "../lib/json.js"

export function ocwtCloseScaffold(): string {
  return stringifyEnvelope(
    ok("NOT_IMPLEMENTED", "ocwt_close scaffold created", {
      tool: "ocwt_close",
    }),
  )
}
