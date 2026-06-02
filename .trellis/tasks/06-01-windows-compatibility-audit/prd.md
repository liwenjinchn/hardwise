# Windows compatibility audit

## Goal

Answer whether Hardwise can be used on Windows today, identify concrete
compatibility risks, and define the minimum work needed to make Windows support
credible for users.

User value: a Windows hardware engineer should know whether to use native
Windows, PowerShell, or WSL, and which commands are expected to work.

## Confirmed Facts

- The project is packaged as a normal Python 3.11+ application with a
  `hardwise = "hardwise.cli:app"` console entry point in `pyproject.toml`.
- Runtime dependencies are cross-platform in principle: `uv` supports Windows
  installation, ChromaDB publishes Windows wheels, and `pdfplumber` is a pure
  Python wheel on PyPI.
- CLI code mostly uses `pathlib.Path`, Typer path arguments, `encoding="utf-8"`
  file I/O, SQLite/SQLAlchemy, FastAPI, and uvicorn. No production code calls
  `xdg-open`, macOS `open`, shell scripts, or POSIX-only path APIs.
- The eval download path uses `subprocess.run(["git", ...])`, so Windows users
  need `git` available on `PATH` for `hardwise eval --download`.
- README and docs currently show bash/POSIX commands only, including `cp`,
  `export`, and `/tmp/...` paths. These are documentation blockers for native
  Windows users, not core runtime blockers.
- The repository has no Windows CI matrix and this audit did not run on a real
  Windows host, so the current status should be described as "likely works,
  not verified" rather than "Windows supported".
- Local smoke checks on the current host passed for `hardwise hello`, a KiCad
  `review` run, and `serve-workbench --fake-ai --dry-run`.

## Requirements

- Provide a clear Windows usage path for:
  - native PowerShell setup
  - optional WSL setup
  - API-backed `.env` configuration
  - local static workbench generation
  - local live workbench server
- Distinguish required tools (`uv`, Python resolved by `uv`, `git` for eval
  download) from optional tools (PostgreSQL, live API key, Chroma vector store).
- Avoid claiming full Windows support until at least one Windows test run passes.
- Close this track as a focused documentation + CI change. Do not redo the
  broad audit unless CI reports a concrete Windows blocker.
- Add Windows-specific README/docs snippets and a GitHub Actions Windows job
  for `uv sync`, `uv run ruff check .`, and `uv run pytest -q`.

## Acceptance Criteria

- [x] Audit packaging, CLI entry points, dependency shape, path handling, and
  shell assumptions.
- [x] Identify blockers versus documentation gaps.
- [x] Provide a concrete Windows setup and usage recipe.
- [x] Add Windows README/docs snippets.
- [x] Add CI validation on `windows-latest` for dependency sync, lint, and fast
      tests.
- [ ] Run `uv run pytest -q` and `uv run ruff check .` on Windows or CI before
  declaring Windows support officially verified.

## Current Recommendation

Native Windows should be usable for the main CLI and workbench paths, but the
project should document it as "Windows likely compatible, not yet CI-verified".
WSL remains the lowest-friction recommendation until Windows CI is added.

The next implementation should be intentionally small: add PowerShell/WSL usage
snippets and a `windows-latest` CI job, then use the GitHub Actions result as
the first Windows verification signal.

## Out of Scope

- Supporting company-internal hardware data.
- Adding Windows installers or binary releases.
- Changing core architecture only for Windows unless CI reveals a real blocker.
