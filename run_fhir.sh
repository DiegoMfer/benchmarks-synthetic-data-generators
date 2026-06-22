#!/bin/bash
# Part 2 — FHIR use case pipeline:
#   generate both FHIR datasets, then run the quality comparisons.
# (For the RDF benchmark, see run_benchmark.sh.)

echo "Generating ALL FHIR datasets..."
echo "Generators: RUDOFGENERATE (ShEx-driven), SYNTHEA (clinical)"

# Start fresh
rm -rf 2-fhir

echo "----------------------------------------------------------------"
echo "Generating datasets -> 2-fhir/"
echo "----------------------------------------------------------------"
python3 generate_all_fhir_datasets.py --generators ALL

echo "----------------------------------------------------------------"
echo "Comparing data quality -> output_charts/fhir_quality_comparison.pdf"
echo "----------------------------------------------------------------"
python3 compare_fhir_quality.py

echo "Done."
