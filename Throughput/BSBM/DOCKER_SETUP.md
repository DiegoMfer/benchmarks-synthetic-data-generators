# BSBM Docker Setup - Complete! ✅

## Summary

Successfully created a complete Docker-based setup for the Berlin SPARQL Benchmark (BSBM) generator, similar to the LUBM setup.

## What Was Done

### 1. **Copied Essential Files** ✅
   - `bsbm.jar` (172K) - Main benchmark generator
   - `ssj.jar` (829K) - Stochastic simulation library  
   - `givennames.txt` (1.2M) - Names database
   - `titlewords.txt` (860K) - Product title words

### 2. **Created Python Wrapper Script** ✅
   - `execute_benchmark.py` with full CLI support
   - Automatic metrics parsing and reporting
   - Progress tracking and error handling
   - JSON report generation

### 3. **Dockerized the Application** ✅
   - `Dockerfile` with Java 21 + Python 3.11
   - `docker-compose.yml` for easy management
   - `.dockerignore` and `.gitignore` for clean builds
   - Volume mapping for output files

### 4. **Created Helper Scripts** ✅
   - `build-docker.sh` - Quick image building
   - `run-benchmark.sh` - Easy benchmark execution
   - Both scripts are executable and tested

### 5. **Comprehensive Documentation** ✅
   - `README.md` with full usage guide
   - Examples for all use cases
   - Performance benchmarks included

## File Structure

```
BSBM/
├── output/                      # Generated files (auto-created)
│   ├── dataset.ttl              # Generated RDF data
│   └── benchmark_report.json    # Metrics report
├── bsbm.jar                     # BSBM generator (copied from bsbmtools-0.2)
├── ssj.jar                      # Stochastic library
├── givennames.txt               # Names database
├── titlewords.txt               # Product title words
├── execute_benchmark.py         # Python wrapper script
├── Dockerfile                   # Docker image definition
├── docker-compose.yml          # Docker Compose config
├── build-docker.sh             # Build script (executable)
├── run-benchmark.sh            # Run script (executable)
├── README.md                   # Full documentation
├── .gitignore                  # Git exclusions
├── .dockerignore               # Docker build exclusions
└── bsbmtools-0.2/              # Original tools (kept for reference)
```

## Quick Start Examples

### Build the Image
```bash
cd BSBM
./build-docker.sh
```

### Run Benchmarks

**Small dataset (1,000 products):**
```bash
./run-benchmark.sh 1000
```

**Large dataset (100,000 products):**
```bash
./run-benchmark.sh 100000
```

**Custom format (N-Triples):**
```bash
./run-benchmark.sh 50000 nt
```

**Direct Docker command:**
```bash
docker run --rm -v $(pwd)/output:/app/output bsbm-benchmark --products 10000 --format ttl
```

## Test Results

✅ **Successfully generated a 1,000 product dataset:**
- **Execution Time:** 3.72 seconds
- **Total Triples:** 374,911
- **Performance:** 100,726 triples/second
- **Output Format:** Turtle (TTL)
- **File Location:** `./output/dataset.ttl`

## Available Options

### Command Line Arguments
- `-p, --products N` - Number of products (default: 1000)
- `-f, --format FORMAT` - Output format: ttl, nt, n3, trig (default: ttl)
- `--no-fc` - Disable forward chaining (reasoning)
- `-o, --output NAME` - Base name for output files (default: dataset)
- `-d, --output-dir DIR` - Output directory (default: output)

### Dataset Sizes
- **1,000 products** → ~375K triples → ~35MB (3-5 seconds)
- **10,000 products** → ~3.5M triples → ~350MB (30-60 seconds)
- **100,000 products** → ~35M triples → ~3.5GB (5-10 minutes)

## Key Features

1. **Automatic Metrics Tracking**
   - Triples generated
   - Execution time
   - Entity counts (products, vendors, reviews, etc.)
   - Performance metrics (triples/sec)

2. **Flexible Output**
   - Multiple RDF formats supported
   - Volume-mapped output directory
   - JSON report generation

3. **Easy to Use**
   - Simple bash scripts for common tasks
   - Docker/Docker Compose support
   - No manual Java setup required

4. **Production Ready**
   - 2GB heap for large datasets
   - Clean Docker image (minimal size)
   - Proper error handling

## Comparison with LUBM

| Feature | LUBM | BSBM |
|---------|------|------|
| **Language** | Java | Java |
| **Python Wrapper** | ✅ | ✅ |
| **Docker Support** | ✅ | ✅ |
| **Helper Scripts** | ✅ | ✅ |
| **JSON Reporting** | ✅ | ✅ |
| **Volume Mapping** | ✅ | ✅ |
| **Java Version** | JDK 17 | JDK 21 |
| **Domain** | University | E-commerce |
| **Main Parameter** | Universities | Products |

## Next Steps

You can now:
1. Generate datasets of any size
2. Use the JAR files directly if needed
3. Customize the Python script for your needs
4. Integrate into CI/CD pipelines
5. Compare with other generators in your benchmark suite

## Notes

- The original `bsbmtools-0.2` folder is kept for reference
- The 3.1GB dataset you generated earlier is in `bsbmtools-0.2/dataset.ttl`
- All new runs will output to the `BSBM/output/` directory
- The Docker setup uses Java 21 (newer than LUBM's Java 17)

---

**Setup completed successfully!** 🎉

The BSBM benchmark is now fully containerized and ready to use, just like LUBM.
