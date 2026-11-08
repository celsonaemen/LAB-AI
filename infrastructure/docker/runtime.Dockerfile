FROM python:3.12-slim
WORKDIR /app
COPY apps/ai-runtime/pyproject.toml .
COPY apps/ai-runtime/app ./app
COPY infrastructure/database/migrations ./migrations
RUN pip install --no-cache-dir . && useradd --create-home runtime && mkdir -p /home/runtime/.model-cache && chown runtime:runtime /home/runtime/.model-cache
USER runtime
CMD ["sh", "-c", "python -m app.migrate && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-config /app/app/logging.json"]
