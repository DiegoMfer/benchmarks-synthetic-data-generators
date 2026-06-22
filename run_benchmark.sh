#!/bin/bash
# Part 1 — RDF benchmark pipeline:
#   generate every benchmark dataset, then compute the comparison metrics.
# (For the FHIR use case, see run_fhir.sh.)

echo "Generating ALL benchmark datasets..."
echo "Generators: BSBM, LUBM, GAIA, LINKGEN, PYGRAFT, RDFGRAPHGEN, RUDOFGENERATE, and LUBM variants"

# Start fresh
rm -rf 1-Datasets

echo "----------------------------------------------------------------"
echo "Generating datasets -> 1-Datasets/"
echo "----------------------------------------------------------------"
python3 generate_all_benchmark_datasets.py --generators ALL

echo "----------------------------------------------------------------"
echo "Computing metrics -> metrics_comparison.csv (this can take hours)"
echo "----------------------------------------------------------------"
python3 generate_csv_metrics.py

echo "Done. Open metrics_histogram.ipynb to plot the results."
