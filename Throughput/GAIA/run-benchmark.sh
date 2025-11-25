#!/bin/bash
# Quick run script for GAIA Benchmark with LUBM Ontology

# Default parameters
INSTANCES=${1:-3}
LIMIT=${2:-""}
MATERIALIZATION=${3:-""}

echo "Running GAIA Benchmark Generator with LUBM Ontology"
echo "Instances per class: $INSTANCES"
if [ ! -z "$LIMIT" ]; then
    echo "Instance limit per class: $LIMIT"
fi
if [ "$MATERIALIZATION" == "true" ]; then
    echo "Materialization: Enabled"
fi
echo "================================"
echo ""

# Build command arguments
ARGS="--instances $INSTANCES"
if [ ! -z "$LIMIT" ]; then
    ARGS="$ARGS --limit $LIMIT"
fi
if [ "$MATERIALIZATION" == "true" ]; then
    ARGS="$ARGS --materialization"
fi

# Run the Python script
python3 execute_benchmark.py $ARGS

echo ""
echo "✅ Benchmark complete!"
echo "📁 Output saved to: ./output/"
echo "📊 Report: ./output/benchmark_report.json"
echo "💾 Generated instances: ./output/gaia_instances.owl"
echo ""
echo "View report:"
echo "  cat output/benchmark_report.json | python3 -m json.tool"
echo ""
echo "Usage examples:"
echo "  ./run-benchmark.sh 5                    # Generate 5 instances per class"
echo "  ./run-benchmark.sh 3 10                 # Generate 3-10 instances per class"
echo "  ./run-benchmark.sh 5 15 true           # Generate 5-15 instances with materialization"
