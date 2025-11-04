#!/bin/bash
# Quick run script for LINKGEN Benchmark (Docker)

# Default parameters
TRIPLES=${1:-100000}
ONTOLOGY=${2:-dbpedia_2015.owl}
DISTRIBUTION=${3:-zipf}

echo "Running LINKGEN Benchmark Generator"
echo "Triples: $TRIPLES"
echo "Ontology: $ONTOLOGY"
echo "Distribution: $DISTRIBUTION"
echo "================================"
echo ""

docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  linkgen-benchmark \
  --triples $TRIPLES \
  --ontology $ONTOLOGY \
  --distribution $DISTRIBUTION

echo ""
echo "✅ Benchmark complete!"
echo "📁 Output saved to: ./output/"
echo "📊 Report: ./output/benchmark_report.json"
echo ""
echo "View report:"
echo "  cat output/benchmark_report.json | python3 -m json.tool"
