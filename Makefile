UV ?= uv
MAP ?=

.DEFAULT_GOAL := install

.PHONY: install run debug clean lint lint-strict

install:
	@$(UV) sync --locked

run:
	@$(UV) run --locked python main.py $(MAP)

debug:
	@$(UV) run --locked python -m pdb main.py $(MAP)

clean:
	@rm -rf .venv .mypy_cache .pytest_cache __pycache__ */__pycache__

lint:
	@$(UV) run --locked flake8 . --extend-exclude .venv
	@$(UV) run --locked mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	@$(UV) run --locked flake8 . --extend-exclude .venv
	@$(UV) run --locked mypy . --strict

