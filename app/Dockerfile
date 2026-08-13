FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY . .

# Install Python dependencies
RUN uv pip install --system \
    streamlit \
    pandas \
    plotly \
    matplotlib \
    psycopg \
    pgvector \
    sentence-transformers \
    pydantic \
    python-dotenv \
    openai

# Expose Streamlit port
EXPOSE 8501

# Set environment variables
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true

# Run Streamlit
CMD ["streamlit", "run", "app/app.py"]