# RDFGraphGen Benchmark - Docker Setup

## LINK to the tool
https://github.com/cadmiumkitty/rdfgraphgen
- PyPI: https://pypi.org/project/rdf-graph-gen/

## What is RDFGraphGen?

**RDFGraphGen** is a Python-based tool that generates synthetic RDF data from SHACL shape definitions. It allows you to:
- Define data structures using SHACL shapes
- Generate realistic RDF graphs at scale
- Control graph size with a scale factor parameter
- Create test datasets for RDF applications

## Quick Start

### 1. Build the Docker Image

```bash
./build-docker.sh
```

Or manually:
```bash
docker build -t rdfgraphgen-benchmark .
```

### 2. Run the Benchmark

**Easy way** (using the run script):
```bash
# Generate with default scale factor (100)
./run-benchmark.sh

# Generate with custom scale factor
./run-benchmark.sh 500
./run-benchmark.sh 1000
```

**Docker way**:
```bash
# Run with default scale factor
docker run --rm -v $(pwd)/output:/app/output rdfgraphgen-benchmark

# Run with custom scale factor
docker run --rm -v $(pwd)/output:/app/output rdfgraphgen-benchmark --scale-factor 500
```

**Docker Compose way**:
```bash
docker-compose run --rm rdfgraphgen-benchmark
docker-compose run --rm rdfgraphgen-benchmark --scale-factor 1000
```

**Native Python way** (requires Python 3.7+):
```bash
# Install first
pip install rdf-graph-gen

# Run with default scale factor
python3 execute_benchmark.py

# Run with custom scale factor
python3 execute_benchmark.py --scale-factor 500

# Full control
python3 execute_benchmark.py \
  --shape input-shape.ttl \
  --output my-output.ttl \
  --scale-factor 1000
```

## Output

All generated files are saved to the `./output` directory:
- `output-graph.ttl` (or custom filename) - Generated RDF graph
- `benchmark_report.json` - Detailed metrics and performance data

## Configuration

### Scale Factor (`-s`, `--scale-factor`)
Controls the size of the generated RDF graph:
- **10** - Tiny (quick test)
- **100** - Small (default)
- **500** - Medium
- **1,000** - Large
- **5,000** - Very Large
- **10,000+** - Extra Large

The scale factor determines how many instances are generated based on the SHACL shape definitions.

### Shape File (`--shape`)
SHACL shape file defining the RDF data structure:
- Default: `input-shape.ttl`
- Must be in Turtle format
- Defines classes, properties, and constraints

### Output File (`--output`)
Output RDF graph filename:
- Default: `output-graph.ttl`
- Saved to `./output` directory
- In Turtle format

## Examples

### Example 1: Quick Test
```bash
# Small graph for testing
./run-benchmark.sh 10
```

### Example 2: Medium Dataset
```bash
# Medium-sized graph
./run-benchmark.sh 500
```

### Example 3: Large Production Dataset
```bash
# Large graph (may take several minutes)
docker run --rm -v $(pwd)/output:/app/output rdfgraphgen-benchmark --scale-factor 5000
```

### Example 4: Custom Shape and Output
```bash
python3 execute_benchmark.py \
  --shape my-custom-shape.ttl \
  --output my-dataset.ttl \
  --scale-factor 1000
```

## Custom SHACL Shapes

Create your own shape file to define custom data structures:

```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.org/> .

ex:PersonShape
    a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property [
        sh:path ex:name ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
    ] ;
    sh:property [
        sh:path ex:age ;
        sh:datatype xsd:integer ;
        sh:minCount 1 ;
    ] .
```

Then run:
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/my-shape.ttl:/app/my-shape.ttl \
  rdfgraphgen-benchmark \
  --shape my-shape.ttl \
  --scale-factor 1000
```

## Performance Notes

- **Scale Factor Impact**: Execution time grows roughly linearly with scale factor
- **Memory Usage**: Larger graphs require more memory
- **Docker Overhead**: First run may be slower due to container startup
- **Output Size**: Generated file size depends on shape complexity and scale factor

## Requirements

### Native Execution
- Python 3.7 or higher
- `rdf-graph-gen` package (installed via pip)

### Docker Execution
- Docker (any recent version)
- Docker Compose (optional)

## Troubleshooting

### Shape File Not Found
Ensure your shape file exists and is in the correct location:
```bash
ls -la input-shape.ttl
```

### Permission Errors (Docker)
The run script uses your user ID:
```bash
docker run --rm -v $(pwd)/output:/app/output -u $(id -u):$(id -g) rdfgraphgen-benchmark
```

### Out of Memory
For very large graphs, increase Docker memory limit:
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  --memory=4g \
  rdfgraphgen-benchmark \
  --scale-factor 10000
```

## Learn More

- **GitHub Repository**: https://github.com/cadmiumkitty/rdfgraphgen
- **PyPI Package**: https://pypi.org/project/rdf-graph-gen/
- **SHACL Specification**: https://www.w3.org/TR/shacl/
