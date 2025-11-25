#!/bin/bash
# Build the Docker image for RDFMutate benchmark

echo "Building RDFMutate Docker image..."
docker build -t rdfmutate-benchmark .

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Docker image built successfully!"
    echo ""
    echo "To run the benchmark:"
    echo "  ./run-benchmark.sh"
    echo ""
    echo "Or directly with docker:"
    echo "  docker run --rm -v \$(pwd)/output:/app/output rdfmutate-benchmark"
else
    echo ""
    echo "❌ Docker build failed!"
    exit 1
fi
