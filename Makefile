.PHONY: dev test lint migrate ingest seed deploy-api deploy-web

dev:
	docker-compose up --build

test:
	cd backend && PYTHONPATH=. pytest tests/unit/ -v --tb=short

lint:
	cd backend && ruff check app/ tests/ && ruff format --check app/ tests/

migrate:
	cd backend && PYTHONPATH=. alembic upgrade head

ingest:
	cd backend && PYTHONPATH=. python -m app.ai.ingestion

seed:
	cd backend && PYTHONPATH=. python scripts/seed_dev_data.py

deploy-api:
	docker build -t gcr.io/$$(gcloud config get-value project)/nln-api:latest ./backend
	docker push gcr.io/$$(gcloud config get-value project)/nln-api:latest
	gcloud run deploy nln-api --image gcr.io/$$(gcloud config get-value project)/nln-api:latest --region europe-north1

deploy-web:
	cd frontend && npm run build && firebase deploy --only hosting

emulators:
	firebase emulators:start --only auth,firestore,storage
