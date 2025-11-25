#!/bin/bash
# Quick script to run PyGraft benchmark locally

# Default parameters
MODE="full"
N_CLASSES=50
N_RELATIONS=30
AVG_INSTANCES=50

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --n-classes)
            N_CLASSES="$2"
            shift 2
            ;;
        --n-relations)
            N_RELATIONS="$2"
            shift 2
            ;;
        --avg-instances)
            AVG_INSTANCES="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            echo "Usage: $0 [--mode schema|kg|full] [--n-classes NUM] [--n-relations NUM] [--avg-instances NUM]"
            exit 1
            ;;
    esac
done

echo "=========================================="
echo "PyGraft Benchmark Runner"
echo "=========================================="
echo "Mode: $MODE"
echo "Classes: $N_CLASSES"
echo "Relations: $N_RELATIONS"
echo "Avg Instances: $AVG_INSTANCES"
echo "=========================================="

# Run the benchmark
python3 execute_benchmark.py \
    --mode "$MODE" \
    --n-classes "$N_CLASSES" \
    --n-relations "$N_RELATIONS" \
    --avg-instances "$AVG_INSTANCES"

echo ""
echo "Benchmark complete! Check output/ directory for results."
