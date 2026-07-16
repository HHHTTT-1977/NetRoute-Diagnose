# Contributing

Thank you for improving NetRoute-Diagnose.

1. Open an issue for substantial behavior changes.
2. Keep all diagnostics read-only by default.
3. Preserve the distinction between static rule inference and runtime evidence.
4. Add tests for every new rule type or report behavior.
5. Run `python -m unittest discover -s tests -v` before opening a pull request.

Do not include real subscription URLs, proxy credentials, controller secrets,
or private network data in issues, fixtures, or commits.
