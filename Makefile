.PHONY: test frontend-build compose-config preprod-config preprod-up preprod-down preprod-logs migrate up down

test:
	PYTHONPATH=. pytest -q

frontend-build:
	pnpm run build

compose-config:
	docker compose config

preprod-config:
	docker compose -f docker-compose.yml -f docker-compose.preprod.yml --env-file .env.preprod config

preprod-up:
	docker compose -f docker-compose.yml -f docker-compose.preprod.yml --env-file .env.preprod up -d --build

preprod-down:
	docker compose -f docker-compose.yml -f docker-compose.preprod.yml --env-file .env.preprod down

preprod-logs:
	docker compose -f docker-compose.yml -f docker-compose.preprod.yml --env-file .env.preprod logs -f --tail=200

migrate:
	alembic upgrade head

up:
	docker compose up --build

down:
	docker compose down
