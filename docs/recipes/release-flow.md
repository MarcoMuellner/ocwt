# Recipe: release flow

`ocwt` uses semantic GitHub releases (`vX.Y.Z`) to trigger publish.

## Release steps

1. create GitHub release tag like `v0.1.8`
2. release workflow runs checks and builds
3. artifacts upload to GitHub release
4. package publishes to PyPI via trusted publishing

## Tag format

Use semantic tags only:

```text
v0.1.8
v1.0.0
```

Non-semantic tags are rejected by workflow.
