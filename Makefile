-include .env
export

# Common commands
pre-commit.install:
	uv run pre-commit install
install:
	uv sync --all-packages
lint:
	uv run ruff format
	uv run ruff check --fix
	uv run mypy
	uv run mypy services/ingest
	uv run mypy services/migrations
test:
	uv run pytest services/ingest
	uv run pytest services/migrations
synth:
	cd cdk && cdk synth --quiet

# Layers commands
lock.layers:
	uv pip compile layers/common/pyproject.toml --python-platform x86_64-manylinux2014 --python-version 3.14 --only-binary :all: --output-file layers/common/pylock.toml
build.layers:
	uv pip install --requirements layers/common/pylock.toml --target layers/common/build/python --python-platform x86_64-manylinux2014 --python-version 3.14 --only-binary :all:

# Local docker commands
local.up:
	docker compose up --detach --wait
local.down:
	docker compose down --volumes

# Migrations service commands
migrations := candidate-search-service-database-migrations

migrations.local.generate: local.up
	cd services/migrations && uv run alembic upgrade head
	cd services/migrations && uv run alembic revision --autogenerate
migrations.local.upgrade: local.up
	cd services/migrations && uv run alembic upgrade head
migrations.local.downgrade: local.up
	cd services/migrations && uv run alembic downgrade -1

migrations.aws.upgrade:
	aws lambda invoke --function-name $(migrations) --cli-binary-format raw-in-base64-out --payload '{}' response.json
migrations.aws.downgrade:
	aws lambda invoke --function-name $(migrations) --cli-binary-format raw-in-base64-out --payload '{"action": "downgrade"}' response.json
migrations.aws.logs:
	aws logs tail /aws/lambda/$(migrations) --since 10m --follow
