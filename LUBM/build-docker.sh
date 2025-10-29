#!/bin/bash
# Quick start script for LUBM Benchmark Generator

set -e

echo "LUBM Benchmark Generator - Docker Setup"
echo "========================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Build the Docker image
echo "Building Docker image..."
docker build -t lubm-benchmark .

echo ""
echo "Build complete!"
echo ""
echo "Usage examples:"
echo "  # Run with 1 university (default):"
echo "  docker run --rm -v \$(pwd)/output:/app/output lubm-benchmark"
echo ""
echo "  # Run with 5 universities:"
echo "  docker run --rm -v \$(pwd)/output:/app/output lubm-benchmark --universities 5"
echo ""
echo "  # Run with custom seed:"
echo "  docker run --rm -v \$(pwd)/output:/app/output lubm-benchmark --universities 10 --seed 42"
echo ""
echo "All generated files will be saved in the ./output directory"
