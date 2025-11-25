# Docker Setup for GAIA Benchmark

This document describes how to run the GAIA generator using Docker.

## Prerequisites

- Docker installed and running
- Docker Compose (optional, for easier management)

## Building the Image

```bash
# Build the Docker image
./build-docker.sh

# Or manually
docker build -t gaia-benchmark .
```

## Running the Container

### Basic Usage

```bash
# Run with default parameters (3 instances per class)
docker run --rm -v $(pwd)/output:/app/output gaia-benchmark

# Run with custom parameters
docker run --rm -v $(pwd)/output:/app/output gaia-benchmark \
  --instances 10 --limit 20 --materialization
```

### Using Docker Compose

```bash
# Run with docker-compose
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs

# Stop and remove
docker-compose down
```

### Advanced Usage

```bash
# Interactive mode
docker run -it --rm -v $(pwd)/output:/app/output gaia-benchmark bash

# Custom memory settings
docker run --rm -v $(pwd)/output:/app/output \
  -e JAVA_OPTS="-Xmx16g" \
  gaia-benchmark --instances 20

# Custom output filename
docker run --rm -v $(pwd)/output:/app/output \
  gaia-benchmark --instances 5 --output output/my_instances.owl
```

## Volume Mounts

The container expects the following volume mount:
- `./output:/app/output` - For output files and reports

## Environment Variables

- `JAVA_OPTS` - JVM options (default: -Xmx8g)

## Container Structure

```
/app/
├── OWLGenerator.jar          # GAIA generator
├── lib/                      # Java dependencies
├── execute_benchmark.py      # Benchmark script
├── run-benchmark.sh          # Shell script
├── output/                   # Output directory (mounted)
└── univ-bench.owl           # LUBM ontology (downloaded)
```

## Troubleshooting

### Memory Issues
```bash
# Increase memory allocation
docker run --rm -v $(pwd)/output:/app/output \
  -e JAVA_OPTS="-Xmx16g" \
  gaia-benchmark --instances 50
```

### Permission Issues
```bash
# Fix output directory permissions
sudo chown -R $USER:$USER output/
```

### Network Issues
```bash
# Run with host network (if ontology download fails)
docker run --rm --network host \
  -v $(pwd)/output:/app/output \
  gaia-benchmark --instances 5
```

## Performance Notes

- Default memory allocation: 8GB
- Recommended minimum: 4GB for small datasets
- For large datasets (>50 instances per class): 16GB+
- Multi-threading is enabled by default in GAIA
