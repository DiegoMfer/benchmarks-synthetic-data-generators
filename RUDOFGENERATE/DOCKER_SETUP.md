# Docker Setup for RUDOF Generate Benchmark

This document provides detailed instructions for running the RUDOF Generate benchmark using Docker.

## Prerequisites

- Docker (version 20.10 or later)
- docker-compose (version 1.29 or later)

## Installation

### Install Docker

**Ubuntu/Debian:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**macOS:**
Download and install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop)

**Windows:**
Download and install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop)

### Install docker-compose

**Linux:**
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

**macOS/Windows:**
docker-compose is included with Docker Desktop.

## Building the Docker Image

The Docker image contains:
- Python 3.11
- pyrudof package (RUDOF Python bindings)
- Benchmark scripts
- Example ShEx schema

Build the image:
```bash
./build-docker.sh
```

Or manually:
```bash
docker-compose build
```

## Running the Benchmark

### Quick Run

```bash
./run-benchmark.sh
```

### Manual Run

```bash
docker-compose up
```

### Custom Parameters

Edit `docker-compose.yml` to change benchmark parameters:

```yaml
services:
  rudofgenerate:
    command: [
      "--schema", "example_schema.shex",
      "--entity-count", "500",  # Change this
      "--output-dir", "output"
    ]
```

Then run:
```bash
docker-compose up
```

## Docker Image Details

### Base Image
- `python:3.11-slim` - Lightweight Python 3.11 image

### Installed Packages
- `pyrudof` - RUDOF Python bindings for RDF generation
- `curl` - For downloading resources if needed

### Volumes
- `./output:/app/output` - Mounts local output directory

### Working Directory
- `/app` - All scripts and schemas are copied here

## Output Files

All output files are written to the `output/` directory:
- `generated_data.ttl` - Generated RDF dataset
- `benchmark_report.json` - Performance metrics
- `generated_data.stats.json` - Detailed statistics (if enabled)

## Troubleshooting

### Permission Issues

If you encounter permission errors with output files:

```bash
sudo chown -R $USER:$USER output/
```

### Container Won't Start

Check Docker logs:
```bash
docker-compose logs
```

### Out of Memory

For large datasets, increase Docker memory limit in Docker Desktop settings or via command line:

```bash
docker-compose run --rm -e DOCKER_MEMORY=4g rudofgenerate
```

### Rebuild After Changes

If you modify scripts or schemas:

```bash
docker-compose build --no-cache
docker-compose up
```

## Cleaning Up

### Remove Output Files
```bash
rm -rf output/
```

### Remove Docker Container
```bash
docker-compose down
```

### Remove Docker Image
```bash
docker rmi rudofgenerate_rudofgenerate
```

### Complete Cleanup
```bash
docker-compose down --rmi all --volumes
rm -rf output/
```

## Advanced Docker Usage

### Interactive Shell

Access the container shell for debugging:

```bash
docker-compose run --rm rudofgenerate /bin/bash
```

### Run with Different Schema

1. Place your schema file in the RUDOFGENERATE directory
2. Update docker-compose.yml:
   ```yaml
   command: ["--schema", "my_schema.shex", "--entity-count", "100"]
   ```
3. Rebuild and run:
   ```bash
   docker-compose build
   docker-compose up
   ```

### Custom Python Commands

Run custom Python commands inside the container:

```bash
docker-compose run --rm rudofgenerate python3 -c "import pyrudof; print(pyrudof.__version__)"
```

## Docker Compose Configuration

The `docker-compose.yml` file defines:

```yaml
version: '3.8'

services:
  rudofgenerate:
    build: .                          # Build from local Dockerfile
    container_name: rudofgenerate-benchmark
    volumes:
      - ./output:/app/output          # Mount output directory
    environment:
      - PYTHONUNBUFFERED=1            # Unbuffered Python output
    command: [                         # Benchmark parameters
      "--schema", "example_schema.shex",
      "--entity-count", "100",
      "--output-dir", "output"
    ]
```

## Security Considerations

- The container runs as root by default
- Output directory is mounted with read/write access
- No network ports are exposed
- No sensitive data should be placed in the container

## Performance Tips

1. **Increase Entity Count**: Edit `entity-count` in docker-compose.yml
2. **Use SSD Storage**: Mount output directory on SSD for better I/O
3. **Allocate More Memory**: Configure Docker to use more RAM
4. **Multi-threading**: The generator uses 4 worker threads by default

## Monitoring

View real-time logs:
```bash
docker-compose logs -f
```

Check container resource usage:
```bash
docker stats rudofgenerate-benchmark
```

## Integration with CI/CD

Example GitHub Actions workflow:

```yaml
name: RUDOF Benchmark

on: [push]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build Docker image
        run: cd RUDOFGENERATE && docker-compose build
      - name: Run benchmark
        run: cd RUDOFGENERATE && docker-compose up
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: benchmark-results
          path: RUDOFGENERATE/output/
```
