#!/bin/bash
# Part 2 — FHIR use case pipeline:
#   generate both FHIR datasets, then compare them.
# (For the RDF benchmark, see run_benchmark.sh.)

echo "Generating FHIR datasets at comparable scale..."
echo "Generators: RUDOFGENERATE (ShEx-driven, tuned + large config), SYNTHEA (clinical)"

# Start fresh
rm -rf 2-fhir

echo "----------------------------------------------------------------"
echo "Generating Synthea -> 2-fhir/"
echo "----------------------------------------------------------------"
python3 generate_all_fhir_datasets.py --generators SYNTHEA

echo "----------------------------------------------------------------"
echo "Generating rudof (tuned schema, Synthea-comparable scale) -> 2-fhir/"
echo "----------------------------------------------------------------"
python3 generate_all_fhir_datasets.py --generators RUDOFGENERATE \
    --schema fhir_usecase/fhir_r4_tuned.shex \
    --config fhir_usecase/fhir_config_tuned_large.toml

echo "----------------------------------------------------------------"
echo "Comparing datasets -> output_charts/fhir_scale_comparison.pdf"
echo "----------------------------------------------------------------"
python3 fhir_scale_comparison.py

echo "Done."
