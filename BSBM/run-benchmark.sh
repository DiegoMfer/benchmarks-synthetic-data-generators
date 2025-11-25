#!/bin/bash
# Quick run script for BSBM Benchmark (Docker)

# Default parameters
PRODUCTS=${1:-1000}
FORMAT=${2:-ttl}

echo "Running BSBM Benchmark Generator"
echo "Products: $PRODUCTS"
echo "Format: $FORMAT"
echo "================================"
echo ""

docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  bsbm-benchmark \
  --products $PRODUCTS \
  --format $FORMAT

echo ""
echo "✅ Benchmark complete!"
echo "📁 Output saved to: ./output/"
echo "📊 Report: ./output/benchmark_report.json"
echo ""
echo "View report:"
echo "  cat output/benchmark_report.json | python3 -m json.tool"
