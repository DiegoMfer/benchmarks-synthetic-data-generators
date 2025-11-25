# LUBM Benchmark Generator

This directory contains the LUBM (Lehigh University Benchmark) generator for synthetic data generation.

## Usage

### Docker (Recommended)

The easiest way to run the benchmark is using Docker. This ensures all dependencies are properly installed and the output is saved to a persistent volume.

#### Build the Docker image:
```bash
docker build -t lubm-benchmark .
```

#### Run with default settings (1 university):
```bash
docker run --rm -v $(pwd)/output:/app/output lubm-benchmark
```

#### Run with custom number of universities:
```bash
# Generate 5 universities
docker run --rm -v $(pwd)/output:/app/output lubm-benchmark --universities 5

# Generate 10 universities with custom seed
docker run --rm -v $(pwd)/output:/app/output lubm-benchmark --universities 10 --seed 42
```

#### Using Docker Compose:
```bash
# Build and run with default settings
docker-compose run --rm lubm-benchmark

# Run with custom universities
docker-compose run --rm lubm-benchmark --universities 5

# View help
docker-compose run --rm lubm-benchmark --help
```

**Output Location**: All generated OWL files and the benchmark report will be saved in the `./output` directory relative to the LUBM folder.

### Local Python Usage

Generate 1 university (default):
```bash
python3 execute_benchmark.py
```

### CLI Parameters

- `-u, --universities N` - Number of universities to generate (default: 1)
- `-i, --index N` - Starting index of universities (default: 0)
- `-s, --seed N` - Seed for random data generation (default: 0)
- `-o, --ontology URL` - URL of the univ-bench ontology (has default)
- `-f, --format FORMAT` - Output format: "owl" or "daml" (default: "owl")

### Examples

Generate 5 universities:
```bash
python3 execute_benchmark.py -u 5
```

Generate 10 universities with custom seed:
```bash
python3 execute_benchmark.py --universities 10 --seed 42
```

View all available options:
```bash
python3 execute_benchmark.py --help
```

**Output Location**: When running locally, generated files will be in the `./output` subdirectory.

## Benchmark Report

The script automatically generates a comprehensive benchmark report that includes:

### Configuration
- Number of universities
- Starting index
- Random seed
- Output format

### Execution Metrics
- Total execution time (seconds, minutes, formatted)
- Timestamp of execution

### Triples Generated
- Class instances (entities like Professor, Student, etc.)
- Property instances (relationships and properties)
- Total triples generated

### Performance Metrics
- Triples generated per second

The report is saved as `benchmark_report.json` in the `output` directory and also printed to the console in a formatted way.

## Output

After execution, you will see:
1. Real-time console output from the generator
2. Execution time measurement
3. A detailed benchmark report (both on console and saved to JSON)

Example report output:
```
============================================================
BENCHMARK REPORT
============================================================

Timestamp: 2025-10-29T17:54:04.297801

Configuration:
  Universities: 1
  Starting Index: 0
  Random Seed: 0
  Output Format: owl

Execution Time:
  Seconds: 0.626330s
  Milliseconds: 626.330ms
  Minutes: 0.0104min
  Formatted: 0:00:00.626330

Triples Generated:
  Class Instances: 20,659
  Property Instances: 82,415
  Total Triples: 103,074

Performance Metrics:
  Triples/Second: 164,568.23

============================================================
Report saved to: /path/to/LUBM/output/benchmark_report.json
============================================================
```

## Requirements

### Docker (Recommended)
- Docker
- Docker Compose (optional, for easier management)

### Local Python
- Java 17+ (required to run the LUBM generator JAR file)
- Python 3.6+

## Output Structure

When you run the benchmark, all generated files will be stored in the `output` directory:

```
LUBM/
├── output/
│   ├── University0_0.owl
│   ├── University0_1.owl
│   ├── ...
│   ├── log.txt
│   └── benchmark_report.json
├── Dockerfile
├── docker-compose.yml
├── execute_benchmark.py
├── lubm-generator-fixed.jar
└── README.md
```

The `output` directory is:
- Created automatically if it doesn't exist
- Used as a Docker volume mount point
- Contains all generated OWL files
- Contains the benchmark report
- Can be easily cleaned between runs
