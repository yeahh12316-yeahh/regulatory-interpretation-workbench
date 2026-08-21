.PHONY: test frontend-build compose-config up down

test:
	PYTHONPATH=. pytest -q

frontend-build:
	pnpm run build

compose-config:
	docker compose config

up:
	docker compose up --build

down:
	docker compose down
