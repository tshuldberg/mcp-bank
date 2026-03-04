FROM python:3.12-slim

WORKDIR /app

# System deps for lxml, pymupdf, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e "."

# Copy shared utilities from repo root (mounted via build context)
COPY shared/ /app/shared/

COPY src/ ./src/

ENV PYTHONPATH=/app
ENV PORT=8080

EXPOSE 8080

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
