# PyGraft runs the HermiT reasoner through owlready2, which shells out to
# `java`, so this image needs a JRE as well as Python.
FROM eclipse-temurin:21-jre-jammy

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip3 install --no-cache-dir pygraft

COPY src/rdfbench/__init__.py src/rdfbench/report.py /app/rdfbench/
COPY generators/_common/entry.py /app/entry.py
COPY generators/pygraft/entrypoint.py /app/entrypoint.py

ENV PYTHONUNBUFFERED=1 JAVA_HOME=/opt/java/openjdk
ENTRYPOINT ["python3", "/app/entrypoint.py"]
