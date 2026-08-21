# sheXer -- shape extraction, not generation.
#
# This image lives under `generators/_extractors/` rather than `generators/` for
# a reason the loader depends on: `Workspace.load_generators` globs
# `generators/*/generator.yaml`, one level deep, so an extractor placed here is
# invisible to it. That is correct -- sheXer consumes RDF and emits a schema, so
# it has no `data_files`, no `rdf_format`, and no place in a profile.
#
# sheXer is pip-installable, so the whole image is one install line.

FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir "shexer>=2.5" "rdflib>=7.0"

COPY generators/_extractors/shexer/entrypoint.py /app/entrypoint.py

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "/app/entrypoint.py"]
