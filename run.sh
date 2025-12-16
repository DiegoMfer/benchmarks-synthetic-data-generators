#!/bin/bash
# Script to generate ALL datasets including LUBM with extracted shapes

echo "Starting generation of ALL datasets..."
echo "Generators: BSBM, LUBM, GAIA, LINKGEN, PYGRAFT, RDFGRAPHGEN, RUDOFGENERATE, and LUBM Variants"

python3 generate_all_datasets.py --generators ALL

echo "Generation complete."
