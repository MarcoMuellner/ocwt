# FAQ

## How do I disable planning for one run?

Use:

```bash
ocwt open "..." --no-plan
```

## Does file input affect branch naming?

Yes. Opening from a file adds file context (including numeric IDs) to branch suffix.

## How do I upgrade?

```bash
uv tool upgrade ocwt
```

## Can I use `uvx` without install?

Yes:

```bash
uvx ocwt --help
```

## How do I set completion?

```bash
ocwt completion bash
ocwt completion zsh
```
