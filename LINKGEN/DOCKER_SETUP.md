# LINKGEN Docker Setup Guide

This guide provides detailed instructions for running the LINKGEN benchmark using Docker.

## Prerequisites

- Docker 20.10 or higher
- Docker Compose 1.29 or higher (optional)
- At least 4GB of available disk space
- At least 4GB of RAM

## Building the Docker Image

### Option 1: Using the Build Script (Recommended)

```bash
chmod +x build-docker.sh
./build-docker.sh
```

### Option 2: Using Docker Command Directly

```bash
docker build -t linkgen-benchmark .
```

### Option 3: Using Docker Compose

```bash
docker-compose build
```

## Running the Benchmark

### Option 1: Using the Run Script (Simplest)

```bash
chmod +x run-benchmark.sh

# Default: 100K triples with DBpedia
./run-benchmark.sh

# Custom: 200K triples with Schema.org
./run-benchmark.sh 200000 schemaorg.owl zipf

# With Gaussian distribution
./run-benchmark.sh 150000 dbpedia_2015.owl gaussian
```

### Option 2: Using Docker Run Command

```bash
# Basic run with default parameters
docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  linkgen-benchmark

# Custom parameters
docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  linkgen-benchmark \
  --triples 200000 \
  --ontology schemaorg.owl \
  --distribution zipf \
  --threads 4
```

### Option 3: Using Docker Compose

Edit `docker-compose.yml` to customize parameters, then run:

```bash
docker-compose up
```

Or override the command:

```bash
docker-compose run --rm linkgen-benchmark \
  --triples 500000 \
  --ontology dbpedia_2015.owl \
  --threads 4
```

## Configuration Examples

### Example 1: Small Dataset (Quick Test)
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  linkgen-benchmark \
  --triples 10000 \
  --threads 2
```

### Example 2: Medium Dataset with Schema.org
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  linkgen-benchmark \
  --triples 500000 \
  --ontology schemaorg.owl \
  --distribution zipf \
  --zipf-exponent 2.3
```

### Example 3: Large Dataset with Gaussian Distribution
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  -e JAVA_OPTS="-Xmx8G" \
  linkgen-benchmark \
  --triples 2000000 \
  --distribution gaussian \
  --gaussian-mean 200 \
  --gaussian-deviation 25 \
  --threads 8
```

### Example 4: N-Quads Format with Entity Linking
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  linkgen-benchmark \
  --triples 100000 \
  --format nq \
  --sameas True
```

### Example 5: Minimal Noise Generation
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  linkgen-benchmark \
  --triples 100000 \
  --noise True \
  --noise-total 1000 \
  --noise-duplicate 100
```

## Memory Configuration

The default Java heap size is 4GB. For larger datasets, increase memory:

### Method 1: Environment Variable
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  -e JAVA_OPTS="-Xmx8G" \
  linkgen-benchmark \
  --triples 2000000
```

### Method 2: Docker Compose
Edit `docker-compose.yml`:
```yaml
environment:
  - JAVA_OPTS=-Xmx8G
```

### Memory Recommendations
- 100K triples: 2GB RAM
- 500K triples: 4GB RAM
- 1M triples: 6GB RAM
- 2M+ triples: 8GB+ RAM

## Output Files

All generated files are saved to the `./output` directory:

```
output/
├── data_0.nt          # Generated RDF data (N-Triples)
├── data_1.nt          # Additional data files
├── void.ttl           # VoID dataset description
├── linkgen.log        # Execution log
└── benchmark_report.json  # Performance report
```

## Troubleshooting

### Issue: Permission Denied on Output Files

**Problem:** Files created by Docker have wrong permissions.

**Solution:** Use user mapping:
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  linkgen-benchmark
```

### Issue: Out of Memory Error

**Problem:** Java heap space error during execution.

**Symptoms:**
```
java.lang.OutOfMemoryError: Java heap space
```

**Solution:** Increase Java heap size:
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  -e JAVA_OPTS="-Xmx8G" \
  linkgen-benchmark
```

### Issue: Ontology File Not Found

**Problem:** Missing ontology files in Docker image.

**Solution:** Ensure `.owl` files are in the directory before building:
```bash
ls -la *.owl
docker build -t linkgen-benchmark .
```

### Issue: Container Exits Immediately

**Problem:** Configuration error or invalid parameters.

**Solution:** Check logs:
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  linkgen-benchmark \
  --triples 100000
```

View logs:
```bash
cat output/linkgen.log
```

### Issue: Slow Performance

**Possible causes and solutions:**

1. **Insufficient CPU cores:**
   - Increase threads: `--threads 8`
   
2. **Low memory:**
   - Increase heap: `-e JAVA_OPTS="-Xmx8G"`
   
3. **Disk I/O bottleneck:**
   - Use faster storage (SSD)
   - Reduce file splits: `--triples-per-file 500000`

### Issue: Docker Build Fails

**Problem:** Build errors during image creation.

**Solution:** 
1. Check Docker version: `docker --version`
2. Ensure all files are present:
   ```bash
   ls -la linkgen.jar lib/*.jar *.owl entity.nt
   ```
3. Clean rebuild:
   ```bash
   docker system prune -a
   ./build-docker.sh
   ```

## Volume Mounting

### Linux/macOS
```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  linkgen-benchmark
```

### Windows (PowerShell)
```powershell
docker run --rm `
  -v ${PWD}/output:/app/output `
  linkgen-benchmark
```

### Windows (CMD)
```cmd
docker run --rm ^
  -v %cd%/output:/app/output ^
  linkgen-benchmark
```

## Cleaning Up

### Remove Generated Files
```bash
rm -rf output/*
```

### Remove Docker Image
```bash
docker rmi linkgen-benchmark
```

### Remove All Containers and Images
```bash
docker system prune -a
```

## Performance Benchmarks

Approximate execution times on a modern system (Intel i7, 16GB RAM):

| Triples   | Ontology  | Distribution | Threads | Time    |
|-----------|-----------|--------------|---------|---------|
| 10K       | DBpedia   | Zipf         | 2       | ~5s     |
| 100K      | DBpedia   | Zipf         | 2       | ~15s    |
| 500K      | DBpedia   | Zipf         | 4       | ~45s    |
| 1M        | DBpedia   | Zipf         | 8       | ~90s    |
| 100K      | Schema.org| Zipf         | 2       | ~12s    |
| 100K      | DBpedia   | Gaussian     | 2       | ~18s    |

*Actual times may vary based on hardware and configuration.*

## Advanced Usage

### Running Multiple Benchmarks

```bash
# Run multiple configurations
for triples in 10000 50000 100000; do
  docker run --rm \
    -v $(pwd)/output_${triples}:/app/output \
    -u $(id -u):$(id -g) \
    linkgen-benchmark \
    --triples $triples \
    --output-name data_${triples}
done
```

### Custom Ontology

To use a custom ontology:

1. Place your `.owl` file in the LINKGEN directory
2. Rebuild the Docker image
3. Use the filename in the `--ontology` parameter

## Support

For issues related to:
- **LINKGEN tool:** https://github.com/akjoshi/linkgen/
- **Docker setup:** Check this guide and Docker documentation
- **Performance:** See troubleshooting section above

## See Also

- [README.md](README.md) - Main documentation
- [LINKGEN GitHub](https://github.com/akjoshi/linkgen/)
- [Docker Documentation](https://docs.docker.com/)
