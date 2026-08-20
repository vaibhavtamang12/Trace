# Development

Create a Python 3.11 virtual environment and install the project with development extras:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

The fastest reproducible loop is `make generate-data`, `make train`, `make test`, and `make run-api`. Run `make lint` for Ruff checks and `make typecheck` for Mypy. The project keeps production logic under `src/recommendation_platform`, with tests organized by unit, integration, end-to-end, and ML concerns.

The default generator command uses a smaller local dataset for fast feedback. The same generator supports the larger portfolio brief through explicit flags, for example `python -m recommendation_platform.ingestion.generator --users 10000 --items 5000 --interactions 500000 --output data`.

Before committing, run `make lint && make typecheck && make test`. CI repeats these checks and builds the container image on pull requests.
