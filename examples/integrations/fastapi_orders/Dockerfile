# examples/integrations/fastapi_orders/Dockerfile
# Build context is the REPOSITORY ROOT so the image runs the library from
# this checkout (the [fastapi] extra is newer than some PyPI releases):
#   docker build -f examples/integrations/fastapi_orders/Dockerfile -t xsm-orders .
# Once released, `pip install "xstate-statemachine[fastapi,redis]"` works too.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install ".[fastapi,redis]" "uvicorn>=0.30"

WORKDIR /app
# Every module app.py imports (migrations.py too) and both charts --
# tests/test_battle_277_readme.py pins this list against app.py's imports.
COPY examples/integrations/fastapi_orders/machine.json \
     examples/integrations/fastapi_orders/machine_v2.json \
     examples/integrations/fastapi_orders/migrations.py \
     examples/integrations/fastapi_orders/models.py \
     examples/integrations/fastapi_orders/logic.py \
     examples/integrations/fastapi_orders/app.py ./
COPY examples/integrations/fastapi_orders/static ./static

RUN useradd --create-home --uid 10001 app && mkdir /data && chown app /data
USER app
ENV XSM_ORDERS_DB=/data/orders.db

EXPOSE 8000
# Readiness (/_xsm/ready): 503 until the store answers, unlike /_xsm/health.
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/_xsm/ready', timeout=2)"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
