FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Download and install RUDOF binary v0.1.142
RUN curl -L -o rudof https://github.com/rudof-project/rudof/releases/download/v0.1.142/rudof_v0.1.142_x86_64_linux_gnu && \
    chmod +x rudof && \
    mv rudof /usr/local/bin/

# Copy benchmark scripts and schema files
COPY execute_benchmark_binary.py .
COPY example_schema.shex .

# Create output directory as a volume mount point
VOLUME ["/app/output"]

# Set the entrypoint to run the binary-based benchmark script
ENTRYPOINT ["python3", "execute_benchmark_binary.py"]
