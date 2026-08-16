.PHONY: help up down logs ingest reset app dashboard

help:
	@echo "Cyber Threat Identifier — Available Commands"
	@echo ""
	@echo "  make up          Start PostgreSQL and Streamlit"
	@echo "  make ingest      Rebuild ATT&CK corpus, database, and embeddings in Compose"
	@echo "  make down        Stop containers"
	@echo "  make logs        Follow Streamlit logs"
	@echo "  make reset       Delete database volume, then rebuild the full local stack"
	@echo "  make app         Run Streamlit on host (development)"
	@echo "  make dashboard   Run dashboard on host (development)"

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f streamlit

ingest:
	docker compose --profile ingest run --rm ingest

reset:
	docker compose down -v
	docker compose up -d --build
	docker compose --profile ingest run --rm ingest