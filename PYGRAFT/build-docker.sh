#!/bin/bash
# Build PyGraft Docker image

echo "=========================================="
echo "Building PyGraft Docker Image"
echo "=========================================="

docker build -t pygraft-benchmark:latest .

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Docker image built successfully!"
    echo ""
    echo "To run the benchmark:"
    echo "  docker-compose up"
    echo ""
    echo "Or run with custom parameters:"
    echo "  docker run -v \$(pwd)/output:/app/output pygraft-benchmark:latest \\"
    echo "    python execute_benchmark.py --n-classes 100 --avg-instances 100"
else
    echo ""
    echo "❌ Docker build failed!"
    exit 1
fi
