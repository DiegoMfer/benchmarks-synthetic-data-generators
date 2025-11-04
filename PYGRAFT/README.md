# PyGraft - Synthetic Knowledge Graph Generator

Configurable generation of schemas and knowledge graphs with RDFS and OWL constructs.

## Overview

PyGraft is a Python-based generator that creates synthetic yet realistic RDF schemas and knowledge graphs. It supports:
- Schema generation with configurable class hierarchies
- Knowledge graph generation with individuals and relations
- Full pipeline (schema + KG) in one process
- Extended RDFS and OWL constructs
- Logical consistency checking via HermiT reasoner
- Domain-agnostic output suitable for benchmarking and research

## Citation

If you use PyGraft, please cite:

```bibtex
@misc{hubert2023pygraft,
  title={PyGraft: Configurable Generation of Schemas and Knowledge Graphs at Your Fingertips}, 
  author={Nicolas Hubert and Pierre Monnin and Mathieu d'Aquin and Armelle Brun and Davy Monticolo},
  year={2023},
  eprint={2309.03685},
  archivePrefix={arXiv},
  primaryClass={cs.AI}
}
```

- Paper: https://arxiv.org/pdf/2309.03685.pdf
- GitHub: https://github.com/nicolas-hbt/pygraft
- Documentation: https://pygraft.readthedocs.io/

## Quick Start

### Local Python Usage

**Prerequisites:**
- Python 3.8+
- Java 11+ (for HermiT reasoner, consistency checking)

**Install PyGraft:**
```bash
pip install pygraft
```

**Run benchmark:**
```bash
# Generate full KG with 50 classes
python3 execute_benchmark.py --mode full --n-classes 50

# Generate only schema
python3 execute_benchmark.py --mode schema --n-classes 100

# Large KG with parallel processing
python3 execute_benchmark.py --n-classes 200 --avg-instances 100 --multitask
```

### Using the Shell Script

```bash
chmod +x run-benchmark.sh
./run-benchmark.sh --mode full --n-classes 50 --n-relations 30
```

### Docker Usage

See [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed Docker instructions.

**Quick Docker run:**
```bash
docker-compose up
```

## Configuration Options

### Generation Mode

- `--mode` - What to generate:
  - `schema` - Only ontology schema (classes, properties)
  - `kg` - Knowledge graph with individuals (requires existing schema)
  - `full` - Complete pipeline: schema + KG (default)

### Core Parameters

#### Schema Parameters
- `--n-classes` - Number of classes to generate (default: 50)
- `--n-relations` - Number of object/data properties (default: 30)
- `--max-depth` - Maximum class hierarchy depth (default: 5)
- `--p-subclass` - Probability of subclass assertion (default: 0.15)
- `--p-disjoint` - Probability of disjoint classes (default: 0.05)

#### Knowledge Graph Parameters
- `--avg-instances` - Average instances per class (default: 50)
- `--std-instances` - Std deviation for instances (default: 10)
- `--avg-relations` - Average relations per individual (default: 3)
- `--std-relations` - Std deviation for relations (default: 1)

### Property Characteristics

Control OWL property axioms:
- `--p-inverse` - Inverse property probability (default: 0.2)
- `--p-functional` - Functional property (default: 0.2)
- `--p-inverse-functional` - Inverse functional (default: 0.1)
- `--p-symmetric` - Symmetric property (default: 0.1)
- `--p-asymmetric` - Asymmetric property (default: 0.05)
- `--p-transitive` - Transitive property (default: 0.1)
- `--p-reflexive` - Reflexive property (default: 0.05)
- `--p-irreflexive` - Irreflexive property (default: 0.05)
- `--p-subproperty` - Sub-property assertion (default: 0.1)

### Advanced Options

- `--check-consistency` - Enable HermiT consistency checking (default: True)
- `--no-check-consistency` - Disable consistency checking (faster)
- `--multitask` - Enable parallel processing (default: False)
- `--seed` - Random seed for reproducibility (default: 42)
- `--verbosity` - Log level: 0=minimal, 1=normal, 2=verbose (default: 1)
- `--output-dir` - Output directory (default: output)
- `--java-home` - Path to Java installation (for HermiT)

## Usage Examples

### Example 1: Small Schema
```bash
python3 execute_benchmark.py \
  --mode schema \
  --n-classes 20 \
  --n-relations 10
```

### Example 2: Medium Knowledge Graph
```bash
python3 execute_benchmark.py \
  --mode full \
  --n-classes 100 \
  --n-relations 50 \
  --avg-instances 75
```

### Example 3: Large KG with Multitasking
```bash
python3 execute_benchmark.py \
  --n-classes 200 \
  --avg-instances 150 \
  --multitask \
  --verbosity 2
```

### Example 4: Fast Generation (No Consistency Check)
```bash
python3 execute_benchmark.py \
  --n-classes 100 \
  --no-check-consistency
```

### Example 5: High Property Diversity
```bash
python3 execute_benchmark.py \
  --n-classes 80 \
  --p-functional 0.4 \
  --p-inverse 0.3 \
  --p-transitive 0.2 \
  --p-symmetric 0.2
```

### Example 6: Deep Hierarchy
```bash
python3 execute_benchmark.py \
  --n-classes 100 \
  --max-depth 10 \
  --p-subclass 0.3
```

## Output

The benchmark generates the following in `output/config/`:

1. **Schema File**: `schema.rdf`
   - OWL ontology with classes and properties
   - RDFS/OWL axioms (subclass, domain, range, etc.)
   - Property characteristics (functional, transitive, etc.)

2. **Knowledge Graph**: `full_graph.rdf` (full mode only)
   - Complete KG combining schema + individuals
   - Instances of classes with relations between them

3. **Metadata Files**:
   - `class_info.json` - Information about generated classes
   - `relation_info.json` - Information about properties

4. **Benchmark Report**: `output/benchmark_report.json`
   ```json
   {
     "benchmark": "PYGRAFT",
     "timestamp": "2025-11-04T10:30:00",
     "configuration": {
       "mode": "full",
       "n_classes": 50,
       "n_relations": 30,
       "avg_instances_per_class": 50
     },
     "execution": {
       "time_seconds": 45.67,
       "time_formatted": "45.67s"
     },
     "generated_data": {
       "files_generated": 4,
       "total_size_mb": 12.34,
       "estimated_triples": 15000
     },
     "performance": {
       "triples_per_second": 328.45
     }
   }
   ```

## Docker Setup Details

For complete Docker setup, configuration, and troubleshooting, see [DOCKER_SETUP.md](DOCKER_SETUP.md).

## Requirements

- **Python**: 3.8 or higher
- **Java**: 11 or higher (for HermiT reasoner)
- **PyGraft**: 0.0.3 or higher (`pip install pygraft`)
- **Dependencies**: owlready2, rdflib (auto-installed with PyGraft)

## Troubleshooting

### JAVA_HOME Not Set

If you see warnings about JAVA_HOME:
```bash
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64  # Linux
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-17.jdk/Contents/Home  # macOS
```

Or disable consistency checking:
```bash
python3 execute_benchmark.py --no-check-consistency
```

### Inconsistent KG Generated

PyGraft uses HermiT reasoner to check consistency. If generation fails:
1. Reduce probability parameters (lower p-functional, p-inverse-functional)
2. Reduce number of classes/relations
3. Disable specific property characteristics
4. Check Java installation

### Slow Generation

For faster generation:
- Use `--no-check-consistency` (skips HermiT reasoning)
- Enable `--multitask` for parallel processing
- Reduce `--avg-instances` or `--n-classes`
- Lower `--verbosity` to 0

### Out of Memory

For large KGs:
- Increase Docker memory limit (Docker Desktop settings)
- Use smaller `--n-classes` and `--avg-instances`
- Generate in batches (schema first, then KG)

## Performance Tips

1. **Enable multitasking** for parallel class/relation generation
2. **Disable consistency checking** for faster iteration during testing
3. **Use schema-only mode** for quick ontology design
4. **Adjust probabilities** to control complexity (lower = simpler, faster)
5. **Set reasonable seeds** for reproducible benchmarks

## License

PyGraft is licensed under the MIT License.

## Original Repository

- PyPI: https://pypi.org/project/pygraft/
- GitHub: https://github.com/nicolas-hbt/pygraft
- Authors: Nicolas Hubert, Pierre Monnin, Mathieu d'Aquin, Armelle Brun, Davy Monticolo
- Affiliation: Université de Lorraine, CNRS, LORIA
