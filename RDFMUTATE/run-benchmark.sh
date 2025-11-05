#!/bin/bash
# Quick run script for RDFMutate Benchmark (Docker)

# Default parameters
CONFIG=${1:-config.yaml}

echo "Running RDFMutate Benchmark Generator"
echo "Config: $CONFIG"
echo "================================"
echo ""

docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  rdfmutate-benchmark \
  --config $CONFIG

echo ""
echo "✅ Benchmark complete!"
echo "📁 Output saved to: ./output/"
echo "📊 Report: ./output/benchmark_report.json"
echo ""
echo "View report:"
echo "  cat output/benchmark_report.json | python3 -m json.tool"
