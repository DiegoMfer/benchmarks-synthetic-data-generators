#!/bin/bash
# Build the Docker image for RDFGraphGen benchmark

echo "Building RDFGraphGen Docker image..."
docker build -t rdfgraphgen-benchmark .

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Docker image built successfully!"
    echo ""
    echo "To run the benchmark:"
    echo "  ./run-benchmark.sh"
    echo ""
    echo "Or directly with docker:"
    echo "  docker run --rm -v \$(pwd)/output:/app/output rdfgraphgen-benchmark"
else
    echo ""
    echo "❌ Docker build failed!"
    exit 1
fi
