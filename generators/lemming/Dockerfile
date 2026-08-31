# LEMMING - example-mimicking knowledge graph generator.
# The same repository also ships SimplexKG, selected with -m Simplex, so this
# one image covers both generators.
#
# THIS IMAGE HAS TWO BUILD PATHS. See BUILD_ISSUE.txt for the full history.
#
#   vendor (default) - copies a prebuilt shaded jar from vendor/. No network,
#                      builds in seconds, works anywhere. This is the only path
#                      that currently works, because the upstream Maven host is
#                      offline (see below). Obtain the jar with:
#                          ./generators/lemming/export-vendor.sh
#                      run on a machine that already has the image, then copy
#                      generators/lemming/vendor/ across.
#
#   source           - clones and builds from source. Kept because it documents
#                      how the vendored jar was produced and will work again if
#                      the host returns. Select with:
#                          docker build --build-arg LEMMING_JAR_SOURCE=source ...
#
# WHY THE SOURCE PATH FAILS. pom.xml pulls three artifacts that exist ONLY on
# maven.aksw.org, a university-hosted Nexus: org.aksw:word2vec-restful-webservice,
# grph:grph, and org.dice_research:ldcbench.api. That host stopped answering HTTP
# in 2026 -- TCP connect and the TLS handshake both complete, but the request
# never gets a reply, so Maven, which sets no default timeout on that socket,
# hangs forever instead of failing. Verified unreachable from two independent
# networks, so this is the server being down rather than a local network path.
# The retry loop below therefore bounds each attempt with an OS-level timeout;
# it is the only thing that reliably stops the hang.
#
ARG LEMMING_JAR_SOURCE=vendor

# ---------------------------------------------------------------------------
# Path A: build from source. Only reachable when maven.aksw.org answers.
# BuildKit skips this stage entirely unless it is the selected one.
# ---------------------------------------------------------------------------
FROM maven:3.9-eclipse-temurin-17 AS source
WORKDIR /src
RUN git config --global http.lowSpeedLimit 1000 \
    && git config --global http.lowSpeedTime 60 \
    && git clone --depth 1 https://github.com/dice-group/LEMMING.git .
RUN ok=0; \
    for i in 1 2 3; do \
        echo "mvn build attempt $i/3 ..."; \
        if timeout 300 mvn -q -B clean package -DskipTests; then ok=1; break; fi; \
        echo "  attempt $i timed out or failed -- retrying in 10s"; \
        sleep 10; \
    done; \
    if [ "$ok" != 1 ]; then \
        echo "" >&2; \
        echo "mvn build failed after 3 attempts." >&2; \
        echo "maven.aksw.org has been offline since 2026; this is expected." >&2; \
        echo "Use the vendored jar instead - see generators/lemming/BUILD_ISSUE.txt" >&2; \
        exit 1; \
    fi
# Normalise the layout so both paths hand the runtime stage the same two paths.
RUN cp /src/target/lemming.jar /lemming.jar \
    && cp -r /src/src/test/resources /testdata

# ---------------------------------------------------------------------------
# Path B: the prebuilt jar. No network, no Maven, seconds instead of minutes.
# ---------------------------------------------------------------------------
FROM busybox:1.36 AS vendor
COPY generators/lemming/vendor/lemming.jar /lemming.jar
COPY generators/lemming/vendor/testdata /testdata

# ---------------------------------------------------------------------------
# Whichever of the two was selected.
# ---------------------------------------------------------------------------
ARG LEMMING_JAR_SOURCE
FROM ${LEMMING_JAR_SOURCE} AS jar

# ---------------------------------------------------------------------------
# Runtime. Only the shaded jar is copied; the source build's target/ also holds
# a second identical 101 MB jar plus test classes, which doubled the image.
# ---------------------------------------------------------------------------
FROM eclipse-temurin:17-jre
RUN apt-get update && apt-get install -y --no-install-recommends python3 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=jar /lemming.jar /app/target/lemming.jar
COPY --from=jar /testdata /app/testdata
COPY src/rdfbench/__init__.py src/rdfbench/report.py /app/rdfbench/
COPY generators/_common/entry.py /app/entry.py
COPY generators/lemming/entrypoint.py /app/entrypoint.py
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "/app/entrypoint.py"]
