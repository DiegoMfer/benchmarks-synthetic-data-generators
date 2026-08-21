FROM eclipse-temurin:21-jre-jammy

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY src/rdfbench/__init__.py src/rdfbench/report.py /app/rdfbench/
COPY generators/_common/entry.py /app/entry.py

COPY generators/linkgen/vendor/ /app/
COPY generators/linkgen/entrypoint.py /app/entrypoint.py

# linkgen resolves its log4j config and scratch state relative to /app while
# running as the host UID.
RUN chmod -R a+rX /app && chmod 777 /app

ENV PYTHONUNBUFFERED=1 JAVA_OPTS="-Xmx4G"
ENTRYPOINT ["python3", "/app/entrypoint.py"]
