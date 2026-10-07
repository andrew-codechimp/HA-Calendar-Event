# Calendar Event tests

The suite uses `pytest-homeassistant-custom-component`, following the shared
fixtures, parameterized tests, and Syrupy snapshots pattern.

Run commands from the repository root:

```bash
./scripts/setup
uv run --no-sync pytest
uv run --no-sync pytest --cov=custom_components.calendar_event --cov-report=term-missing
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync mypy
```

VS Code provides `Tests: All with Coverage` (the default test task), `Tests: All`,
and `Tests: Current File`. The coverage task also writes an HTML report to
`htmlcov/index.html`.

The GitHub `Tests` workflow runs on relevant pushes and pull requests to `main`,
and can be started manually. It installs dependencies from `uv.lock` and runs
the full suite.

The tests cover:

- Matching methods, matching fields, active event times, and event attributes.
- Empty, malformed, and failing calendar responses and recovery.
- Minute polling, disabled entities, task cancellation, migrations, and source changes.

`mock_config_entry` accepts option overrides with indirect parametrization.
`setup_integration` loads the helper. Timer tests advance a frozen clock and run
scheduled callbacks without waiting in real time.

Entity metadata is captured in `snapshots/*.ambr`. After intentional output
changes, regenerate and review the snapshots:

```bash
uv run --no-sync pytest tests --snapshot-update
```
