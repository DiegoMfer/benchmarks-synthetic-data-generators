# RUDOF Generate Benchmark

This benchmark evaluates the RUDOF RDF data generator, which creates synthetic RDF datasets from ShEx and SHACL schemas using the Python bindings (pyrudof).

## About RUDOF Generate

RUDOF (RUst Data On the Fly) is an RDF generation tool that can create synthetic RDF data from schema definitions. It supports:
- **ShEx** (Shape Expressions) schemas
- **SHACL** (Shapes Constraint Language) schemas
- Multiple cardinality strategies (Minimum, Maximum, Random, Balanced)
- Various RDF output formats (Turtle, N-Triples, RDF/XML)
- Parallel processing for large datasets
- Statistical reporting
- Configurable batch processing

## Quick Start

### Using Docker (Recommended)

1. **Build the Docker image:**
   ```bash
   ./build-docker.sh
   ```

2. **Run the benchmark:**
   ```bash
   ./run-benchmark.sh
   ```

3. **View results:**
   - Generated RDF data: `output/generated_data.ttl`
   - Benchmark report: `output/benchmark_report.json`
   - Statistics: `output/generated_data.stats.json` (if enabled)

### Direct Execution (without Docker)

**Prerequisites:**
- Python 3.11+
- pyrudof package

**Installation:**
```bash
pip install pyrudof
```

**Run benchmark with default settings:**
```bash
python3 execute_benchmark.py --schema example_schema.shex --entity-count 100
```

**Run with advanced configuration:**
```bash
python3 execute_benchmark.py \
  --schema example_schema.shex \
  --entity-count 100 \
  --worker-threads 4 \
  --cardinality-strategy Balanced \
  --batch-size 100 \
  --output-format Turtle
```

## Configuration Options

### Command-Line Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--schema` | string | `example_schema.shex` | Path to ShEx/SHACL schema file |
| `--entity-count` | int | 100 | Number of entities to generate |
| `--output-dir` | string | `output` | Directory for output files |
| `--worker-threads` | int | 4 | Number of parallel worker threads (2-8 recommended) |
| `--cardinality-strategy` | choice | `Balanced` | Strategy for cardinality: `Minimum`, `Maximum`, `Random`, `Balanced` |
| `--batch-size` | int | 100 | Batch size for entity processing |
| `--output-format` | choice | `Turtle` | RDF format: `Turtle`, `NTriples`, `RDFXML` |
| `--no-stats` | flag | false | Disable statistics file generation |
| `--compress` | flag | false | Compress output file |

### Cardinality Strategies

- **Minimum**: Uses minimum cardinality values defined in the schema
  - Generates fewer relationships and smaller datasets
  - Fastest generation time
  - Example: `--cardinality-strategy Minimum`

- **Maximum**: Uses maximum cardinality values defined in the schema
  - Generates maximum relationships and larger datasets
  - Slower generation but more comprehensive data
  - Example: `--cardinality-strategy Maximum`

- **Random**: Randomly picks cardinality values within schema constraints
  - Generates varied relationship counts
  - Good for testing diverse scenarios
  - Example: `--cardinality-strategy Random`

- **Balanced** (Default): Picks balanced values between min and max
  - Moderate dataset size
  - Good balance of performance and data richness
  - Example: `--cardinality-strategy Balanced`

### Output Formats

- **Turtle** (`.ttl`): Human-readable, compact format
  - Best for: Manual inspection, small-medium datasets
  - File size: Medium

- **NTriples** (`.nt`): Line-based, simple format
  - Best for: Streaming, large datasets, parsing
  - File size: Larger

- **RDFXML** (`.rdf`): XML-based format
  - Best for: Legacy systems, XML toolchains
  - File size: Largest

### Performance Tuning

#### Worker Threads

```bash
# Single thread (slower but less memory)
python3 execute_benchmark.py --worker-threads 1 --entity-count 1000

# Optimal for most CPUs (4-8 threads)
python3 execute_benchmark.py --worker-threads 4 --entity-count 1000

# High parallelism for powerful systems
python3 execute_benchmark.py --worker-threads 8 --entity-count 1000
```

#### Batch Size

```bash
# Small batches (less memory, more overhead)
python3 execute_benchmark.py --batch-size 50 --entity-count 1000

# Medium batches (balanced)
python3 execute_benchmark.py --batch-size 100 --entity-count 1000

# Large batches (more memory, less overhead)
python3 execute_benchmark.py --batch-size 500 --entity-count 1000
```

## Usage Examples

### Example 1: Small Dataset with Maximum Relationships

```bash
python3 execute_benchmark.py \
  --schema example_schema.shex \
  --entity-count 50 \
  --cardinality-strategy Maximum \
  --output-format Turtle
```

Expected output: ~500-600 triples

### Example 2: Large Dataset with Balanced Approach

```bash
python3 execute_benchmark.py \
  --schema example_schema.shex \
  --entity-count 1000 \
  --worker-threads 8 \
  --cardinality-strategy Balanced \
  --batch-size 200 \
  --output-format NTriples
```

Expected output: ~1,500-2,000 triples

### Example 3: Minimal Dataset for Testing

```bash
python3 execute_benchmark.py \
  --schema example_schema.shex \
  --entity-count 10 \
  --cardinality-strategy Minimum \
  --worker-threads 1 \
  --no-stats
```

Expected output: ~15-20 triples

### Example 4: Production-Ready Configuration

```bash
python3 execute_benchmark.py \
  --schema example_schema.shex \
  --entity-count 5000 \
  --worker-threads 6 \
  --cardinality-strategy Balanced \
  --batch-size 250 \
  --output-format NTriples \
  --compress
```

Expected output: ~7,500-10,000 triples (compressed)

## Schema File

The benchmark uses a ShEx schema (`example_schema.shex`) that defines:
- **Person**: Entities with name, email, birthdate, age, enrolled courses, and friends
- **Course**: Entities with name, code, credits, and instructor
- **Instructor**: Entities with name, email, and courses taught

You can customize the schema or provide your own ShEx/SHACL files.

## Docker Configuration

Edit `docker-compose.yml` to adjust benchmark parameters:

```yaml
services:
  rudofgenerate:
    command: [
      "--schema", "example_schema.shex",
      "--entity-count", "100",
      "--worker-threads", "4",
      "--cardinality-strategy", "Balanced",
      "--batch-size", "100",
      "--output-format", "Turtle",
      "--output-dir", "output"
    ]
```

## Output Files

The benchmark generates:

1. **generated_data.ttl** (or .nt, .rdf) - The synthetic RDF dataset
2. **benchmark_report.json** - Performance metrics:
   ```json
   {
     "benchmark": "RUDOF Generate",
     "timestamp": "2025-11-06 12:00:00",
     "configuration": {
       "schema_file": "example_schema.shex",
       "entity_count": 100,
       "cardinality_strategy": "Balanced",
       "output_format": "Turtle",
       "worker_threads": 4,
       "batch_size": 100,
       "write_stats": true,
       "compress": false
     },
     "execution": {
       "time_seconds": 0.029,
       "success": true
     },
     "generated_data": {
       "triples_total": 149,
       "file_size_mb": 0.03,
       "output_file": "generated_data.ttl"
     },
     "performance_metrics": {
       "triples_per_second": 5114.58
     }
   }
   ```

3. **generated_data.stats.json** (optional) - Detailed generation statistics

## Benchmarking Results

Typical performance metrics (on standard hardware):

| Entity Count | Strategy | Threads | Triples | Time (s) | Triples/sec |
|--------------|----------|---------|---------|----------|-------------|
| 100 | Minimum | 4 | ~120 | 0.025 | ~4,800 |
| 100 | Balanced | 4 | ~150 | 0.029 | ~5,100 |
| 100 | Maximum | 4 | ~200 | 0.035 | ~5,700 |
| 50 | Maximum | 8 | ~600 | 0.027 | ~22,000 |
| 1000 | Balanced | 8 | ~1,500 | 0.180 | ~8,300 |

## Comparison with Other Generators

RUDOF Generate offers:
- ✅ **Fast**: Rust-based core with high performance
- ✅ **Schema-driven**: Strict conformance to ShEx/SHACL
- ✅ **Flexible**: Multiple strategies and output formats
- ✅ **Scalable**: Parallel processing support
- ✅ **Configurable**: Fine-grained control over generation

## Troubleshooting

### Import Error: pyrudof not found

```bash
pip install pyrudof
```

### Low Performance

Try increasing worker threads:
```bash
python3 execute_benchmark.py --worker-threads 8 --entity-count 1000
```

### Out of Memory

Reduce batch size or entity count:
```bash
python3 execute_benchmark.py --batch-size 50 --entity-count 500
```

### Docker Build Fails

Ensure Docker and docker-compose are installed:
```bash
docker --version
docker compose version
```

## Learn More

- [RUDOF GitHub Repository](https://github.com/rudof-project/rudof)
- [pyrudof Documentation](https://github.com/rudof-project/rudof/tree/main/python)
- [ShEx Specification](http://shex.io/)
- [SHACL Specification](https://www.w3.org/TR/shacl/)
