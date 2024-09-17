# Makefile for Poetry-managed Python projects

REPO_ROOT_PATH = $(shell git rev-parse --show-toplevel 2> /dev/null)

.PHONY: install format lint

install:
	poetry install --no-interaction

format: install
	poetry run black --config "$(REPO_ROOT_PATH)/pyproject.toml" .
	poetry run isort --config-root $(REPO_ROOT_PATH) --resolve-all-configs .

lint: install
	poetry run black --config "$(REPO_ROOT_PATH)/pyproject.toml" . --check
	poetry run flake8 --config $(REPO_ROOT_PATH)/.flake8 .
	poetry run isort --config-root $(REPO_ROOT_PATH) --resolve-all-configs --check-only --diff .
	poetry run pylint --rcfile $(REPO_ROOT_PATH)/pyproject.toml .
	poetry run mypy --config-file $(REPO_ROOT_PATH)/pyproject.toml .
