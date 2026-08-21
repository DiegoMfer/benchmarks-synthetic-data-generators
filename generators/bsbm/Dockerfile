# Build context is the project root, so this image can copy the shared entry
# library and the canonical report schema alongside its own vendored jars.
FROM eclipse-temurin:21-jre-jammy

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Shared, identical in every generator image.
COPY src/rdfbench/__init__.py src/rdfbench/report.py /app/rdfbench/
COPY generators/_common/entry.py /app/entry.py

# Generator-specific.
COPY generators/bsbm/vendor/ /app/
COPY generators/bsbm/entrypoint.py /app/entrypoint.py

# bsbmtools writes scratch state next to its jars and runs as the host UID, so
# these must be writable by an arbitrary non-root user.
RUN mkdir -p /app/td_data && chmod -R 777 /app

ENV PYTHONUNBUFFERED=1 JAVA_OPTS="-Xmx2G"
ENTRYPOINT ["python3", "/app/entrypoint.py"]
