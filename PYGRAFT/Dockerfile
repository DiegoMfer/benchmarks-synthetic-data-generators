# PyGraft Benchmark Docker Image with Java and Python

FROM eclipse-temurin:21-jre-jammy

# Install Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

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
