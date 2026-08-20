SHELL := /bin/bash
PYTHON ?= python3
export PYTHONPATH := $(PWD)/src

.PHONY: install generate-data train evaluate retrain run-api run-stream produce-events demo benchmark lint typecheck test format docker-up docker-down validate-compose

install:
	$(PYTHON) -m pip install -e '.[dev]'

generate-data:
	$(PYTHON) -m recommendation_platform.ingestion.generator --users 1000 --items 500 --interactions 20000 --output data

train:
	$(PYTHON) -m recommendation_platform.training.train --data-dir data --output data/processed

evaluate:
	$(PYTHON) -m recommendation_platform.evaluation.evaluate --data-dir data --model-path data/processed/model.joblib

retrain:
	$(PYTHON) pipelines/retrain.py --data-dir data --output-dir data/processed

run-api:
	uvicorn recommendation_platform.api.main:app --host 0.0.0.0 --port 8000 --reload

run-stream:
	$(PYTHON) -m recommendation_platform.streaming.processor --demo

produce-events:
	$(PYTHON) -m recommendation_platform.ingestion.producer --count 20

demo:
	$(PYTHON) scripts/demo.py

benchmark:
	$(PYTHON) scripts/benchmark.py

lint:
	ruff check src tests scripts

format:
	ruff format src tests scripts

typecheck:
	mypy src

test:
	pytest

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down -v

validate-compose:
	docker compose config >/dev/null

test-fast:
	pytest tests/unit
