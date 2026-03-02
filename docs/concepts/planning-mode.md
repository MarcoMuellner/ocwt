# Planning mode

Planning mode runs a one-shot planning pass, then continues in an interactive OpenCode session.

## Enable

```bash
# per command
ocwt open "improve retry policy" --plan

# default for all opens
ocwt config auto-plan true
```

## Disable for one run

```bash
ocwt open "small fix" --no-plan
```

## Agent behavior

- Default planning agent: `plan`
- `--agent <name>` overrides it for that invocation

## Output behavior

- shows a clean live status line (latest step only)
- avoids raw JSON event spam
