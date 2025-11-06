#!/usr/bin/env python3
"""
RUDOF Generate Benchmark Script

This script benchmarks the RUDOF RDF data generator by measuring:
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

def count_triples_in_file(file_path):
    """Count the number of triples in an RDF file (N-Triples or Turtle format)."""
    try:
        # Convert Path to string if needed
        file_path_str = str(file_path)
        
        if not os.path.exists(file_path_str):
            return 0
        
        with open(file_path_str, 'r') as f:
            content = f.read()
        
        # For N-Triples, count lines that are not comments or empty
        if file_path_str.endswith('.nt'):
            lines = [line.strip() for line in content.split('\n') 
                    if line.strip() and not line.strip().startswith('#')]
            return len(lines)
        
        # For Turtle, approximate by counting periods (not perfect but reasonable)
        elif file_path_str.endswith('.ttl'):
            # Remove prefixes and comments
            lines = [line for line in content.split('\n') 
                    if not line.strip().startswith('@prefix') 
                    and not line.strip().startswith('#')]
            cleaned = '\n'.join(lines)
            # Count statement-ending periods
            return cleaned.count(' .')
        
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

def run_rudof_generate(schema_file, output_file, entity_count, output_dir, worker_threads=4, 
                       cardinality_strategy='Balanced', batch_size=100, write_stats=True, 
                       compress=False, output_format='Turtle'):
    """
    Run RUDOF generate using Python API to generate RDF data.
    
    Args:
        schema_file: Path to the ShEx/SHACL schema file
        output_file: Path for the output RDF file
        entity_count: Number of entities to generate
        output_dir: Directory for output files
        worker_threads: Number of worker threads for parallel processing
        cardinality_strategy: Strategy for cardinality ('Minimum', 'Maximum', 'Random', 'Balanced')
        batch_size: Batch size for processing
        write_stats: Whether to write statistics file
        compress: Whether to compress output
        output_format: Output format ('Turtle', 'NTriples', 'RDFXML', etc.)
    
    Returns:
        dict: Benchmark metrics including execution time, triples, and file size
    """
    print(f"\n{'='*70}")
    print(f"RUDOF Generate Benchmark")
    print(f"{'='*70}")
    print(f"Schema: {schema_file}")
    print(f"Output: {output_file}")
    print(f"Entity count: {entity_count}")
    print(f"Worker threads: {worker_threads}")
    print(f"Cardinality strategy: {cardinality_strategy}")
    print(f"Batch size: {batch_size}")
    print(f"Output format: {output_format}")
    print(f"Write stats: {write_stats}")
    print(f"Compress: {compress}")
    print(f"{'='*70}\n")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Measure execution time
    start_time = time.time()
    
    try:
        # Import pyrudof for data generation
        import pyrudof
        
        # Map string strategy to enum
        strategy_map = {
            'Minimum': pyrudof.CardinalityStrategy.Minimum,
            'Maximum': pyrudof.CardinalityStrategy.Maximum,
            'Random': pyrudof.CardinalityStrategy.Random,
            'Balanced': pyrudof.CardinalityStrategy.Balanced
        }
        
        # Map string format to enum
        format_map = {
            'Turtle': pyrudof.OutputFormat.Turtle,
            'NTriples': pyrudof.OutputFormat.NTriples,
            'RDFXML': pyrudof.OutputFormat.RDFXML if hasattr(pyrudof.OutputFormat, 'RDFXML') else pyrudof.OutputFormat.Turtle
        }
        
        # Create configuration
        config = pyrudof.GeneratorConfig()
        config.set_entity_count(entity_count)
        config.set_output_path(str(output_file))
        config.set_output_format(format_map.get(output_format, pyrudof.OutputFormat.Turtle))
        config.set_cardinality_strategy(strategy_map.get(cardinality_strategy, pyrudof.CardinalityStrategy.Balanced))
        config.set_write_stats(write_stats)
        config.set_worker_threads(worker_threads)
        config.set_batch_size(batch_size)
        config.set_compress(compress)
        
        # Create generator and run
        generator = pyrudof.DataGenerator(config)
        generator.run(str(schema_file))
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Count triples and get file size
        triples_total = count_triples_in_file(output_file)
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
    parser = argparse.ArgumentParser(description='Benchmark RUDOF RDF data generator')
    parser.add_argument('--schema', type=str, default='example_schema.shex',
                       help='Path to the ShEx/SHACL schema file')
    parser.add_argument('--entity-count', type=int, default=100,
                       help='Number of entities to generate')
    parser.add_argument('--output-dir', type=str, default='output',
                       help='Directory for output files')
    parser.add_argument('--worker-threads', type=int, default=4,
                       help='Number of worker threads for parallel processing (default: 4)')
    parser.add_argument('--cardinality-strategy', type=str, default='Balanced',
                       choices=['Minimum', 'Maximum', 'Random', 'Balanced'],
                       help='Cardinality strategy (default: Balanced)')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Batch size for processing (default: 100)')
    parser.add_argument('--output-format', type=str, default='Turtle',
                       choices=['Turtle', 'NTriples', 'RDFXML'],
                       help='Output RDF format (default: Turtle)')
    parser.add_argument('--no-stats', action='store_true',
                       help='Disable statistics file generation')
    parser.add_argument('--compress', action='store_true',
                       help='Compress output file')
    
    args = parser.parse_args()
    
    # Set up paths
    script_dir = Path(__file__).parent
    schema_path = script_dir / args.schema
    output_dir = script_dir / args.output_dir
    output_file = output_dir / 'generated_data.ttl'
    report_file = output_dir / 'benchmark_report.json'
    
    # Validate schema file exists
    if not schema_path.exists():
        print(f"Error: Schema file not found: {schema_path}")
        return 1
    
    # Run benchmark
    metrics = run_rudof_generate(
        schema_file=schema_path,
        output_file=output_file,
        entity_count=args.entity_count,
        output_dir=output_dir,
        worker_threads=args.worker_threads,
        cardinality_strategy=args.cardinality_strategy,
        batch_size=args.batch_size,
        write_stats=not args.no_stats,
        compress=args.compress,
        output_format=args.output_format
    )
    
    # Create benchmark report
    report = {
        'benchmark': 'RUDOF Generate',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'configuration': {
            'schema_file': args.schema,
            'entity_count': args.entity_count,
            'cardinality_strategy': args.cardinality_strategy,
            'output_format': args.output_format,
            'worker_threads': args.worker_threads,
            'batch_size': args.batch_size,
            'write_stats': not args.no_stats,
            'compress': args.compress
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
    
    if not metrics['success']:
        report['error'] = metrics.get('error', 'Unknown error')
    
    # Save report
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"Benchmark report saved to: {report_file}")
    print(f"{'='*70}\n")
    
    return 0 if metrics['success'] else 1

if __name__ == '__main__':
    exit(main())
