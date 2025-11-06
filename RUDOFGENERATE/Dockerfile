FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pyrudof (RUDOF Python bindings for RDF generation)
RUN pip install --no-cache-dir pyrudof

# Copy benchmark scripts and schema files
COPY execute_benchmark.py .
COPY example_schema.shex .

# Create output directory as a volume mount point
VOLUME ["/app/output"]

# Set the entrypoint to run the benchmark script
ENTRYPOINT ["python3", "execute_benchmark.py"]
