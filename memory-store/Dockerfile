# Build context: mcp-bank/ repo root
# Deploy with: fly deploy --config memory-store/fly.toml (from repo root)
FROM python:3.12-slim

WORKDIR /app

# Install system deps for sentence-transformers and asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy shared utilities first (referenced at runtime via sys.path)
COPY shared/ /shared/

# Copy service source
COPY memory-store/pyproject.toml ./
RUN pip install --no-cache-dir -e "."

COPY memory-store/ .

EXPOSE 8080

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
