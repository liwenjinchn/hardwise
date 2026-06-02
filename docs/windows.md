# Windows Usage

Hardwise is expected to work on native Windows for the main CLI and local
workbench paths, but Windows support should be described as CI-verified only
after the `windows-latest` GitHub Actions job passes.

WSL remains a good fallback if a dependency wheel or local shell setup causes
friction on a specific Windows machine.

## Required Tools

- Git on `PATH`
- PowerShell 7 or Windows PowerShell
- `uv`, which manages the Python runtime and virtual environment

Install `uv` from PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart the terminal after installing `uv` if the command is not immediately on
`PATH`.

## Native PowerShell Setup

```powershell
git clone <repo> hardwise
Set-Location hardwise
uv sync --extra dev
Copy-Item .env.example .env
```

Edit `.env` for API-backed commands such as `ask`, `verify-api`, or live
`serve-workbench` without `--fake-ai`. Local deterministic commands and
`--fake-ai` work without an API key.

Useful `.env` fields:

```text
ANTHROPIC_API_KEY=...
ANTHROPIC_BASE_URL=...
HARDWISE_MODEL_FAST=mimo-v2.5
HARDWISE_MODEL_NORMAL=mimo-v2.5
HARDWISE_MODEL_DEEP=mimo-v2.5
```

## Local Commands

Fast deterministic checks:

```powershell
uv run hardwise --help
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component
```

Static workbench, no server and no API key:

```powershell
uv run hardwise design-validator-ui `
  tests/fixtures/allegro/mixed_controller_power_stage.net `
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv `
  --ai-snapshot --output reports/controller-workbench.html
```

Local live workbench server with the deterministic fake model:

```powershell
uv run hardwise serve-workbench `
  tests/fixtures/allegro/mixed_controller_power_stage.net `
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv `
  --fake-ai --port 8765
```

Open `http://127.0.0.1:8765/` in a browser.

## WSL Setup

Use WSL when you want the same shell shape as the macOS/Linux examples:

```bash
git clone <repo> hardwise
cd hardwise
uv sync --extra dev
cp .env.example .env
```

The usual README commands then work unchanged.

## Verification

Run the same fast quality gate locally:

```powershell
uv run ruff check .
uv run pytest -q
```

The GitHub Actions CI workflow runs this gate on both `macos-latest` and
`windows-latest`. Treat Windows as "likely compatible" until that CI job has
passed for the commit you plan to show.

## Notes

- `hardwise eval --download` requires Git on `PATH` because it shells out to
  `git clone`.
- PostgreSQL is optional. The default relational store is SQLite under
  `reports/`.
- Chroma/vector search may initialize extra local model data on first semantic
  retrieval use. The default fast test suite avoids slow vector ranking tests.
