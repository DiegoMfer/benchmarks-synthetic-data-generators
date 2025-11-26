# RDF Synthetic Data Generators Benchmark

A comprehensive benchmark suite for evaluating 8 different RDF synthetic data generators.

## 🚀 Quick Start

### Generate All Datasets

```bash
python3 generate_all_datasets.py
```

This will generate datasets from all 8 generators and save them in the `1-Datasets/` folder with complete metadata.

### Generate Specific Datasets

```bash
# Generate only BSBM and LUBM datasets
python3 generate_all_datasets.py --generators BSBM LUBM

# Generate only RUDOF Generate dataset
python3 generate_all_datasets.py --generators RUDOFGENERATE
```

### Custom Dataset Directory

```bash
python3 generate_all_datasets.py --dataset-dir my-custom-datasets
```

## 📊 Available Generators

| Generator | Status | Description |
|-----------|--------|-------------|
| **BSBM** | ✅ Done | E-commerce domain with products, vendors, offers, and reviews |
| **LUBM** | ✅ Done | University domain with departments, professors, students, and courses |
| **GAIA** | ✅ Done | Ontology instance generator using LUBM ontology for university domain data |
| **LINKGEN** | ✅ Done | Flexible synthetic linked data generator with configurable distributions (Zipf/Gaussian) |
| **PyGraft** | ✅ Done | Configurable schema and knowledge graph generator with RDFS/OWL constructs |
| **RDFMutate** | ✅ Done | Graph mutation-based synthetic data generator using SWRL/SHACL operators |
| **RDFGraphGen** | ✅ Done | SHACL-based synthetic data generator that generates RDF from shape definitions |
| **RUDOF Generate** | ✅ Done | High-performance RDF generator using ShEx schemas (Binary v0.1.142) |

## 📁 Dataset Structure

After running the generation script, datasets are organized as follows:

```
1-Datasets/
├── INDEX.md                    # Overview of all generated datasets
├── BSBM/
│   ├── metadata.json          # Configuration and generation metadata
│   ├── dataset.ttl            # Generated RDF data
│   └── benchmark_report.json  # Performance metrics
├── LUBM/
│   ├── metadata.json
│   ├── University0_*.owl      # Generated OWL files
│   └── benchmark_report.json
├── RUDOFGENERATE/
│   ├── metadata.json
│   ├── generated_data.ttl
│   ├── generated_data.stats.json
│   └── benchmark_report.json
└── ... (other generators)
```

## 🔧 Requirements

- Python 3.8+
- Docker (for PyGraft)
- Java 8+ (for BSBM, LUBM, GAIA, LINKGEN)
- RUDOF binary v0.1.142 (installed via Docker or system)

## 📈 Benchmark Comparison

Use the Jupyter notebook for comprehensive performance comparisons:

```bash
jupyter notebook benchmark_comparison.ipynb
```

The notebook provides:
- Execution time comparisons
- Triples/second performance metrics
- Output size analysis
- Interactive visualizations

## 🛠️ Individual Generator Usage

Each generator can also be run independently:

```bash
# BSBM
python3 BSBM/execute_benchmark.py --products 10000 --format ttl

# LUBM
python3 LUBM/execute_benchmark.py --universities 10 --seed 0

# RUDOF Generate (Binary)
python3 RUDOFGENERATE/execute_benchmark_binary.py --entity-count 100000 --seed 42
```

## 📚 Generators Not Included

- **PoDiGG**: Implementation issues
- **EvoGen**: Not yet integrated
- **GRR**: Not publicly available