pre-commit.install:
	uv run pre-commit install

install:
	uv sync --all-packages

lock.layers:
	uv pip compile layers/common/pyproject.toml --python-platform x86_64-manylinux2014 --python-version 3.14 --only-binary :all: --output-file layers/common/pylock.toml

build.layers:
	uv pip install --requirements layers/common/pylock.toml --target layers/common/build/python --python-platform x86_64-manylinux2014 --python-version 3.14 --only-binary :all:

lint:
	uv run ruff format
	uv run ruff check --fix
	uv run mypy

test:
	uv run pytest

synth:
	cd cdk && cdk synth --quiet
