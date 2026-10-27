FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund --fetch-timeout=30000 --fetch-retries=1 --loglevel=http
COPY tailwind.config.cjs tailwind.customer.config.cjs ./
COPY templates ./templates
COPY static ./static
RUN npm run build:css

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 appuser
COPY --chown=appuser:appuser main.py ./
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser ops ./ops
COPY --chown=appuser:appuser templates ./templates
COPY --chown=appuser:appuser static ./static
COPY --from=frontend --chown=appuser:appuser /build/static/css/dist/dashboard.css ./static/css/dist/dashboard.css
COPY --from=frontend --chown=appuser:appuser /build/static/css/dist/customer.css ./static/css/dist/customer.css
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)" || exit 1
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
