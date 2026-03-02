# Branch naming

`ocwt` enforces semantic branch prefixes and stable fallback behavior.

## Prefixes

- `feat/`
- `bugfix/`
- `fix/`
- `chore/`
- `docs/`
- `refactor/`
- `test/`
- `perf/`

## File-driven context

When opening from a file, branch suffix includes file context.

Example:

```text
pm/epic_011/ticket_003_delivery_status.md
=> feat/...-epic-011-ticket-003-delivery-status
```

Numeric identifiers are preserved.

## Fallback behavior

If model-based branch generation fails, `ocwt` falls back to a deterministic semantic branch from intent/file context.
