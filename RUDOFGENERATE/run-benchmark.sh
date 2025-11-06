#!/bin/bash

# Run the RUDOF Generate benchmark using Docker
echo "Running RUDOF Generate benchmark..."
echo "=================================="

# Run the container
docker compose up

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Benchmark completed successfully!"
    echo ""
    echo "Results:"
    echo "  - Generated data: output/generated_data.ttl"
    echo "  - Benchmark report: output/benchmark_report.json"
    echo ""
    
    # Display the benchmark report if it exists
    if [ -f "output/benchmark_report.json" ]; then
        echo "Benchmark Summary:"
        cat output/benchmark_report.json | python3 -m json.tool 2>/dev/null || cat output/benchmark_report.json
    fi
else
    echo ""
    echo "✗ Benchmark failed!"
    exit 1
fi
