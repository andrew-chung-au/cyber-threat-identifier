.PHONY: help install app dashboard docker-up docker-down eval-llm


help:
	@echo "Cyber Threat Identifier — Available Commands"
	@echo ""
	@echo "  make install        Install all dependencies (including Streamlit)"
	@echo "  make app            Run Streamlit app (home page with tabs)"
	@echo "  make dashboard      Run Streamlit dashboard page"
	@echo "  make docker-up      Start PostgreSQL + Streamlit with Docker"
	@echo "  make docker-down    Stop Docker containers"
	@echo "  make eval-llm       Run LLM evaluation (3.1 vs 3.5 Flash-Lite)"
	@echo ""


install:
	uv pip install streamlit plotly matplotlib


app:
	PYTHONPATH=. uv run streamlit run app/home.py --server.fileWatcherType=none


dashboard:
	PYTHONPATH=. uv run streamlit run app/pages/1_dashboard.py --server.fileWatcherType=none


docker-up:
	docker-compose up --build


docker-down:
	docker-compose down


eval-llm:
	uv run python -m src.evaluation.run_expert_llm_comparison --limit 226