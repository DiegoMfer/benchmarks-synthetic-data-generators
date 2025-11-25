# Use OpenJDK base image with Python
FROM python:3.11-slim

# Install Java
RUN apt-get update && \
    apt-get install -y openjdk-21-jre-headless && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the BSBM generator files
COPY bsbm.jar /app/
COPY ssj.jar /app/
COPY givennames.txt /app/
COPY titlewords.txt /app/
COPY execute_benchmark.py /app/

# Create output directory for generated data
RUN mkdir -p /app/output

# Set the output directory as a volume
VOLUME ["/app/output"]

# Make the script executable
RUN chmod +x /app/execute_benchmark.py

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV JAVA_OPTS="-Xmx2G"

# Default command - can be overridden
ENTRYPOINT ["python3", "execute_benchmark.py"]
CMD ["--products", "1000"]
