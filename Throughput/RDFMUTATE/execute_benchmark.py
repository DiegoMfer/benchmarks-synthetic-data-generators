#!/usr/bin/env python3
"""
RDFMutate - Benchmark Execution Script
Generates synthetic RDF data through graph mutations
"""

import subprocess
import json
import time
import argparse
import re
import yaml
from datetime import datetime, timedelta
from pathlib import Path


def run_rdfmutate(config_file="config.yaml", output_dir="output", 
                  mutations=None, mutants=None, seed_file=None, operator_file=None):
    """
    Run RDFMutate generator and collect metrics
    
    Args:
        config_file: Path to YAML configuration file
        output_dir: Directory for output files
        mutations: Number of mutations to apply (overrides config)
        mutants: Number of mutants to generate (overrides config)
        seed_file: Seed graph file (overrides config)
        operator_file: Mutation operator file (overrides config)
    """
    
    # Get the directory where this script is located (RDFMUTATE directory)
    script_dir = Path(__file__).parent.resolve()
    
    # Prepare output directory (relative to script directory)
    output_path = script_dir / output_dir
    output_path.mkdir(exist_ok=True)
    
    # Load and potentially modify config
    config_path = script_dir / config_file
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Override config values if provided
    if mutations is not None:
        config['number_of_mutations'] = mutations
    if mutants is not None:
        config['number_of_mutants'] = mutants
    if seed_file is not None:
        config['seed_graph']['file'] = seed_file
    if operator_file is not None:
        if 'mutation_operators' in config and len(config['mutation_operators']) > 0:
            if 'resource' in config['mutation_operators'][0]:
                config['mutation_operators'][0]['resource']['file'] = operator_file
    
    # Create temporary config file with overrides
    temp_config_path = script_dir / "temp_config.yaml"
    with open(temp_config_path, 'w') as f:
        yaml.dump(config, f)
    
    # Find the JAR file
    jar_files = list(script_dir.glob("rdfmutate*.jar"))
    if not jar_files:
        raise FileNotFoundError("RDFMutate JAR file not found")
    jar_file = jar_files[0]
    
    # Build command
    cmd = [
        "java",
        "-jar", str(jar_file),
        f"--config={temp_config_path}"
    ]
    
    print(f"Running RDFMutate Generator...")
    print(f"JAR: {jar_file.name}")
    print(f"Config: {config_file}")
    if mutations is not None:
        print(f"Mutations (override): {mutations}")
    if mutants is not None:
        print(f"Mutants (override): {mutants}")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)
    
    # Run generator
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd=script_dir
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Clean up temporary config
        if temp_config_path.exists():
            temp_config_path.unlink()
        
        # Parse output to extract metrics
        metrics = parse_generator_output(result.stdout)
        
        # Print summary
        print("\n" + "=" * 60)
        print("✅ RDFMutate Generation Complete!")
        print("=" * 60)
        print(f"⏱️  Execution Time: {execution_time:.3f} seconds")
        print(f"🔄 Mutations Applied: {metrics.get('num_mutations', 'N/A')}")
        print(f"➕ Axioms Added: {metrics.get('num_add', 'N/A')}")
        print(f"➖ Axioms Deleted: {metrics.get('num_del', 'N/A')}")
        print(f"📁 Output Location: {output_path}")
        if metrics.get('affected_nodes'):
            print(f"🎯 Affected Nodes: {metrics['affected_nodes']}")
        print("=" * 60)
        
        # Create detailed report
        report = create_benchmark_report(
            config_file, execution_time, metrics, result.stdout
        )
        
        # Save report
        report_path = output_path / "benchmark_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Detailed report saved to: {report_path}")
        
        return report
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running RDFMutate generator:")
        print(f"Exit code: {e.returncode}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        raise


def parse_generator_output(output):
    """Parse RDFMutate output to extract metrics"""
    metrics = {}
    
    # Look for mutation summary line
    # Format: "numMutations;numDel;numAdd;appliedMutations;affectedSeedNodes"
    # Example: "1;0;1;[RuleMutation(...)];[bob,alice]"
    
    summary_pattern = r'(\d+);(\d+);(\d+);(\[.*?\]);(\[.*?\])'
    match = re.search(summary_pattern, output)
    
    if match:
        metrics['num_mutations'] = int(match.group(1))
        metrics['num_del'] = int(match.group(2))
        metrics['num_add'] = int(match.group(3))
        metrics['applied_mutations'] = match.group(4)
        metrics['affected_nodes'] = match.group(5)
    
    # Count mutation operations from logs
    mutation_lines = [line for line in output.split('\n') if 'applying mutation' in line.lower()]
    if mutation_lines:
        metrics['mutation_operations'] = len(mutation_lines)
    
    # Look for saving output message
    save_match = re.search(r'Saving.*?to (.+)', output)
    if save_match:
        metrics['output_file'] = save_match.group(1).strip()
    
    return metrics


def create_benchmark_report(config_file, execution_time, metrics, raw_output):
    """Create a comprehensive benchmark report"""
    
    report = {
        "benchmark": "RDFMutate",
        "version": "1.1.1",
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "config_file": config_file
        },
        "execution": {
            "time_seconds": round(execution_time, 3),
            "time_milliseconds": round(execution_time * 1000, 3),
            "time_formatted": str(timedelta(seconds=execution_time))
        },
        "mutations": {
            "total_mutations": metrics.get('num_mutations', 0),
            "axioms_added": metrics.get('num_add', 0),
            "axioms_deleted": metrics.get('num_del', 0),
            "net_change": metrics.get('num_add', 0) - metrics.get('num_del', 0)
        },
        "performance_metrics": {
            "mutations_per_second": round(
                metrics.get('num_mutations', 0) / execution_time, 2
            ) if execution_time > 0 else 0,
            "axioms_per_second": round(
                (metrics.get('num_add', 0) + metrics.get('num_del', 0)) / execution_time, 2
            ) if execution_time > 0 else 0
        },
        "output": {
            "file": metrics.get('output_file', 'N/A'),
            "affected_nodes": metrics.get('affected_nodes', '[]')
        }
    }
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description="RDFMutate Benchmark - Generate synthetic RDF data through mutations"
    )
    
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to configuration YAML file (default: config.yaml)"
    )
    
    parser.add_argument(
        "-o", "--output-dir",
        default="output",
        help="Output directory for generated files (default: output)"
    )
    
    parser.add_argument(
        "-m", "--mutations",
        type=int,
        help="Number of mutations to apply (overrides config)"
    )
    
    parser.add_argument(
        "-n", "--mutants",
        type=int,
        help="Number of mutant graphs to generate (overrides config)"
    )
    
    parser.add_argument(
        "-s", "--seed",
        help="Seed graph file path (overrides config)"
    )
    
    parser.add_argument(
        "-op", "--operator",
        help="Mutation operator file path (overrides config)"
    )
    
    args = parser.parse_args()
    
    try:
        report = run_rdfmutate(
            config_file=args.config,
            output_dir=args.output_dir,
            mutations=args.mutations,
            mutants=args.mutants,
            seed_file=args.seed,
            operator_file=args.operator
        )
        
        print("\n✨ Benchmark execution completed successfully!")
        
    except Exception as e:
        print(f"\n💥 Benchmark execution failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
