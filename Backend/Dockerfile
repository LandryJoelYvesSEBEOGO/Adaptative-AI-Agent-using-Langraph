FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# Dépendances d'abord (couche mise en cache). `--extra ml` : reranker et modèles locaux.
COPY pyproject.toml uv.lock ./
ARG UV_EXTRAS="--extra ml --extra ingest"
RUN uv sync --frozen --no-dev --no-install-project ${UV_EXTRAS}

COPY . .
ENV PATH="/app/.venv/bin:$PATH"

# Processus non-root ; /app/data (PDF, repli SQLite) doit rester inscriptible
RUN useradd --system --uid 10001 --home /app app && mkdir -p /app/data && chown -R app /app/data
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

# Les migrations Alembic sont appliquées au démarrage (AUTO_MIGRATE=true).
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
