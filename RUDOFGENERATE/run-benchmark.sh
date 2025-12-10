#!/bin/bash

# Run the RUDOF Generate Binary benchmark using Docker
echo "Running RUDOF Generate Binary benchmark..."
echo "======================================="

# Check if a config file was provided as an argument
CONFIG_FILE=${1:-benchmark_config.toml}
echo "Using configuration file: $CONFIG_FILE"

# Run the container with the specified config file
CONFIG_FILE=$CONFIG_FILE docker compose up

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
