# Pinned Python version so every build uses the same interpreter.
FROM python:3.14.10-slim

# Don't write .pyc files, print output immediately (needed for an interactive
# menu), and keep the database on the /data volume.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INVENTORY_DB=/data/inventory.db

WORKDIR /app

# Dependencies change rarely, so install them first. Docker caches this layer
# and reuses it when only the code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code changes often, so it is copied last.
COPY . .

# The database lives on a volume, so data survives when a new container starts.
VOLUME /data

CMD ["python", "main.py"]
