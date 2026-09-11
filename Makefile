pre-commit.install:
	uv run pre-commit install

install:
	uv sync --all-packages

lint:
	uv run ruff format
	uv run ruff check --fix
	uv run mypy

test:
	uv run pytest

synth:
	cd cdk && cdk synth --quiet
