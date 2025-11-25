# Use Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install rdf-graph-gen from PyPI
RUN pip install --no-cache-dir rdf-graph-gen

# Copy the benchmark execution script and sample files
COPY execute_benchmark.py /app/
COPY input-shape.ttl /app/

# Create output directory for generated data
RUN mkdir -p /app/output

# Set the output directory as a volume
VOLUME ["/app/output"]

# Make the script executable
RUN chmod +x /app/execute_benchmark.py

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command - can be overridden
ENTRYPOINT ["python3", "execute_benchmark.py"]
CMD ["--scale-factor", "100"]
