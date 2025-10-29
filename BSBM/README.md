# BSBM Benchmark - Docker Setup

## LINK to the tool
http://wbsg.informatik.uni-mannheim.de/bizer/berlinsparqlbenchmark/ 
https://sourceforge.net/projects/bsbmtools/ 

## What is BSBM?

The **Berlin SPARQL Benchmark (BSBM)** is a benchmark for evaluating the performance of RDF storage systems. It generates synthetic e-commerce data with products, producers, vendors, offers, reviews, and ratings.

## Quick Start

### 1. Build the Docker Image

```bash
./build-docker.sh
```

Or manually:
```bash
docker build -t bsbm-benchmark .
```

### 2. Run the Benchmark

**Easy way** (using the run script):
```bash
# Generate 1,000 products (default)
./run-benchmark.sh

# Generate 10,000 products
./run-benchmark.sh 10000

# Generate 100,000 products in N-Triples format
./run-benchmark.sh 100000 nt
```

**Docker way**:
```bash
# Generate 1,000 products in Turtle format
docker run --rm -v $(pwd)/output:/app/output bsbm-benchmark

# Generate 50,000 products
docker run --rm -v $(pwd)/output:/app/output bsbm-benchmark --products 50000

# Generate 100,000 products in N-Triples format without forward chaining
docker run --rm -v $(pwd)/output:/app/output bsbm-benchmark --products 100000 --format nt --no-fc
```

**Docker Compose way**:
```bash
docker-compose run --rm bsbm-benchmark
docker-compose run --rm bsbm-benchmark --products 10000
```

## Output

All generated files are saved to the `./output` directory:
- `dataset.ttl` (or `.nt`, `.n3`, `.trig` depending on format)
- `benchmark_report.json` - Detailed metrics

## Configuration Options

### Products (`-p`, `--products`)
Controls the size of the generated dataset:
- **1,000** - Small (quick test, ~35K triples)
- **10,000** - Medium (~350K triples)
- **100,000** - Large (~3.5M triples, ~3GB file)
- **1,000,000** - Extra Large (~35M triples, ~30GB file)

### Format (`-f`, `--format`)
Output serialization format:
- `ttl` - Turtle (default, human-readable)
- `nt` - N-Triples (simple line-based)
- `n3` - Notation3
- `trig` - TriG (named graphs)

### Forward Chaining (`--no-fc`)
- By default, forward chaining (reasoning) is enabled
- Use `--no-fc` to disable it

## Examples

```bash
# Small dataset for testing
./run-benchmark.sh 1000

# Production-sized dataset
./run-benchmark.sh 100000

# Large dataset in N-Triples format
./run-benchmark.sh 500000 nt

# Custom run with all options
docker run --rm -v $(pwd)/output:/app/output bsbm-benchmark \
  --products 50000 \
  --format ttl \
  --output my-dataset \
  --output-dir output
```

## What Gets Generated

For 100,000 products, you get:
- **~35 million triples**
- **100,000 products** with descriptions, features, and properties
- **~2,000 producers** (manufacturers)
- **~1,000 vendors** (retailers)
- **~2 million offers** (products sold by vendors)
- **~100 rating sites** with ~50,000 reviewers
- **~1 million reviews** with ratings and comments
- **~2,000 product types** in a hierarchy
- **~50,000 product features**

## Benchmark Report

The `benchmark_report.json` contains:
- Execution time
- Number of triples generated
- Triples per second (performance metric)
- Detailed entity counts (products, vendors, reviews, etc.)

View it nicely:
```bash
cat output/benchmark_report.json | python3 -m json.tool
```

## File Structure

```
BSBM/
├── output/                    # Generated files (created automatically)
│   ├── dataset.ttl           # Generated RDF data
│   └── benchmark_report.json # Metrics
├── bsbm.jar                  # BSBM generator
├── ssj.jar                   # Stochastic simulation library
├── givennames.txt            # Names for generating data
├── titlewords.txt            # Words for product titles
├── execute_benchmark.py      # Python wrapper script
├── Dockerfile                # Docker image definition
├── docker-compose.yml        # Docker Compose config
├── build-docker.sh           # Build script
└── run-benchmark.sh          # Quick run script
```

## Requirements

- **Docker** (recommended)
- OR **Java 17+** and **Python 3.11+** for local execution

## Local Execution (without Docker)

```bash
python3 execute_benchmark.py --products 10000 --format ttl
```

## Performance Notes

- 1,000 products: ~1-2 seconds
- 10,000 products: ~5-10 seconds  
- 100,000 products: ~30-60 seconds
- 1,000,000 products: ~5-10 minutes

Performance varies based on CPU, memory, and disk speed.
