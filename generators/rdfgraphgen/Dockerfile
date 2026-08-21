FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir rdf-graph-gen

COPY src/rdfbench/__init__.py src/rdfbench/report.py /app/rdfbench/
COPY generators/_common/entry.py /app/entry.py
COPY generators/rdfgraphgen/entrypoint.py /app/entrypoint.py

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "/app/entrypoint.py"]
