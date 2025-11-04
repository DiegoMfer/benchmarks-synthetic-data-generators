# LINKGEN - Linked Data Generator Benchmark

Multi-purpose Synthetic Linked Data Generator that can generate large amounts of RDF data based on ontologies with statistical distributions.

## Overview

LINKGEN generates synthetic RDF data based on OWL ontologies using configurable statistical distributions (Zipfian or Gaussian). It supports:
- Multiple ontologies (DBpedia, Schema.org, or custom)
- Statistical distributions (Zipf, Gaussian)
- Noise and inconsistent data generation
- Entity linking (sameAs)
- Multi-threaded generation
- N-Triples and N-Quads output formats

## Citation

If you use this tool, please cite:
- Joshi, A.K., Hitzler, P., Dong, G.: Multi-purpose Synthetic Linked Data Generator
- https://github.com/akjoshi/linkgen/
- Web Id: http://w3id.org/linkgen

## Quick Start

### Using Docker (Recommended)

1. **Build the Docker image:**
   ```bash
   chmod +x build-docker.sh
   ./build-docker.sh
   ```

2. **Run with default parameters (100K triples, DBpedia ontology):**
   ```bash
   chmod +x run-benchmark.sh
   ./run-benchmark.sh
   ```

3. **Run with custom parameters:**
   ```bash
   # Generate 200K triples with Schema.org ontology
   ./run-benchmark.sh 200000 schemaorg.owl zipf
   ```

4. **Using docker-compose:**
   ```bash
   docker-compose up
   ```

### Using Python Directly

1. **Ensure Java 17+ and Python 3.11+ are installed**

2. **Run the benchmark:**
   ```bash
   python3 execute_benchmark.py --triples 100000 --ontology dbpedia_2015.owl
   ```

## Configuration Options

### Core Parameters

- `--triples` - Number of distinct triples to generate (default: 100000)
- `--ontology` - Ontology file: `dbpedia_2015.owl` or `schemaorg.owl` (default: dbpedia_2015.owl)
- `--distribution` - Statistical distribution: `zipf` or `gaussian` (default: zipf)
- `--threads` - Number of threads for parallel generation (default: 2)
- `--format` - Output format: `nt` (N-Triples) or `nq` (N-Quads) (default: nt)
- `--output-name` - Base name for output files (default: data)

### Distribution Parameters

**Zipf Distribution:**
- `--zipf-exponent` - Exponent value, typically 2.0-3.0 (default: 2.1)

**Gaussian Distribution:**
- `--gaussian-mean` - Mean value (default: 200)
- `--gaussian-deviation` - Standard deviation (default: 15)

### Advanced Parameters

- `--triples-per-file` - Triples per output file (default: 100000)
- `--max-file-size` - Maximum file size in bytes (default: 100000000)
- `--avg-frequency` - Average frequency of subjects (default: 5)
- `--num-strings` - Number of unique string values (default: 10)

### Noise Generation

- `--noise` - Enable noise data generation (default: True)
- `--noise-total` - Total noise instances (default: 10000)
- `--noise-notype` - Instances without type (default: 100)
- `--noise-invalid` - Invalid instances (default: 100)
- `--noise-duplicate` - Duplicate instances (default: 1000)

### Entity Linking

- `--sameas` - Generate sameAs links to real entities (default: False)

## Usage Examples

### Example 1: Basic Generation
```bash
python3 execute_benchmark.py --triples 100000
```

### Example 2: Large Dataset with Schema.org
```bash
python3 execute_benchmark.py \
  --triples 1000000 \
  --ontology schemaorg.owl \
  --threads 4
```

### Example 3: Gaussian Distribution
```bash
python3 execute_benchmark.py \
  --triples 500000 \
  --distribution gaussian \
  --gaussian-mean 150 \
  --gaussian-deviation 20
```

### Example 4: Custom Zipf Exponent
```bash
python3 execute_benchmark.py \
  --triples 200000 \
  --distribution zipf \
  --zipf-exponent 2.5
```

### Example 5: N-Quads Format with Entity Linking
```bash
python3 execute_benchmark.py \
  --triples 100000 \
  --format nq \
  --sameas True
```

### Example 6: With Noise Control
```bash
python3 execute_benchmark.py \
  --triples 100000 \
  --noise True \
  --noise-total 5000 \
  --noise-duplicate 500
```

## Output

The benchmark generates:

1. **Data Files**: `output/data_*.nt` (or `.nq` for N-Quads)
   - RDF data in N-Triples or N-Quads format
   - Split across multiple files based on configuration

2. **VoID Description**: `output/void.ttl`
   - Dataset statistics and metadata

3. **Benchmark Report**: `output/benchmark_report.json`
   ```json
   {
     "benchmark": "LINKGEN",
     "timestamp": "2025-11-04T10:30:00",
     "configuration": {
       "ontology": "dbpedia_2015.owl",
       "triples": 100000,
       "distribution": "zipf",
       "format": "nt"
     },
     "execution": {
       "time_seconds": 12.34,
       "time_formatted": "12.34s"
     },
     "generated_data": {
       "files_generated": 2,
       "total_size_mb": 15.67
     },
     "performance_metrics": {
       "triples_per_second": 8103.73
     }
   }
   ```

4. **Log File**: `output/linkgen.log`
   - Detailed execution logs

## Docker Setup Details

See [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed Docker configuration and troubleshooting.

## Requirements

### Native Execution
- Java 17 or higher
- Python 3.11 or higher
- 4GB+ RAM (8GB recommended for large datasets)

### Docker Execution
- Docker 20.10+
- Docker Compose 1.29+ (optional)

## Troubleshooting

### Out of Memory Error
Increase Java heap size in Dockerfile or when running directly:
```bash
export JAVA_OPTS="-Xmx8G"
python3 execute_benchmark.py --triples 1000000
```

### Ontology File Not Found
Ensure ontology files are present:
```bash
ls -la *.owl
```

### Permission Errors (Docker)
Run with correct user permissions:
```bash
docker run --rm -u $(id -u):$(id -g) -v $(pwd)/output:/app/output linkgen-benchmark
```

## Performance Tips

1. **Increase threads** for faster generation on multi-core systems
2. **Adjust triples-per-file** for optimal file sizes
3. **Use Zipf distribution** for more realistic data patterns
4. **Disable noise** for faster generation if not needed

## License

GNU General Public License, version 3 (GPL-3.0)

## Original Repository

- GitHub: https://github.com/akjoshi/linkgen/
- Author: Amit Joshi, Data Semantics Lab, Wright State University
