# Runtime image installs only the reviewed, checked-in dependency lock.
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.4 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

FROM python:3.12-slim
RUN useradd --uid 10001 --create-home sentinel
WORKDIR /app
COPY --from=build --chown=sentinel:sentinel /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER sentinel
EXPOSE 8000
CMD ["uvicorn", "app.entrypoints.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
