# Use OpenJDK base image with Python
FROM python:3.11-slim

# Install Java
RUN apt-get update && \
    apt-get install -y openjdk-17-jre-headless && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the LUBM generator files
COPY lubm-generator-fixed.jar /app/
COPY execute_benchmark.py /app/

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
CMD ["--universities", "1"]
