.PHONY: install run test lint clean help

help:
	@echo "Targets:"
	@echo "  install  — uv sync (creates .venv, installs deps)"
	@echo "  run      — uv run hardwise hello (sanity check)"
	@echo "  test     — uv run pytest -q"
	@echo "  lint     — uv run ruff check ."
	@echo "  clean    — remove .venv and caches"

install:
	uv sync

run:
	uv run hardwise hello

test:
	uv run pytest -q

lint:
	uv run ruff check .

clean:
	rm -rf .venv .ruff_cache .pytest_cache build dist *.egg-info
