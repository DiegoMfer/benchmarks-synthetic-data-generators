# RDFMutate Benchmark - Docker Setup

## LINK to the tool
https://github.com/smolang/RDFMutate
- Wiki: https://github.com/smolang/RDFMutate/wiki
- Releases: https://github.com/smolang/RDFMutate/releases

## What is RDFMutate?

**RDFMutate** is a tool for generating synthetic RDF data through controlled mutations of seed graphs. It applies mutation operators (defined via SWRL rules or SHACL shapes) to transform an initial RDF graph into new variants. This is useful for:
- Testing RDF processing systems
- Generating diverse test datasets
- Evaluating reasoning engines
- Creating controlled variations of ontologies

## Quick Start

### 1. Build the Docker Image

```bash
./build-docker.sh
```

Or manually:
```bash
docker build -t rdfmutate-benchmark .
```

### 2. Run the Benchmark

**Easy way** (using the run script):
```bash
# Run with default config
./run-benchmark.sh

# Run with custom config
./run-benchmark.sh my-config.yaml
```

**Docker way**:
```bash
# Run with default configuration
docker run --rm -v $(pwd)/output:/app/output rdfmutate-benchmark

# Run with custom config
docker run --rm -v $(pwd)/output:/app/output rdfmutate-benchmark --config my-config.yaml
```

**Docker Compose way**:
```bash
docker-compose run --rm rdfmutate-benchmark
docker-compose run --rm rdfmutate-benchmark --config my-config.yaml
```

**Native Python way** (requires Java 17):
```bash
# Run with default config
python3 execute_benchmark.py

# Run with custom config
python3 execute_benchmark.py --config my-config.yaml
```

## Output

All generated files are saved to the `./output` directory:
- `mutated.ttl` (or other format depending on config) - Generated RDF graph
- `benchmark_report.json` - Detailed metrics and performance data

## Configuration

RDFMutate uses YAML configuration files. The default `config.yaml` includes:

### Key Configuration Elements

```yaml
strict_parsing: false

seed_graph:
  file: seed.ttl          # Input RDF graph
  type: rdf               # Type: rdf or owl

output_graph:
  file: output/mutated.ttl  # Output path
  overwrite: true          # Overwrite existing files
  type: rdf               # Output type

number_of_mutations: 1    # How many mutations to apply
number_of_mutants: 1      # How many mutant graphs to generate

mutation_operators:
  - resource:
      file: addRelation.ttl  # SWRL rule file
      syntax: swrl           # Syntax: swrl or shacl
  # Or use built-in operators:
  # - module:
  #     location: org.smolang.robust.mutant.operators
  #     operators:
  #       - className: AddSubclassRelationMutation

print_summary: true       # Print mutation summary
```

### Supported Formats
- **Input/Output types**: `rdf` (Turtle, N-Triples, etc.) or `owl` (OWL functional syntax)
- **Mutation operators**: SWRL rules or SHACL shapes

### Scale Parameters
- `number_of_mutations`: Controls how many mutation operations to apply
- `number_of_mutants`: Generate multiple variants in one run (more efficient)

## Examples

### Example 1: Basic Mutation
```bash
# Uses default config (1 mutation, 1 mutant)
./run-benchmark.sh
```

### Example 2: Multiple Mutations
Create a config with `number_of_mutations: 10`:
```yaml
number_of_mutations: 10
number_of_mutants: 1
```

### Example 3: Batch Generation
Generate 100 mutants at once (efficient):
```yaml
number_of_mutations: 5
number_of_mutants: 100
```

### Example 4: Using Built-in Operators
```yaml
mutation_operators:
  - module:
      location: org.smolang.robust.mutant.operators
      operators:
        - className: AddSubclassRelationMutation
        - className: AddObjectPropertyRelationMutation
        - className: DeclareClassMutation
```

## Custom Configurations

### Create Your Own Seed Graph
1. Create a TTL file with your initial RDF data
2. Update `seed_graph.file` in config.yaml

### Create Custom Mutation Operators (SWRL)
See the [RDFMutate Wiki](https://github.com/smolang/RDFMutate/wiki/Examples) for examples.

Basic SWRL rule template:
```turtle
@prefix : <http://example.org/> .
@prefix swrl: <http://www.w3.org/2003/11/swrl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

:x rdf:type swrl:Variable .
:y rdf:type swrl:Variable .

[ rdf:type swrl:Imp ;
  swrl:body [ ... ] ;   # Condition: when to apply
  swrl:head [ ... ]     # Action: what to add/remove
].
```

## Performance Notes

- **JVM Startup**: First run includes ~1s JVM startup overhead
- **Batch Generation**: Use `number_of_mutants > 1` to amortize startup cost
- **Memory**: Default 2GB heap should handle most cases
- **Parallelization**: Generate mutants sequentially; run multiple containers for parallel execution

## Requirements

### Native Execution
- Java 17 or higher
- Python 3.7+ (for benchmark script)

### Docker Execution
- Docker (any recent version)
- Docker Compose (optional)

## Troubleshooting

### Java Version Mismatch
RDFMutate requires Java 17. If you see version errors:
```bash
# Check Java version
java -version

# Should show: openjdk version "17.x.x"
```

### File Not Found Errors
Ensure paths in config.yaml are relative to the working directory:
```yaml
seed_graph:
  file: seed.ttl  # NOT /app/seed.ttl
```

### Permission Errors (Docker)
The run script uses your user ID:
```bash
docker run --rm -v $(pwd)/output:/app/output -u $(id -u):$(id -g) rdfmutate-benchmark
```

## Learn More

- **Full Documentation**: https://github.com/smolang/RDFMutate/wiki
- **Mutation Operators**: https://github.com/smolang/RDFMutate/wiki/List-of-Mutation-Operators
- **Configuration Guide**: https://github.com/smolang/RDFMutate/wiki/User-Documentation
- **SWRL Examples**: https://github.com/smolang/RDFMutate/wiki/Examples
