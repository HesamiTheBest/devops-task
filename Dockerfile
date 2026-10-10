# the builder
FROM python:3.12 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

#the final image
FROM python:3.12-slim
WORKDIR /app

# create a dedicated non-root user and group for running the app
RUN groupadd --system appgroup && useradd --system --gid appgroup --create-home appuser

COPY --from=builder --chown=appuser:appgroup /install /usr/local

COPY --chown=appuser:appgroup app ./app

# everything below this line runs as appuser, not root
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]