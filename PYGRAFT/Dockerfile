# PyGraft Benchmark Docker Image
# Python 3.11 with Java 17 for HermiT reasoner

FROM python:3.11-slim

# Install Java (required for HermiT reasoner in PyGraft)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME environment variable
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# Set working directory
WORKDIR /app

# Install PyGraft and dependencies
RUN pip install --no-cache-dir pygraft

# Copy benchmark execution script
COPY execute_benchmark.py .

# Create output directory
RUN mkdir -p output

# Set volume for output
VOLUME /app/output

# Default command: show help
CMD ["python", "execute_benchmark.py", "--help"]
