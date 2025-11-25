# RDFGraphGen Docker Setup Guide

## Overview

This guide provides detailed instructions for running the RDFGraphGen benchmark in a Docker container.

## Prerequisites

- **Docker** (version 20.10 or higher recommended)
- **Docker Compose** (version 1.29 or higher, optional)
- **Linux/macOS/Windows** with WSL2

## Docker Image Details

### Base Image
- `python:3.11-slim`

### Installed Packages
- `rdf-graph-gen` (latest from PyPI)
- Python 3.11 runtime

### Image Structure
```
/app/
  ├── execute_benchmark.py    # Benchmark execution script
  ├── input-shape.ttl          # Sample SHACL shape file
  └── output/                  # Output directory (mounted)
```

## Building the Image

### Method 1: Using the Build Script (Recommended)
```bash
cd RDFGRAPHGEN
./build-docker.sh
```

This script will:
- Build the Docker image tagged as `rdfgraphgen-benchmark`
- Display build progress
- Confirm successful build

### Method 2: Manual Docker Build
```bash
cd RDFGRAPHGEN
docker build -t rdfgraphgen-benchmark .
```

### Verify the Build
```bash
docker images | grep rdfgraphgen
```

Expected output:
```
rdfgraphgen-benchmark    latest    abc123def456    2 minutes ago    250MB
```

## Running the Container

### Method 1: Using the Run Script (Easiest)
```bash
# Default scale factor (100)
./run-benchmark.sh

# Custom scale factor
./run-benchmark.sh 500
./run-benchmark.sh 1000
```

The script automatically:
- Mounts the `./output` directory
- Sets correct user permissions
- Shows output location after completion

### Method 2: Docker Run Command
```bash
# Basic run with default parameters
docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  rdfgraphgen-benchmark

# Custom scale factor
docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  rdfgraphgen-benchmark \
  --scale-factor 1000

# Full customization
docker run --rm \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/my-shape.ttl:/app/my-shape.ttl \
  -u $(id -u):$(id -g) \
  rdfgraphgen-benchmark \
  --shape my-shape.ttl \
  --output custom-output.ttl \
  --scale-factor 2000
```

### Method 3: Docker Compose
```bash
# Default run
docker-compose run --rm rdfgraphgen-benchmark

# Custom scale factor
docker-compose run --rm rdfgraphgen-benchmark --scale-factor 1000

# Background execution
docker-compose up -d
docker-compose logs -f
docker-compose down
```

## Volume Mounts

### Output Directory
The `./output` directory is mounted as `/app/output` in the container:
```
Host: ./RDFGRAPHGEN/output
Container: /app/output
```

All generated files will be written here.

### Custom Shape Files
To use a custom SHACL shape file:
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/my-custom-shape.ttl:/app/my-custom-shape.ttl \
  rdfgraphgen-benchmark \
  --shape my-custom-shape.ttl \
  --scale-factor 500
```

## Configuration Options

### Command-Line Arguments

| Argument | Short | Default | Description |
|----------|-------|---------|-------------|
| `--shape` | `-h` | `input-shape.ttl` | SHACL shape file path |
| `--output` | `-o` | `output-graph.ttl` | Output RDF file name |
| `--scale-factor` | `-s` | `100` | Size of generated graph |
| `--output-dir` | | `output` | Output directory path |

### Environment Variables

You can set defaults using Docker environment variables:
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  -e SCALE_FACTOR=1000 \
  rdfgraphgen-benchmark
```

## Performance Tuning

### Memory Limits
For large graphs, increase Docker memory:
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  --memory=4g \
  --memory-swap=8g \
  rdfgraphgen-benchmark \
  --scale-factor 10000
```

### CPU Limits
Limit CPU usage:
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  --cpus=2 \
  rdfgraphgen-benchmark \
  --scale-factor 5000
```

### Disk I/O Optimization
For better I/O performance, use a local volume:
```bash
docker volume create rdfgraphgen-output
docker run --rm \
  -v rdfgraphgen-output:/app/output \
  rdfgraphgen-benchmark \
  --scale-factor 10000
```

## Troubleshooting

### Issue: Permission Denied on Output Files

**Problem**: Files in `./output` are owned by root

**Solution**: The run script already handles this, but if running manually:
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  rdfgraphgen-benchmark
```

### Issue: Shape File Not Found

**Problem**: `FileNotFoundError: input-shape.ttl`

**Solution**: Ensure the shape file is either:
1. In the RDFGRAPHGEN directory and rebuilt into the image:
   ```bash
   ./build-docker.sh
   ```
2. Mounted as a volume:
   ```bash
   docker run --rm \
     -v $(pwd)/output:/app/output \
     -v $(pwd)/my-shape.ttl:/app/my-shape.ttl \
     rdfgraphgen-benchmark \
     --shape my-shape.ttl
   ```

### Issue: Out of Memory

**Problem**: Container crashes with OOM (Out of Memory)

**Solution**: Increase Docker memory limit:
```bash
# Check current Docker memory limit
docker info | grep Memory

# Run with increased memory
docker run --rm \
  -v $(pwd)/output:/app/output \
  --memory=4g \
  rdfgraphgen-benchmark \
  --scale-factor 5000
```

### Issue: Slow Performance

**Problem**: Generation takes too long

**Solutions**:
1. Reduce scale factor
2. Simplify SHACL shapes
3. Use SSD for output directory
4. Increase Docker CPU allocation

### Issue: Container Won't Start

**Problem**: `docker: Error response from daemon`

**Solutions**:
```bash
# Check if port conflicts exist
docker ps -a

# Remove old containers
docker rm $(docker ps -aq -f name=rdfgraphgen)

# Rebuild image
./build-docker.sh

# Check Docker daemon
sudo systemctl status docker
```

## Best Practices

### 1. Use the Run Script
The `run-benchmark.sh` script handles common issues automatically.

### 2. Clean Up Old Outputs
```bash
# Before large runs
rm -rf output/*.ttl

# Keep only reports
find output -name "*.ttl" -delete
```

### 3. Version Your Shape Files
```bash
# Keep shapes versioned
cp input-shape.ttl input-shape-v1.0.ttl
git add input-shape-v1.0.ttl
```

### 4. Monitor Resource Usage
```bash
# Watch container stats
docker stats rdfgraphgen-benchmark

# View logs in real-time
docker logs -f <container-id>
```

### 5. Test with Small Scale First
```bash
# Always test with small scale before large runs
./run-benchmark.sh 10
./run-benchmark.sh 100
./run-benchmark.sh 1000  # Then scale up
```

## Integration with docker-compose.yml

The provided `docker-compose.yml` includes:

```yaml
version: '3.8'

services:
  rdfgraphgen-benchmark:
    build: .
    image: rdfgraphgen-benchmark
    volumes:
      - ./output:/app/output
    user: "${UID:-1000}:${GID:-1000}"
    command: ["--scale-factor", "100"]
```

Customize the scale factor:
```bash
# Edit docker-compose.yml
# Change: command: ["--scale-factor", "1000"]

# Then run
docker-compose up
```

## Cleaning Up

### Remove Containers
```bash
docker-compose down
docker rm $(docker ps -aq -f ancestor=rdfgraphgen-benchmark)
```

### Remove Images
```bash
docker rmi rdfgraphgen-benchmark
```

### Remove All Build Cache
```bash
docker builder prune -a
```

### Remove Output Files
```bash
rm -rf output/*.ttl
rm -rf output/*.json
```

## Next Steps

1. **Generate a small test dataset**: `./run-benchmark.sh 10`
2. **Inspect the output**: `cat output/output-graph.ttl | head -50`
3. **Check the benchmark report**: `cat output/benchmark_report.json`
4. **Scale up**: `./run-benchmark.sh 1000`
5. **Integrate with benchmark comparison notebook**: See main README.md

## Additional Resources

- **RDFGraphGen Documentation**: https://github.com/cadmiumkitty/rdfgraphgen
- **SHACL Specification**: https://www.w3.org/TR/shacl/
- **Docker Best Practices**: https://docs.docker.com/develop/dev-best-practices/
