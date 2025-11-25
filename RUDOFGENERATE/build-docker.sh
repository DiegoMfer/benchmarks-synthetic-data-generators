#!/bin/bash

# Build the Docker image for RUDOF Generate benchmark
echo "Building RUDOF Generate benchmark Docker image..."
docker compose build

if [ $? -eq 0 ]; then
    echo "✓ Docker image built successfully!"
    echo ""
    echo "To run the benchmark, use:"
    echo "  ./run-benchmark.sh"
else
    echo "✗ Docker build failed!"
    exit 1
fi
