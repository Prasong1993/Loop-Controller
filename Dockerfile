FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app
WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY nexus ./nexus
COPY openapi.yaml ./openapi.yaml

RUN useradd --create-home --uid 10001 nexus \
    && mkdir -p /app/data \
    && chown -R nexus:nexus /app
USER nexus

EXPOSE 8000 8001
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()" || exit 1

CMD ["uvicorn", "nexus.api:app", "--host", "0.0.0.0", "--port", "8000"]
