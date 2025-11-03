# GAIA Generator with LUBM Ontology

This directory contains the GAIA (Generator for Automatic Instanciation) benchmark setup configured to work with the LUBM (Lehigh University Benchmark) ontology.

## Overview

GAIA is an ontology instance generator that can create synthetic data based on OWL ontologies. This setup uses the LUBM ontology as input to generate university domain instances.

## Files

- `OWLGenerator.jar` - The GAIA generator executable
- `lib/` - Required Java libraries for GAIA
- `execute_benchmark.py` - Python script to run GAIA with LUBM ontology
- `run-benchmark.sh` - Shell script for easy execution
- `Dockerfile` - Docker container configuration
- `docker-compose.yml` - Docker Compose configuration
- `build-docker.sh` - Docker build script
- `output/` - Directory for generated files

## Quick Start

### Method 1: Direct Execution

```bash
# Run with default settings (3 instances per class)
python3 execute_benchmark.py

# Run with custom parameters
python3 execute_benchmark.py --instances 5 --limit 10 --materialization

# Using the shell script
./run-benchmark.sh 5          # 5 instances per class
./run-benchmark.sh 3 10       # 3-10 instances per class
./run-benchmark.sh 5 15 true  # 5-15 instances with materialization
```

### Method 2: Docker

```bash
# Build the Docker image
./build-docker.sh

# Run with Docker
docker run --rm -v $(pwd)/output:/app/output gaia-benchmark --instances 5

# Or use Docker Compose
docker-compose up
```

## Parameters

- `--instances, -n`: Number of instances per class (default: 3)
- `--limit, -l`: Maximum number of instances per class (optional)
- `--materialization, -m`: Enable materialization (adds superclass references)
- `--threads, -t`: Number of threads to use (optional)
- `--output, -o`: Output file path (default: output/gaia_instances.owl)

## Requirements

- Java 11 or higher
- Python 3
- Internet connection (to download LUBM ontology on first run)

## LUBM Ontology

The script automatically downloads the LUBM ontology from:
http://swat.cse.lehigh.edu/onto/univ-bench.owl

This ontology defines university domain concepts like:
- Universities, Departments, Courses
- Students, Faculty, Staff
- Publications, Research Areas
- Administrative structures

## Output

The generator creates:
- `output/gaia_instances.owl` - Generated OWL instances
- `output/benchmark_report.json` - Detailed benchmark report with statistics

## Example Output Report

```json
{
  "benchmark_name": "GAIA",
  "generator_version": "3.1",
  "ontology": "LUBM",
  "results": {
    "execution_time_seconds": 12.5,
    "instances_generated": 450,
    "classes_processed": 15,
    "output_size_mb": 2.3
  }
}
```

## Docker Setup Documentation

For detailed Docker setup instructions, see `DOCKER_SETUP.md`.

## Troubleshooting

1. **Java OutOfMemoryError**: Increase heap size in the Python script (modify `-Xmx8g`)
2. **Connection errors**: Check internet connection for LUBM ontology download
3. **Permission errors**: Ensure scripts are executable (`chmod +x *.sh`)

## About GAIA

GAIA v3.1 is developed for automatic instance generation from OWL ontologies. It supports:
- Multiple instance generation strategies
- Materialization options
- Multi-threaded execution
- Various output formats
