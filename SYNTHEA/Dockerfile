# Synthea FHIR generator + official HL7 FHIR (org.hl7.fhir.core) Turtle converter
# Ubuntu 24.04 mirrors the RUDOFGENERATE image for a consistent toolchain.
FROM ubuntu:24.04

# Java 21 JDK (Synthea needs 17+; javac compiles the Turtle converter against
# the org.hl7.fhir.core classes), Python 3 + rdflib for merging,
# wget/ca-certificates for fetching the jars.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    openjdk-21-jdk-headless \
    python3 \
    python3-rdflib \
    wget \
    ca-certificates \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

WORKDIR /app

# Synthea (binary distribution, master-branch-latest) and the official
# org.hl7.fhir.core library jar (shipped as validator_cli.jar; it bundles the
# org.hl7.fhir.r4.formats.RdfParser used for JSON -> Turtle serialization).
RUN wget -q -O synthea-with-dependencies.jar \
      https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar && \
    wget -q -O validator_cli.jar \
      https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar

# Compile the JSON -> Turtle converter against the org.hl7.fhir.core classes.
COPY FhirJsonToTurtle.java .
RUN mkdir -p classes && \
    javac -cp validator_cli.jar -d classes FhirJsonToTurtle.java

COPY execute_synthea_benchmark.py .

VOLUME ["/app/output"]

ENTRYPOINT ["python3", "execute_synthea_benchmark.py"]
