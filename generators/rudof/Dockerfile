# Ubuntu 24.04 for glibc 2.39, which the rudof_generate binary requires.
FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY generators/rudof/vendor/rudof-generate_0.2.20-prerelease-1_amd64.deb /tmp/rudof.deb
RUN dpkg -i /tmp/rudof.deb && rm /tmp/rudof.deb

COPY src/rdfbench/__init__.py src/rdfbench/report.py /app/rdfbench/
COPY generators/_common/entry.py /app/entry.py
COPY generators/rudof/entrypoint.py /app/entrypoint.py

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "/app/entrypoint.py"]
