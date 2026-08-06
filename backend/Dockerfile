# Backend image: API and worker share it, differing only in the command they run.
FROM python:3.12-slim

WORKDIR /app

# Build tools for psycopg, then removed to keep the image small.
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Requirements first so dependency layers survive code edits.
# torch alone is 500+ MB; a stalled connection on a slow line hits pip's
# default 15s read timeout well before that finishes, killing the whole
# build. Longer timeout + more retries make it resilient to that, not just
# fast connections.
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 100 --retries 10 -r requirements.txt

# Bake the embedding model into the image so first run is not a 130 MB download.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('BAAI/bge-small-en-v1.5')"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
