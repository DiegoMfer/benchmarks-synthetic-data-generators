# EvoGen -- NOT WIRED INTO ANY PROFILE. Kept so the attempt is reproducible.
#
# The image builds and EvoGen compiles cleanly (7 .java files, Jena 2.12,
# commons-lang3, slf4j), but the generator crashes before producing a complete
# dataset on every parameter combination documented in its own README:
#
#   -versions 1            ArithmeticException: / by zero
#                          (EvoGenerator.java:1029, schemaEvol/(evoVersions-1))
#   -univ 1|2, -versions 2 IllegalArgumentException: bound must be positive
#                          (_getRandomFromRange -> _AssignGraduateCourse:1608)
#   -univ 5, -versions 2   NullPointerException at main:759, after emitting only
#                          27 .owl files (LUBM emits ~15 per university, so the
#                          output is truncated)
#
# The failures are in EvoGen's own generation logic, not in this packaging.
# Last upstream commit: 2017-01.
#
# EvoGen - LUBM-derived generator that also supports evolving datasets.
# Source-only distribution (7 .java files, no build file), compiled here against
# Jena 2.12 as its README requires. A throwaway POM is used so Maven resolves
# Jena's full transitive tree (slf4j, xerces, ...) rather than just the named
# artifacts.
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /src
RUN git clone --depth 1 https://github.com/MMeimaris/EvoGen.git .

RUN printf '%s' '<project xmlns="http://maven.apache.org/POM/4.0.0">\
<modelVersion>4.0.0</modelVersion><groupId>x</groupId><artifactId>deps</artifactId>\
<version>1</version><dependencies>\
<dependency><groupId>org.apache.jena</groupId><artifactId>jena-core</artifactId><version>2.12.1</version></dependency>\
<dependency><groupId>org.apache.jena</groupId><artifactId>jena-arq</artifactId><version>2.12.1</version></dependency>\
<dependency><groupId>org.apache.commons</groupId><artifactId>commons-lang3</artifactId><version>3.14.0</version></dependency>\
<dependency><groupId>org.slf4j</groupId><artifactId>slf4j-simple</artifactId><version>1.7.36</version></dependency>\
</dependencies></project>' > /tmp/deps-pom.xml \
    && mvn -q -B -f /tmp/deps-pom.xml dependency:copy-dependencies -DoutputDirectory=/deps

RUN mkdir -p /out/classes \
    && javac -nowarn -cp "/deps/*" -d /out/classes $(find /src/src -name '*.java')

FROM eclipse-temurin:17-jre
RUN apt-get update && apt-get install -y --no-install-recommends python3 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /out/classes /app/classes
COPY --from=build /deps /app/deps
COPY src/rdfbench/__init__.py src/rdfbench/report.py /app/rdfbench/
COPY generators/_common/entry.py /app/entry.py
COPY generators/evogen/entrypoint.py /app/entrypoint.py
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "/app/entrypoint.py"]
