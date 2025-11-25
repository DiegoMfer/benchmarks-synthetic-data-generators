# Docker Setup for RDFMutate Benchmark

This guide provides detailed instructions for building and running the RDFMutate benchmark using Docker.

## Prerequisites

- Docker installed on your system
- Docker Compose (optional, but recommended)

## Building the Docker Image

### Option 1: Using the build script (Recommended)

```bash
./build-docker.sh
```

### Option 2: Manual build

```bash
docker build -t rdfmutate-benchmark .
```

## Running the Benchmark

### Option 1: Using the run script (Easiest)

```bash
# Run with default configuration
./run-benchmark.sh

# Run with custom configuration file
./run-benchmark.sh my-config.yaml
```

### Option 2: Using Docker directly

```bash
# Run with default configuration
docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  rdfmutate-benchmark

# Run with custom configuration
docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  rdfmutate-benchmark \
  --config my-config.yaml
```

### Option 3: Using Docker Compose

```bash
# Run with default configuration
docker-compose run --rm rdfmutate-benchmark

# Run with custom configuration
docker-compose run --rm rdfmutate-benchmark --config my-config.yaml
```

## Volume Mounts

The Docker container uses volume mounts to persist generated data:

- `./output:/app/output` - Output directory for generated RDF files and reports

### Adding Custom Files

To use custom seed graphs or mutation operators:

1. **Place files in the current directory** or subdirectories
2. **Mount them as volumes**:

```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/my-seed.ttl:/app/my-seed.ttl \
  -v $(pwd)/my-operator.ttl:/app/my-operator.ttl \
  rdfmutate-benchmark \
  --config my-config.yaml
```

3. **Reference them in your config**:

```yaml
seed_graph:
  file: my-seed.ttl

mutation_operators:
  - resource:
      file: my-operator.ttl
      syntax: swrl
```

## Configuration

### Default Configuration

The default `config.yaml` is included in the Docker image:

```yaml
strict_parsing: false

seed_graph:
  file: seed.ttl
  type: rdf

output_graph:
  file: output/mutated.ttl
  overwrite: true
  type: rdf

number_of_mutations: 1
number_of_mutants: 1

mutation_operators:
  - resource:
      file: addRelation.ttl
      syntax: swrl

print_summary: true
```

### Custom Configuration

Create your own YAML file and mount it:

```bash
# Create custom config
cat > my-config.yaml << EOF
strict_parsing: false
seed_graph:
  file: my-seed.ttl
  type: rdf
output_graph:
  file: output/my-output.ttl
  overwrite: true
  type: rdf
number_of_mutations: 10
number_of_mutants: 5
mutation_operators:
  - resource:
      file: my-operators.ttl
      syntax: swrl
print_summary: true
EOF

# Run with custom config
docker run --rm \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/my-config.yaml:/app/my-config.yaml \
  -v $(pwd)/my-seed.ttl:/app/my-seed.ttl \
  -v $(pwd)/my-operators.ttl:/app/my-operators.ttl \
  rdfmutate-benchmark \
  --config my-config.yaml
```

## Memory Configuration

By default, the container uses up to 2GB of heap memory. To adjust:

```bash
# Set custom memory limit
docker run --rm \
  -v $(pwd)/output:/app/output \
  -e JAVA_OPTS="-Xmx4G" \
  rdfmutate-benchmark
```

Or update `docker-compose.yml`:

```yaml
environment:
  - JAVA_OPTS=-Xmx4G
```

## Output Files

Generated files appear in the `./output` directory:

- `mutated.ttl` (or specified filename) - Generated RDF graph(s)
- `benchmark_report.json` - Performance metrics and statistics

If `number_of_mutants > 1`, files are numbered:
- `mutated0.ttl`
- `mutated1.ttl`
- `mutated2.ttl`
- etc.

## Troubleshooting

### Permission Errors

If you get permission errors on output files:

```bash
# Run with your user ID (recommended)
docker run --rm \
  -v $(pwd)/output:/app/output \
  -u $(id -u):$(id -g) \
  rdfmutate-benchmark
```

### File Not Found Errors

Ensure your config file references mounted paths correctly:

```yaml
# ✅ Correct - relative to container working directory
seed_graph:
  file: seed.ttl

# ❌ Incorrect - absolute host path
seed_graph:
  file: /home/user/seed.ttl
```

### Java Out of Memory

Increase heap size:

```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  -e JAVA_OPTS="-Xmx8G" \
  rdfmutate-benchmark
```

### Image Build Fails

Check Docker has enough disk space and try rebuilding:

```bash
# Clean up old images
docker system prune -a

# Rebuild
./build-docker.sh
```

## Examples

### Quick Test Run

```bash
# Build
./build-docker.sh

# Run with defaults
./run-benchmark.sh
```

### Large-Scale Generation

```bash
# Create config for 100 mutants with 20 mutations each
cat > large-scale.yaml << EOF
strict_parsing: false
seed_graph:
  file: seed.ttl
  type: rdf
output_graph:
  file: output/mutant.ttl
  overwrite: true
  type: rdf
number_of_mutations: 20
number_of_mutants: 100
mutation_operators:
  - resource:
      file: addRelation.ttl
      syntax: swrl
print_summary: true
EOF

# Run
docker run --rm \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/large-scale.yaml:/app/large-scale.yaml \
  -e JAVA_OPTS="-Xmx4G" \
  rdfmutate-benchmark \
  --config large-scale.yaml
```

## Advanced Usage

### Interactive Shell

Get a shell inside the container:

```bash
docker run --rm -it \
  -v $(pwd)/output:/app/output \
  --entrypoint /bin/bash \
  rdfmutate-benchmark
```

### Run Raw Java Command

```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  --entrypoint java \
  rdfmutate-benchmark \
  -jar rdfmutate-1.1.1.jar --config=config.yaml
```

## Docker Compose Advanced

### Override default command

```bash
docker-compose run --rm rdfmutate-benchmark --config custom.yaml --output-dir output
```

### Build and run in one command

```bash
docker-compose up --build
```

### Scale (run multiple instances)

```bash
# Not directly supported, but you can run multiple times:
for i in {1..5}; do
  docker-compose run --rm rdfmutate-benchmark &
done
wait
```

## Performance Tips

1. **Batch generation**: Use `number_of_mutants > 1` to amortize JVM startup
2. **Volume locality**: Keep seed/config files in the same directory
3. **Memory allocation**: Set `-Xmx` based on seed graph size
4. **Docker caching**: Rebuild only when JAR or dependencies change

## References

- [RDFMutate Documentation](https://github.com/smolang/RDFMutate/wiki)
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
