.PHONY: dev migrate seed test deploy-gcp lint build clean

# -----------------------------------------------------------
# IP Guardian — Development Commands
# -----------------------------------------------------------

dev:
	docker compose up --build

dev-detached:
	docker compose up --build -d

stop:
	docker compose down

migrate:
	docker compose exec backend alembic upgrade head

migrate-create:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

seed:
	docker compose exec backend python -m app.seed

test:
	docker compose exec backend pytest tests/ -v --tb=short
	cd frontend && npm test -- --watchAll=false

lint:
	cd backend && ruff check . && ruff format --check .
	cd frontend && npm run lint

build:
	cd frontend && npm run build
	cd backend && echo "Backend build OK"

clean:
	docker compose down -v --remove-orphans
	docker system prune -f

deploy-gcp:
	@echo "=== Deploying IP Guardian to GCP ==="
	./infra/deploy.sh

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-worker:
	docker compose logs -f worker

logs-frontend:
	docker compose logs -f frontend
