FROM python:3.13-slim

WORKDIR /app

# System deps needed by psycopg (Postgres driver)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Hugging Face Spaces expects port 7860
EXPOSE 7860

# uvicorn reads PORT if set, otherwise 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
