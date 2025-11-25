# PyGraft Docker Setup Guide

Complete guide for running PyGraft benchmark in Docker containers.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 1.29+
- 4GB RAM minimum (8GB recommended for large graphs)
- 2GB disk space

## Quick Start

### 1. Build the Image

```bash
chmod +x build-docker.sh
./build-docker.sh
```

Or manually:
```bash
docker build -t pygraft-benchmark:latest .
```

### 2. Run with Docker Compose

```bash
docker-compose up
```

This runs the default configuration:
- Mode: full (schema + KG)
- Classes: 50
- Relations: 30
- Instances: 50 per class

### 3. Check Results

```bash
ls -lh output/
cat output/benchmark_report.json
```

## Custom Configurations

### Method 1: Edit docker-compose.yml

Modify the `command` section:

```yaml
services:
  pygraft:
    # ... other settings ...
    command: >
      python execute_benchmark.py
      --mode full
      --n-classes 100
      --n-relations 60
      --avg-instances 100
      --multitask
```

Then run:
```bash
docker-compose up
```

### Method 2: Direct Docker Run

```bash
docker run -v $(pwd)/output:/app/output pygraft-benchmark:latest \
  python execute_benchmark.py \
  --mode full \
  --n-classes 200 \
  --avg-instances 150 \
  --multitask
```

### Method 3: Interactive Container

```bash
docker run -it -v $(pwd)/output:/app/output pygraft-benchmark:latest bash

# Inside container:
python execute_benchmark.py --n-classes 100 --verbosity 2
```

## Configuration Examples

### Small Test Run
```bash
docker run -v $(pwd)/output:/app/output pygraft-benchmark:latest \
  python execute_benchmark.py \
  --mode schema \
  --n-classes 20 \
  --n-relations 10
```

### Medium Benchmark
```bash
docker run -v $(pwd)/output:/app/output pygraft-benchmark:latest \
  python execute_benchmark.py \
  --n-classes 100 \
  --avg-instances 75
```

### Large KG with Parallel Processing
```bash
docker run -v $(pwd)/output:/app/output pygraft-benchmark:latest \
  python execute_benchmark.py \
  --n-classes 200 \
  --avg-instances 150 \
  --multitask \
  --verbosity 2
```

### Fast Mode (No Consistency Check)
```bash
docker run -v $(pwd)/output:/app/output pygraft-benchmark:latest \
  python execute_benchmark.py \
  --n-classes 150 \
  --no-check-consistency
```

## Environment Variables

The Docker container includes:

- `JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64`
- `PATH` includes Java binaries
- Python 3.11 with PyGraft pre-installed

## Volume Mounts

The `output/` directory is mounted to persist generated files:

```yaml
volumes:
  - ./output:/app/output
```

All generated files appear in your local `output/` folder.

## Resource Limits

### Setting Memory Limits

In `docker-compose.yml`:

```yaml
services:
  pygraft:
    # ... other settings ...
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G
```

Or with `docker run`:

```bash
docker run --memory=8g --memory-reservation=4g \
  -v $(pwd)/output:/app/output \
  pygraft-benchmark:latest \
  python execute_benchmark.py --n-classes 200
```

### Setting CPU Limits

```bash
docker run --cpus=4 \
  -v $(pwd)/output:/app/output \
  pygraft-benchmark:latest \
  python execute_benchmark.py --multitask
```

## Troubleshooting

### Problem: Permission Denied on Output Files

**Cause:** Docker writes files as root by default.

**Solution:** Use user mapping in docker-compose.yml:

```yaml
services:
  pygraft:
    user: "${UID:-1000}:${GID:-1000}"
```

Run with your user ID:
```bash
UID=$(id -u) GID=$(id -g) docker-compose up
```

### Problem: Java Not Found

**Cause:** JAVA_HOME not set correctly.

**Solution:** The Dockerfile sets this automatically, but you can verify:

```bash
docker run pygraft-benchmark:latest java -version
```

Should show: `openjdk version "17.x.x"`

### Problem: Out of Memory During Generation

**Symptoms:**
- Container killed
- "Killed" message
- Incomplete output files

**Solutions:**

1. **Increase Docker memory:**
   - Docker Desktop: Settings → Resources → Memory → 8GB+

2. **Reduce graph size:**
   ```bash
   docker run -v $(pwd)/output:/app/output pygraft-benchmark:latest \
     python execute_benchmark.py \
     --n-classes 50 \
     --avg-instances 50
   ```

3. **Disable consistency checking:**
   ```bash
   docker run -v $(pwd)/output:/app/output pygraft-benchmark:latest \
     python execute_benchmark.py \
     --no-check-consistency
   ```

### Problem: Slow Generation

**Symptoms:**
- Takes very long time
- High CPU usage

**Solutions:**

1. **Enable multitasking:**
   ```bash
   docker run -v $(pwd)/output:/app/output pygraft-benchmark:latest \
     python execute_benchmark.py --multitask
   ```

2. **Disable consistency checking:**
   ```bash
   docker run -v $(pwd)/output:/app/output pygraft-benchmark:latest \
     python execute_benchmark.py --no-check-consistency
   ```

3. **Reduce verbosity:**
   ```bash
   docker run -v $(pwd)/output:/app/output pygraft-benchmark:latest \
     python execute_benchmark.py --verbosity 0
   ```

### Problem: Inconsistent KG Errors

**Symptoms:**
- HermiT reasoner detects inconsistencies
- Generation fails after long processing

**Solutions:**

1. **Reduce conflicting properties:**
   ```bash
   docker run -v $(pwd)/output:/app/output pygraft-benchmark:latest \
     python execute_benchmark.py \
     --p-functional 0.1 \
     --p-inverse-functional 0.05
   ```

2. **Simplify structure:**
   ```bash
   docker run -v $(pwd)/output:/app/output pygraft-benchmark:latest \
     python execute_benchmark.py \
     --n-classes 50 \
     --max-depth 3
   ```

3. **Skip consistency check (not recommended for production):**
   ```bash
   docker run -v $(pwd)/output:/app/output pygraft-benchmark:latest \
     python execute_benchmark.py --no-check-consistency
   ```

## Container Management

### List Running Containers
```bash
docker ps
```

### Stop Container
```bash
docker-compose down
# or
docker stop pygraft-benchmark
```

### View Logs
```bash
docker-compose logs -f
# or
docker logs -f pygraft-benchmark
```

### Remove Container and Image
```bash
docker-compose down
docker rmi pygraft-benchmark:latest
```

### Clean Up Everything
```bash
docker-compose down -v
docker system prune -a
```

## Advanced Usage

### Multi-Stage Builds

Generate schema first, then KG:

```bash
# Stage 1: Generate schema
docker run -v $(pwd)/output:/app/output pygraft-benchmark:latest \
  python execute_benchmark.py --mode schema --n-classes 100

# Stage 2: Generate KG from schema
docker run -v $(pwd)/output:/app/output pygraft-benchmark:latest \
  python execute_benchmark.py --mode kg
```

### Batch Processing

Create a script `batch_run.sh`:

```bash
#!/bin/bash
for classes in 50 100 150 200; do
  echo "Running with $classes classes..."
  docker run -v $(pwd)/output:/app/output pygraft-benchmark:latest \
    python execute_benchmark.py \
    --n-classes $classes \
    --output-dir "output/run_${classes}"
done
```

### Custom Dockerfile Modifications

To add custom Python packages:

```dockerfile
FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends openjdk-17-jre-headless && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

WORKDIR /app

# Add custom packages here
RUN pip install --no-cache-dir pygraft pandas numpy

COPY execute_benchmark.py .
RUN mkdir -p output

VOLUME /app/output
CMD ["python", "execute_benchmark.py", "--help"]
```

## Performance Benchmarks

Approximate generation times (Docker on 4-core, 8GB RAM):

| Classes | Relations | Instances | Time (no check) | Time (with check) |
|---------|-----------|-----------|-----------------|-------------------|
| 20      | 10        | 50        | ~10s            | ~20s              |
| 50      | 30        | 50        | ~30s            | ~60s              |
| 100     | 50        | 75        | ~90s            | ~180s             |
| 200     | 100       | 100       | ~300s           | ~600s             |

*Times vary based on probability settings and system resources*

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: PyGraft Benchmark

on: [push]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker Image
        run: |
          cd PYGRAFT
          docker build -t pygraft-benchmark .
      
      - name: Run Benchmark
        run: |
          docker run -v ${{ github.workspace }}/PYGRAFT/output:/app/output \
            pygraft-benchmark:latest \
            python execute_benchmark.py --n-classes 50
      
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: PYGRAFT/output/
```

## Best Practices

1. **Always use volume mounts** to preserve generated data
2. **Set memory limits** for large graphs to prevent system overload
3. **Use multitask mode** for faster generation when possible
4. **Start small** (20-50 classes) to test configuration
5. **Monitor logs** with `docker-compose logs -f`
6. **Clean up regularly** with `docker system prune`

## Support

For issues specific to:
- **PyGraft package**: https://github.com/nicolas-hbt/pygraft/issues
- **This benchmark setup**: Check main project README
- **Docker**: https://docs.docker.com/

## Additional Resources

- PyGraft Documentation: https://pygraft.readthedocs.io/
- PyGraft Paper: https://arxiv.org/pdf/2309.03685.pdf
- Docker Best Practices: https://docs.docker.com/develop/dev-best-practices/
