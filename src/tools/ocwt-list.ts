import { stringifyEnvelope, ok } from "../lib/json.js"

export function ocwtListScaffold(): string {
  return stringifyEnvelope(
    ok("NOT_IMPLEMENTED", "ocwt_list scaffold created", {
      tool: "ocwt_list",
    }),
  )
}
