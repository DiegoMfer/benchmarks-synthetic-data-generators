# Use official Java image
FROM eclipse-temurin:21-jre-jammy

# Install Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy GAIA generator and dependencies
COPY OWLGenerator.jar ./
COPY lib/ ./lib/
COPY execute_benchmark.py ./

# Copy run script
COPY run-benchmark.sh ./
RUN chmod +x run-benchmark.sh

# Create output directory
RUN mkdir -p output

# Set default command
ENTRYPOINT ["python3", "execute_benchmark.py"]

# Default parameters
CMD ["--instances", "3"]
