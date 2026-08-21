.PHONY: test frontend-build compose-config migrate up down

test:
	PYTHONPATH=. pytest -q

frontend-build:
	pnpm run build

compose-config:
	docker compose config

migrate:
	alembic upgrade head

up:
	docker compose up --build

down:
	docker compose down
