# WatDiv (Waterloo SPARQL Diversity Test Suite) data generator.
#
# The binary hardcodes the relative paths ../../files/firstnames.txt and
# ../../files/lastnames.txt, so it only runs from bin/Release/ inside its own
# tree -- the entrypoint sets that working directory. It also reads
# /usr/share/dict/words, hence wamerican.
FROM ubuntu:22.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential libboost-all-dev python3 wamerican ca-certificates curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN curl -sLO https://dsg.uwaterloo.ca/watdiv/watdiv_v06.tar \
    && tar -xf watdiv_v06.tar \
    && rm watdiv_v06.tar
ENV BOOST_HOME=/usr/lib/
RUN cd /opt/watdiv && make

WORKDIR /app
COPY src/rdfbench/__init__.py src/rdfbench/report.py /app/rdfbench/
COPY generators/_common/entry.py /app/entry.py
COPY generators/watdiv/entrypoint.py /app/entrypoint.py

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "/app/entrypoint.py"]
