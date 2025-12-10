#!/usr/bin/env python3
"""
RUDOF Generate Binary Benchmark Script

This script benchmarks the RUDOF binary RDF data generator by measuring:
- Execution time
- Number of triples generated
- Output file size
- Memory usage
"""

import subprocess
import json
import time
import argparse
from pathlib import Path
import os


def count_triples_from_stats(stats_file_path):
    """Count the number of triples from RUDOF Generate stats file."""
    try:
        # Convert Path to string if needed
        stats_file_str = str(stats_file_path)
        
        if not os.path.exists(stats_file_str):
            print(f"Warning: Stats file not found at {stats_file_str}")
            return 0
        
        with open(stats_file_str, 'r') as f:
            stats = json.load(f)
        
        # Get total_triples from stats
        return stats.get('total_triples', 0)
        
    except Exception as e:
        print(f"Warning: Could not read triples from stats file {stats_file_path}: {e}")
        return 0

def count_triples_from_file(file_path):
    """Count triples using basic parsing as fallback."""
    try:
        file_path_str = str(file_path)
        
        if not os.path.exists(file_path_str):
            return 0
        
        with open(file_path_str, 'r') as f:
            content = f.read()
        
        # For Turtle format - count complete statements (ending with .)
        if file_path_str.endswith('.ttl'):
            # Remove prefixes and comments
            lines = [line for line in content.split('\n') 
                    if not line.strip().startswith('@prefix') 
                    and not line.strip().startswith('#')
                    and line.strip()]
            # Count subject blocks (lines ending with .)
            statements = len([line for line in lines if line.strip().endswith('.')])
            return statements
        
        # For N-Triples format - count lines
        elif file_path_str.endswith('.nt'):
            lines = [line.strip() for line in content.split('\n') 
                    if line.strip() and not line.strip().startswith('#')]
            return len(lines)
        
        return 0
    except Exception as e:
        print(f"Warning: Could not count triples in {file_path}: {e}")
        return 0

def get_file_size_mb(file_path):
    """Get file size in megabytes."""
    try:
        if os.path.exists(file_path):
            return os.path.getsize(file_path) / (1024 * 1024)
        return 0.0
    except Exception as e:
        print(f"Warning: Could not get file size for {file_path}: {e}")
        return 0.0

def run_rudof_generate_binary(schema_file, output_file, entity_count, output_dir, 
                             output_format='turtle', seed=None, parallel_threads=None, config_file=None):
    """
    Run RUDOF binary to generate RDF data.
    
    Args:
        schema_file: Path to the ShEx/SHACL schema file
        output_file: Path for the output RDF file
        entity_count: Number of entities to generate
        output_dir: Directory for output files
        output_format: Output format ('turtle', 'ntriples', 'rdfxml', 'trig', 'n3', 'nquads', 'jsonld')
        seed: Random seed for reproducible generation
        parallel_threads: Number of parallel threads
        config_file: Path to configuration file
    """
    print(f"\n{'='*70}")
    print(f"RUDOF Generate Binary Benchmark")
    print(f"{'='*70}")
    print(f"Schema: {schema_file}")
    print(f"Output: {output_file}")
    if config_file:
        print(f"Config file: {config_file}")
    if entity_count:
        print(f"Entity count: {entity_count}")
    print(f"Output format: {output_format}")
    print(f"Seed: {seed}")
    print(f"Parallel threads: {parallel_threads}")
    print(f"{'='*70}\n")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Prepare RUDOF command
    rudof_cmd = [
        'rudof', 'generate',
        '--schema', str(schema_file),
        '--output-file', str(output_file),
        '--result-format', output_format.lower()
    ]
    
    if config_file:
        rudof_cmd.extend(['--config', str(config_file)])
    
    # Add optional parameters (only if provided)
    if entity_count is not None:
        rudof_cmd.extend(['--entities', str(entity_count)])
        
    if seed is not None:
        rudof_cmd.extend(['--seed', str(seed)])
    
    if parallel_threads is not None:
        rudof_cmd.extend(['--parallel', str(parallel_threads)])
    
    print(f"Running command: {' '.join(rudof_cmd)}")
    
    # Measure execution time
    start_time = time.time()
    
    try:
        # Run RUDOF binary
        result = subprocess.run(
            rudof_cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"RUDOF stdout: {result.stdout}")
        if result.stderr:
            print(f"RUDOF stderr: {result.stderr}")
        
        # Count triples - try stats file first, then fallback to parsing
        # Stats file is named: <base_name>.stats.json (e.g., generated_data.stats.json)
        stats_file = output_file.with_suffix('.stats.json')
        if stats_file.exists():
            triples_total = count_triples_from_stats(stats_file)
            if triples_total == 0:
                print(f"Warning: Stats file exists but returned 0 triples, trying fallback parsing...")
                triples_total = count_triples_from_file(output_file)
        else:
            print(f"Warning: Stats file not found at {stats_file}, using fallback parsing...")
            # Fallback to parsing the output file
            triples_total = count_triples_from_file(output_file)
        
        file_size_mb = get_file_size_mb(output_file)
        
        # Calculate triples per second
        triples_per_second = triples_total / execution_time if execution_time > 0 else 0
        
        print(f"\n✓ Generation completed successfully!")
        print(f"  Execution time: {execution_time:.3f} seconds")
        print(f"  Total triples: {triples_total:,}")
        print(f"  Output size: {file_size_mb:.2f} MB")
        print(f"  Triples/second: {triples_per_second:,.2f}")
        
        return {
            'success': True,
            'execution_time': execution_time,
            'triples_total': triples_total,
            'file_size_mb': file_size_mb,
            'triples_per_second': triples_per_second
        }
        
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n✗ Generation failed!")
        print(f"  Error: {e}")
        print(f"  Exit code: {e.returncode}")
        print(f"  Stdout: {e.stdout}")
        print(f"  Stderr: {e.stderr}")
        print(f"  Execution time: {execution_time:.3f} seconds")
        
        return {
            'success': False,
            'execution_time': execution_time,
            'error': str(e),
            'triples_total': 0,
            'file_size_mb': 0.0,
            'triples_per_second': 0.0
        }
    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n✗ Generation failed!")
        print(f"  Error: {str(e)}")
        print(f"  Execution time: {execution_time:.3f} seconds")
        
        return {
            'success': False,
            'execution_time': execution_time,
            'error': str(e),
            'triples_total': 0,
            'file_size_mb': 0.0,
            'triples_per_second': 0.0
        }

def main():
    parser = argparse.ArgumentParser(description='Benchmark RUDOF binary RDF data generator')
    parser.add_argument('--schema', type=str, default='example_schema.shex',
                       help='Path to the ShEx/SHACL schema file')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to configuration file')
    parser.add_argument('--entity-count', type=int, default=None,
                       help='Number of entities to generate (default: 100 if no config)')
    parser.add_argument('--output-dir', type=str, default='output',
                       help='Directory for output files')
    parser.add_argument('--output-format', type=str, default='turtle',
                       choices=['turtle', 'ntriples', 'rdfxml', 'trig', 'n3', 'nquads', 'jsonld'],
                       help='Output RDF format (default: turtle)')
    parser.add_argument('--seed', type=int, default=None,
                       help='Random seed for reproducible generation')
    parser.add_argument('--parallel-threads', type=int, default=None,
                       help='Number of parallel threads')
    
    args = parser.parse_args()
    
    # Set up paths
    script_dir = Path(__file__).parent
    schema_path = script_dir / args.schema
    output_dir = script_dir / args.output_dir
    
    # Handle default entity count if not provided and no config
    entity_count = args.entity_count
    
    # If config file is provided, try to read entity_count from it
    if args.config and entity_count is None:
        try:
            config_path = script_dir / args.config
            if config_path.exists():
                # Simple TOML parsing for entity_count to avoid dependencies
                with open(config_path, "r") as f:
                    in_generation = False
                    for line in f:
                        line = line.strip()
                        if line == "[generation]":
                            in_generation = True
                            continue
                        elif line.startswith("["):
                            in_generation = False
                            continue
                        
                        if in_generation and (line.startswith("entity_count") or line.startswith("entities")):
                            parts = line.split("=")
                            if len(parts) >= 2:
                                val = parts[1].split("#")[0].strip()
                                entity_count = int(val)
                                print(f"Read entity_count from config: {entity_count}")
                                break
        except Exception as e:
            print(f"Warning: Could not read config file: {e}")

    if entity_count is None:
        entity_count = 100
    
    # Determine output file extension based on format
    format_extensions = {
        'turtle': '.ttl',
        'ntriples': '.nt', 
        'rdfxml': '.rdf',
        'trig': '.trig',
        'n3': '.n3',
        'nquads': '.nq',
        'jsonld': '.jsonld'
    }
    
    extension = format_extensions.get(args.output_format.lower(), '.ttl')
    output_file = output_dir / f'generated_data{extension}'
    report_file = output_dir / 'benchmark_report.json'
    
    # Validate schema file exists
    if not schema_path.exists():
        print(f"Error: Schema file not found: {schema_path}")
        return 1
    
    # Run benchmark
    metrics = run_rudof_generate_binary(
        schema_file=schema_path,
        output_file=output_file,
        entity_count=entity_count,
        output_dir=output_dir,
        output_format=args.output_format,
        seed=args.seed,
        parallel_threads=args.parallel_threads,
        config_file=args.config
    )
    
    # Create benchmark report
    report = {
        'benchmark': 'RUDOF Generate (Binary)',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'configuration': {
            'schema_file': args.schema,
            'config_file': args.config,
            'entity_count': entity_count,
            'output_format': args.output_format,
            'seed': args.seed,
            'parallel_threads': args.parallel_threads,
        },
        'execution': {
            'time_seconds': metrics['execution_time'],
            'success': metrics['success']
        },
        'generated_data': {
            'triples_total': metrics['triples_total'],
            'file_size_mb': metrics['file_size_mb'],
            'output_file': str(output_file.name)
        },
        'performance_metrics': {
            'triples_per_second': metrics['triples_per_second']
        }
    }
    
    # Add error information if generation failed
    if not metrics['success']:
        report['error'] = metrics.get('error', 'Unknown error')
    
    # Save benchmark report
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"Benchmark report saved to: {report_file}")
    print(f"{'='*70}")
    
    return 0 if metrics['success'] else 1

if __name__ == "__main__":
    exit(main())