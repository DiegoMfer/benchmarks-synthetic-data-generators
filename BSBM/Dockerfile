# Use official Java image
FROM eclipse-temurin:21-jre-jammy

# Install Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip && \
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

# Create fresh td_data directory and initialize with world-writable permissions
RUN mkdir -p /app/td_data && \
    touch /app/td_data/.init && \
    chmod -R 777 /app/td_data && \
    rm /app/td_data/.init

# Create output directory for generated data
RUN mkdir -p /app/output && chmod 777 /app/output && chmod 777 /app

# Set the output directory as a volume
VOLUME ["/app/output"]

# Make the script executable
RUN chmod +x /app/execute_benchmark.py

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV JAVA_OPTS="-Xmx2G"

# Default command - can be overridden
# Use a wrapper script approach to properly pass arguments
ENTRYPOINT ["sh", "-c", "umask 0000 && exec python3 /app/execute_benchmark.py \"$@\"", "--"]
CMD ["--products", "1000"]
