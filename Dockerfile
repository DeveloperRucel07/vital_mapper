FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --break-system-packages .

# Security by Design: Prozess laeuft nicht als root
RUN useradd --create-home appuser \
    && mkdir -p /var/lib/vital-mapper/audio \
    && chown -R appuser:appuser /var/lib/vital-mapper
USER appuser

EXPOSE 8000
CMD ["uvicorn", "vital_mapper.interfaces.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
