install:
	poetry install --with dev

lint:
	poetry run ruff check .
	poetry run ruff format --check .
	poetry run mypy --config-file pyproject.toml .

test:
	poetry run pytest -m "not integration"

test-integration:
	poetry run pytest -m "integration"

precommit-install:
	poetry run pre-commit install
