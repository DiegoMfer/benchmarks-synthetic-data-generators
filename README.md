# RDF Synthetic Data Generators Benchmark

A comprehensive benchmark suite for evaluating 10 different RDF synthetic data generators with Docker containerization.

**Author:** DiegoMfer (diegomartin.research@gmail.com)

## 🚀 Quick Start

### Generate All Datasets

```bash
python3 generate_all_datasets.py
```

This will generate datasets from all 10 generators and save them in the `1-Datasets/` folder with complete metadata. All generators run in Docker containers for consistency and reproducibility.

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

## 📊 Available Generators (10 Total)

| Generator | Status | Type | Description |
|-----------|--------|------|-------------|
| **BSBM** | ✅ Working | Docker | E-commerce benchmark with products, vendors, offers, and reviews |
| **LUBM** | ✅ Working | Docker | University domain with departments, professors, students, and courses |
| **GAIA** | ✅ Working | Docker | Ontology instance generator using LUBM ontology |
| **LINKGEN** | ✅ Working | Docker | Flexible linked data generator with configurable distributions (Zipf/Gaussian) |
| **PyGraft** | ✅ Working | Docker | Knowledge graph generator with RDFS/OWL constructs |
| **RDFGraphGen** | ✅ Working | Docker | SHACL-based synthetic data generator |
| **RDFGraphGen-LUBM** | ✅ Working | Docker | RDFGraphGen variant with LUBM SHACL shapes |
| **RUDOF Generate** | ✅ Working | Docker | ShEx-based RDF generator (Binary v0.1.142) |
| **RUDOF Generate-LUBM-ShEx** | ✅ Working | Docker | RUDOF variant with LUBM ShEx schema |
| **RUDOF Generate-LUBM-SHACL** | ✅ Working | Docker | RUDOF variant with LUBM SHACL shapes |

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
- Docker & Docker Compose (all generators run containerized)
- Linux/macOS/WSL (Docker host environment)

**Note:** All generators are containerized, so you don't need to install Java or other dependencies locally. Docker Compose handles all dependencies.

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

Each generator can also be run independently via its Docker Compose setup:

```bash
# BSBM
cd BSBM && docker compose run --rm bsbm-benchmark --products 10000 --format ttl

# LUBM
cd LUBM && docker compose run --rm lubm-benchmark --universities 10

# RUDOF Generate
cd RUDOFGENERATE && docker compose run --rm rudof --entity-count 100000
```

## 🐳 Docker Containerization

All 10 generators now run in Docker containers for consistent, reproducible results across environments:

- **Base Images**: eclipse-temurin:21-jre-jammy (Java), debian:bookworm-slim (system packages), python:3.11-slim (Python tools)
- **Volume Mounting**: Generated datasets are saved to the host's `output/` directory
- **Isolation**: Each generator runs in its own containerized environment with all dependencies pre-installed

## 📝 Recent Improvements

- ✅ All 10 generators converted to Docker Compose
- ✅ Fixed permission issues with containerized execution
- ✅ Automated dataset copying to `1-Datasets/` with metadata tracking
- ✅ Added support for SHACL and ShEx schema variants
- ✅ Improved performance metrics collection across all generators