# Synthea (FHIR R4 JSON) + the official org.hl7.fhir.core Turtle converter.
# A JDK, not just a JRE: javac compiles FhirJsonToTurtle against the HL7 classes.
FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       openjdk-21-jdk-headless python3 wget ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

WORKDIR /app

# validator_cli.jar ships org.hl7.fhir.core, which provides the RdfParser used
# for the JSON -> Turtle conversion.
RUN wget -q -O synthea-with-dependencies.jar \
      https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar \
    && wget -q -O validator_cli.jar \
      https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar

COPY generators/synthea/FhirJsonToTurtle.java .
RUN mkdir -p classes && javac -cp validator_cli.jar -d classes FhirJsonToTurtle.java

COPY src/rdfbench/__init__.py src/rdfbench/report.py /app/rdfbench/
COPY generators/_common/entry.py /app/entry.py
COPY generators/synthea/entrypoint.py /app/entrypoint.py

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "/app/entrypoint.py"]
