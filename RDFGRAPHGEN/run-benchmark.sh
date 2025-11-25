#!/bin/bash
# Quick run script for RDFGraphGen Benchmark (Docker)

# Default parameters
SCALE_FACTOR=${1:-100}

echo "Running RDFGraphGen Benchmark"
echo "Scale Factor: $SCALE_FACTOR"
echo "================================"
echo ""

docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  rdfgraphgen-benchmark \
  --scale-factor $SCALE_FACTOR

echo ""
echo "✅ Benchmark complete!"
echo "📁 Output saved to: ./output/"
echo "📊 Report: ./output/benchmark_report.json"
echo ""
echo "View report:"
echo "  cat output/benchmark_report.json | python3 -m json.tool"
