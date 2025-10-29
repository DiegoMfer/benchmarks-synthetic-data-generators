#!/bin/bash
# Quick run script for LUBM Benchmark (Docker)

# Default number of universities
UNIVERSITIES=${1:-1}

echo "Running LUBM Benchmark Generator"
echo "Universities: $UNIVERSITIES"
echo "================================"
echo ""

docker run --rm \
  -v $(pwd)/output:/app/output \
  lubm-benchmark \
  --universities $UNIVERSITIES

echo ""
echo "✅ Benchmark complete!"
echo "📁 Output saved to: ./output/"
echo "📊 Report: ./output/benchmark_report.json"
echo ""
echo "View report:"
echo "  cat output/benchmark_report.json | python3 -m json.tool"
