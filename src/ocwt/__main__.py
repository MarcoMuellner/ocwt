from ocwt.cli import run


def main() -> int:
    """Expose a stable console entrypoint for package execution.

    Args:
        None.

    Returns:
        Process-style exit code from the CLI dispatcher.
    """
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
