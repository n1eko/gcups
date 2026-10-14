FROM docker.io/library/python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/n1eko/gcups" \
      org.opencontainers.image.description="Prometheus exporter for the Green Cell UPS app (GC UPS)" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY gcups_exporter ./gcups_exporter

ENV GCUPS_URL=http://gcups:8080 \
    EXPORTER_PORT=9199 \
    PYTHONUNBUFFERED=1

EXPOSE 9199
USER nobody
ENTRYPOINT ["python3", "-m", "gcups_exporter"]
