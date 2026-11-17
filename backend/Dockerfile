FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
# Seed demo data only when the database does not exist yet, so restarts keep data.
CMD ["sh", "-c", "[ -f /data/samavesh.db ] || python -m app.seed --wipe-prod; exec uvicorn app.main:app --host 0.0.0.0 --port 8210"]
