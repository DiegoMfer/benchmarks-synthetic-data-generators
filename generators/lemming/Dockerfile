# LEMMING - example-mimicking knowledge graph generator.
# The same repository also ships SimplexKG, selected with -m Simplex, so this
# one image covers both generators.
#
# BUILD FRAGILITY. This is the only generator built from source at image-build
# time, and the clone has hung indefinitely more than once -- observed wedged at
# 24 minutes with no CPU in the container. The timeouts below turn that hang
# into a fast failure with a clear message; without them a stalled clone looks
# exactly like a slow one and silently blocks a whole profile.
#
# Vendoring the artefact instead is not an option: the shaded jar is 97 MB.
# Build the image once, ahead of any timing run, and use --skip-build after.
#
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /src
RUN git config --global http.lowSpeedLimit 1000 \
    && git config --global http.lowSpeedTime 60 \
    && git clone --depth 1 https://github.com/dice-group/LEMMING.git . \
    && mvn -q -B clean package -DskipTests

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
