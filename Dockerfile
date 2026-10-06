# the builder
FROM python:3.12 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

#the final image
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local

COPY app ./app
CMD ["uvicorn", "app.main:app", "--host","0.0.0.0", "--port", "8000"]