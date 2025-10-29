# LUBM Benchmark - Docker Setup Summary

## What Was Done

### 1. **Moved execute_benchmark.py to LUBM folder** ✅
   - Script is now inside the LUBM directory
   - Works with relative paths

### 2. **Added CLI Parameterization** ✅
   - `-u, --universities N` - Number of universities to generate
   - `-i, --index N` - Starting index
   - `-s, --seed N` - Random seed
   - `-o, --ontology URL` - Ontology URL
   - `-f, --format FORMAT` - Output format (owl/daml)

### 3. **Enhanced Benchmark Reporting** ✅
   - Reports now focus on **time** and **triples generated**
   - Shows class instances, property instances, and total triples
   - Displays triples per second performance metric
   - Simplified output (removed file size metrics)

### 4. **Dockerized the Application** ✅
   - Created `Dockerfile` with Java 17 + Python 3.11
   - Created `docker-compose.yml` for easier management
   - Created `.dockerignore` to optimize build
   - Created `build-docker.sh` quick start script

### 5. **Volume Management** ✅
   - All generated files go to `./output` directory
   - Path is relative to LUBM folder structure
   - Docker volume maps `./output` to `/app/output`
   - Easy to access, backup, or clean generated files

## File Structure

```
LUBM/
├── output/                        # Generated files (gitignored)
│   ├── University0_*.owl         # Generated OWL files
│   ├── log.txt                   # Generator log
│   └── benchmark_report.json     # Benchmark report
├── Dockerfile                     # Docker image definition
├── docker-compose.yml            # Docker Compose config
├── .dockerignore                 # Docker build exclusions
├── .gitignore                    # Git exclusions
├── build-docker.sh               # Quick build script
├── execute_benchmark.py          # Main benchmark script
├── lubm-generator-fixed.jar      # LUBM generator
└── README.md                     # Documentation
```

## Quick Start

### Using Docker (Recommended)

```bash
# Build the image
./build-docker.sh

# OR manually:
docker build -t lubm-benchmark .

# Run with 1 university
docker run --rm -v $(pwd)/output:/app/output lubm-benchmark

# Run with 5 universities
docker run --rm -v $(pwd)/output:/app/output lubm-benchmark --universities 5
```

### Using Docker Compose

```bash
# Run with default (1 university)
docker-compose run --rm lubm-benchmark

# Run with custom universities
docker-compose run --rm lubm-benchmark --universities 5
```

### Using Python Locally

```bash
python3 execute_benchmark.py --universities 5
```

## Benchmark Report Format

The new report focuses on execution time and triples generated:

```json
{
  "timestamp": "2025-10-29T17:54:04.297801",
  "configuration": {
    "universities": 1,
    "starting_index": 0,
    "seed": 0,
    "format": "owl"
  },
  "execution": {
    "time_seconds": 0.62633,
    "time_milliseconds": 626.33,
    "time_minutes": 0.0104,
    "time_formatted": "0:00:00.626330"
  },
  "triples_generated": {
    "class_instances": 20659,
    "property_instances": 82415,
    "total_triples": 103074
  },
  "performance_metrics": {
    "triples_per_second": 164568.23
  }
}
```

## Output Location

All generated files are stored in `LUBM/output/`:
- ✅ Relative to LUBM folder
- ✅ Automatically created if missing
- ✅ Mounted as Docker volume
- ✅ Gitignored to avoid committing large files
- ✅ Easy to clean between runs

## Benefits

1. **Isolated Environment**: Docker ensures consistent Java/Python versions
2. **Easy Deployment**: Single command to build and run
3. **Clean Output**: All files in one dedicated directory
4. **Persistent Storage**: Volume mounting preserves data
5. **Flexible CLI**: Easy to parameterize number of universities
6. **Focused Metrics**: Report shows what matters (time + triples)
