#!/bin/bash
# Script to generate ALL datasets including LUBM with extracted shapes

echo "Starting generation of ALL datasets..."
echo "Generators: BSBM, LUBM, GAIA, LINKGEN, PYGRAFT, RDFGRAPHGEN, RUDOFGENERATE, and LUBM Variants"

# Run 4 times as requested

echo "----------------------------------------------------------------"
echo "Starting generation"
echo "----------------------------------------------------------------"
python3 generate_all_datasets.py --generators ALL

echo "Generating CSV metrics..."
python3 generate_csv_metrics.py

echo "Generation complete."
