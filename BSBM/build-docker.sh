#!/bin/bash
# Quick start script for BSBM Benchmark Generator

set -e

echo "BSBM Benchmark Generator - Docker Setup"
echo "========================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Build the Docker image
echo "Building Docker image..."
docker build -t bsbm-benchmark .

echo ""
echo "✅ Build complete!"
echo ""
echo "Usage examples:"
echo "  # Run with 1,000 products (default):"
echo "  ./run-benchmark.sh"
echo ""
echo "  # Run with 10,000 products:"
echo "  ./run-benchmark.sh 10000"
echo ""
echo "  # Run with 100,000 products in N-Triples format:"
echo "  ./run-benchmark.sh 100000 nt"
echo ""
echo "  # Or use docker directly:"
echo "  docker run --rm -v \$(pwd)/output:/app/output bsbm-benchmark --products 5000"
echo ""
echo "All generated files will be saved in the ./output directory"
