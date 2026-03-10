import type { ResultEnvelope } from "./types.js"

export function ok<TData>(
  code: string,
  message: string,
  data?: TData,
): ResultEnvelope<TData> {
  return {
    ok: true,
    code,
    message,
    ...(data === undefined ? {} : { data }),
  }
}

export function fail<TData>(
  code: string,
  message: string,
  options?: {
    data?: TData
    nextAction?: string
  },
): ResultEnvelope<TData> {
  return {
    ok: false,
    code,
    message,
    ...(options?.data === undefined ? {} : { data: options.data }),
    ...(options?.nextAction === undefined
      ? {}
      : { next_action: options.nextAction }),
  }
}

export function stringifyEnvelope<TData>(
  envelope: ResultEnvelope<TData>,
): string {
  return JSON.stringify(envelope, null, 2)
}
