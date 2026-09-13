# Ubuntu 24.04 for glibc 2.39, which the rudof binary requires.
FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# The published release artifact, vendored so a clone builds without network
# access and every run is traceable to one upstream release:
#   https://github.com/rudof-project/rudof/releases/tag/0.3.21
#   asset rudof_0.3.21_amd64.deb, sha256
#   16be829bf9785af9cb52de778e78cd8020b428c2e68d14b6cac0fbc92f3ae3cd
# Pinned by filename rather than a glob, so the image records which build it
# installs. Bump this line and the vendored file together.
COPY generators/rudof/vendor/rudof_0.3.21_amd64.deb /tmp/rudof.deb
RUN dpkg -i /tmp/rudof.deb && rm /tmp/rudof.deb

COPY src/rdfbench/__init__.py src/rdfbench/report.py /app/rdfbench/
COPY generators/_common/entry.py /app/entry.py
COPY generators/rudof/entrypoint.py /app/entrypoint.py

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "/app/entrypoint.py"]
