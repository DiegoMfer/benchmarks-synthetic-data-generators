#!/bin/bash
set -euo pipefail

ROOT_DIR="/home/benchmark/Documents/benchmarks-synthetic-data-generators"
cd "$ROOT_DIR"

echo "Starting RUDOF-only regeneration..."
echo "Removing previous RUDOF datasets from 1-Datasets/..."
rm -rf 1-Datasets/RUDOFGENERATE_LUBM_SHEX_HIGH_COHERENCE \
       1-Datasets/RUDOFGENERATE_LUBM_SHEX_LOW_COHERENCE \
       1-Datasets/RUDOFGENERATE_LUBM_SHACL_HIGH_COHERENCE \
       1-Datasets/RUDOFGENERATE_LUBM_SHACL_LOW_COHERENCE

echo "Running RUDOF generators..."
python3 generate_all_datasets.py --generators \
  RUDOFGENERATE_LUBM_SHEX_HIGH_COHERENCE \
  RUDOFGENERATE_LUBM_SHEX_LOW_COHERENCE \
  RUDOFGENERATE_LUBM_SHACL_HIGH_COHERENCE \
  RUDOFGENERATE_LUBM_SHACL_LOW_COHERENCE

echo "Generating metrics..."
python3 generate_csv_metrics.py

echo "RUDOF regeneration and metrics complete."
