# Configuration Summary - RDF Synthetic Data Generators

## Overview
This folder contains comprehensive configuration documentation for all 8 RDF synthetic data generators evaluated in the benchmarking suite. Each generator includes configurations for **HIGH COHERENCE** and **LOW COHERENCE** experiments.

## Coherence Definition
- **HIGH COHERENCE (~1)**: Highly structured data where instances have values for almost all properties (similar to relational databases like TPC-H)
- **LOW COHERENCE (~0)**: Sparse/unstructured data where properties vary significantly between instances (similar to LOD datasets like DBpedia)

## Generators Included

1. **BSBM** - Berlin SPARQL Benchmark (E-commerce data)
2. **LUBM** - Lehigh University Benchmark (University data)
3. **GAIA** - Ontology Instance Generator (LUBM-based)
4. **LINKGEN** - Flexible Linked Data Generator (LUBM-based)
5. **PYGRAFT** - Schema and Knowledge Graph Generator
6. **RDFGRAPHGEN** - SHACL-based Generator (LUBM-based)
7. **RUDOFGENERATE** - ShEx/SHACL High-Performance Generator
8. **RDFGRAPHGEN_LUBM** and **RUDOFGENERATE_LUBM** variants

## Files in This Folder

- **INDEX.md** - This file
- **01_BSBM_Configuration.txt** - BSBM generator configuration
- **02_LUBM_Configuration.txt** - LUBM generator configuration
- **03_GAIA_Configuration.txt** - GAIA generator configuration
- **04_LINKGEN_Configuration.txt** - LINKGEN generator configuration
- **05_PYGRAFT_Configuration.txt** - PYGRAFT generator configuration
- **06_RDFGRAPHGEN_Configuration.txt** - RDFGRAPHGEN generator configuration
- **07_RUDOFGENERATE_Configuration.txt** - RUDOFGENERATE generator configuration
- **SUMMARY_TABLE.txt** - Quick reference table of all configurations

## Usage

To use these configurations:

1. Navigate to the respective generator folder (e.g., `BSBM/`)
2. Run the `execute_benchmark.py` script with the parameters specified in the configuration files
3. Example: `python3 BSBM/execute_benchmark.py --products 50000 --format ttl`

## Key Configuration Parameters by Generator

### BSBM
- **HIGH**: products=50000
- **LOW**: products=10000

### LUBM
- **HIGH**: universities=10, seed=0
- **LOW**: universities=5, seed=42

### GAIA
- **HIGH**: instances=10000, materialization=True
- **LOW**: instances=10000, materialization=False

### LINKGEN
- **HIGH**: distribution=uniform, triples=6000
- **LOW**: distribution=zipf, triples=6000

### PYGRAFT
- **HIGH**: avg_instances=200, avg_relations=5, std_relations=1
- **LOW**: avg_instances=50, avg_relations=2, std_relations=2

### RDFGRAPHGEN
- **HIGH**: scale_factor=3000
- **LOW**: scale_factor=500

### RUDOFGENERATE
- **HIGH**: cardinality_strategy=Maximum, quality=High
- **LOW**: cardinality_strategy=Minimum, quality=Low

## All Generator Classes Used
All generators use the **LUBM (Lehigh University Benchmark) ontology** or LUBM-like structure for fair comparison:
- Source: `univ-bench.owl` from Lehigh University
- Ontology defines: Universities, Departments, Courses, Students, Faculty, Publications, Research Areas

## For More Information
- See `coherence_configurations.txt` in the root directory for detailed explanations
- See `generate_all_benchmark_datasets.py` for the Python configuration dictionary
- See individual generator READMEs in their respective folders

---
Generated: Configuration Summary Document
Last Updated: 2025-05-04
