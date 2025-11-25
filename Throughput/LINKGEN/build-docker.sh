#!/bin/bash
# Build script for LINKGEN Docker image

echo "Building LINKGEN Benchmark Docker image..."
echo "=========================================="

docker build -t linkgen-benchmark .

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Docker image built successfully!"
    echo "📦 Image name: linkgen-benchmark"
    echo ""
    echo "Run with:"
    echo "  ./run-benchmark.sh [TRIPLES] [ONTOLOGY] [DISTRIBUTION]"
    echo ""
    echo "Or use docker-compose:"
    echo "  docker-compose up"
else
    echo ""
    echo "❌ Docker build failed!"
    exit 1
fi
