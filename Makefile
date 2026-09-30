.PHONY: test lint typecheck fmt gate demo demo-core up down clean

test:        ## run pytest
	uv run pytest

lint:        ## ruff + mypy strict
	uv run ruff check src tests
	uv run mypy

typecheck:
	uv run mypy

fmt:         ## ruff autofix
	uv run ruff check --fix src tests

gate:        ## phase gate: PHASE=n required (runs tests marked phase<n>)
	@test -n "$(PHASE)" || (echo "usage: make gate PHASE=n"; exit 1)
	uv run pytest -m "phase$(PHASE)"

demo:        ## Experiment 01 smoke: 20 ticks, mock LLM, report
	uv run python -m agentville.cli demo

demo-core:   ## headless 200-tick engine run with mock agents
	uv run python -m agentville.cli run --ticks 200 --mock

up:
	docker compose up -d --build

down:
	docker compose down

clean:
	rm -rf data .pytest_cache .mypy_cache .ruff_cache dist
