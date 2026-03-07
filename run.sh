#!/bin/bash
# Script to generate ALL datasets including LUBM with extracted shapes

echo "Starting generation of ALL datasets..."
echo "Generators: BSBM, LUBM, GAIA, LINKGEN, PYGRAFT, RDFGRAPHGEN, RUDOFGENERATE, and LUBM Variants"

# Remove existing 1-Datasets folder to start fresh
rm -rf 1-Datasets


echo "----------------------------------------------------------------"
echo "Starting generation"
echo "----------------------------------------------------------------"
python3 generate_all_datasets.py --generators ALL


echo "----------------------------------------------------------------"
echo "Starting measurements, this will take hours..."
echo "----------------------------------------------------------------"


echo "Generating CSV metrics..."
python3 generate_csv_metrics.py

echo "Generation complete."
