# Use Ubuntu 24.04 for newer glibc (2.39) required by rudof binary
FROM ubuntu:24.04

# Install Python, Java 21, and system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    openjdk-21-jre-headless \
    wget \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME environment variable
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# Set working directory
WORKDIR /app

# Download and install RUDOF binary v0.2.19
RUN wget https://github.com/rudof-project/rudof/releases/download/0.2.19/rudof_0.2.19_amd64.deb && \
    dpkg -i rudof_0.2.19_amd64.deb

# Copy benchmark scripts and schema files
COPY execute_benchmark_binary.py .
COPY example_schema.shex .

# Create output directory as a volume mount point
VOLUME ["/app/output"]

# Set the entrypoint to run the binary-based benchmark script
ENTRYPOINT ["python3", "execute_benchmark_binary.py"]
