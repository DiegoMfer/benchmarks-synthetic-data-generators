# LEMMING - example-mimicking knowledge graph generator.
# The same repository also ships SimplexKG, selected with -m Simplex, so this
# one image covers both generators.
#
# BUILD FRAGILITY. This is the only generator built from source at image-build
# time, and the build has hung indefinitely more than once -- observed wedged
# with no CPU in the container. Root cause, confirmed by hand: pom.xml pulls
# three artifacts (org.aksw:word2vec-restful-webservice, grph:grph,
# org.dice_research:ldcbench.api) that exist ONLY on maven.aksw.org, a small
# university-hosted Nexus. It is not simply slow or unreachable -- a raw TCP
# connect to it succeeds immediately, but the TLS handshake past that point
# never completes, so no read/connect-timeout system property (tried
# maven.wagon.http.*, aether.connector.*) has anything to bind against; the
# socket just sits open. The only thing that reliably bounds it is an
# OS-level wall-clock timeout around the whole command.
#
# The retry loop below is the fix: each attempt is capped at 3 minutes, and
# already-downloaded artifacts stay in the shared ~/.m2 cache across attempts,
# so a retry only re-pays for whatever the previous attempt was stuck on. This
# mirrors the git timeouts already in place for the clone step.
#
# Vendoring the artefact instead is not an option: the shaded jar is 97 MB.
# Build the image once, ahead of any timing run, and use --skip-build after.
#
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /src
RUN git config --global http.lowSpeedLimit 1000 \
    && git config --global http.lowSpeedTime 60 \
    && git clone --depth 1 https://github.com/dice-group/LEMMING.git .
RUN ok=0; \
    for i in 1 2 3 4 5; do \
        echo "mvn build attempt $i/5 ..."; \
        if timeout 180 mvn -q -B clean package -DskipTests; then ok=1; break; fi; \
        echo "  attempt $i timed out or failed (maven.aksw.org is a known-flaky dependency host) -- retrying in 15s"; \
        sleep 15; \
    done; \
    if [ "$ok" != 1 ]; then \
        echo "mvn build failed after 5 attempts, most likely maven.aksw.org being unreachable" >&2; \
        exit 1; \
    fi

FROM eclipse-temurin:17-jre
RUN apt-get update && apt-get install -y --no-install-recommends python3 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /src/target/ /app/target/
COPY --from=build /src/src/test/resources/ /app/testdata/
COPY src/rdfbench/__init__.py src/rdfbench/report.py /app/rdfbench/
COPY generators/_common/entry.py /app/entry.py
COPY generators/lemming/entrypoint.py /app/entrypoint.py
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "/app/entrypoint.py"]
