#!/bin/bash
# Build script for GAIA Docker container

echo "🐳 Building GAIA Benchmark Docker container..."
echo "================================================"

# Build the Docker image
docker build -t gaia-benchmark .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully!"
    echo ""
    echo "Usage:"
    echo "  docker run --rm -v \$(pwd)/output:/app/output gaia-benchmark --instances 5"
    echo "  docker-compose up"
    echo ""
else
    echo "❌ Docker build failed!"
    exit 1
fi
