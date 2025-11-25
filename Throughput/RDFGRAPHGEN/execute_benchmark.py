#!/usr/bin/env python3
"""
RDFGraphGen - Benchmark Execution Script
Generates synthetic RDF data from SHACL shapes
"""

import subprocess
import json
import time
import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path


def run_rdfgraphgen(shape_file="input-shape.ttl", output_file="output-graph.ttl", 
                    scale_factor=100, output_dir="output"):
    """
    Run RDFGraphGen and collect metrics
    
    Args:
        shape_file: Path to SHACL shape file
        output_file: Output RDF graph filename
        scale_factor: Determines the size of the generated RDF graph
        output_dir: Directory for output files
    """
    
    # Get the directory where this script is located (RDFGRAPHGEN directory)
    script_dir = Path(__file__).parent.resolve()
    
    # Prepare output directory
    output_path = script_dir / output_dir
    output_path.mkdir(exist_ok=True)
    
    # Full paths
    shape_path = script_dir / shape_file
    output_full_path = output_path / output_file
    
    if not shape_path.exists():
        raise FileNotFoundError(f"Shape file not found: {shape_path}")
    
    # Build command
    cmd = [
        "rdfgen",
        str(shape_path),
        str(output_full_path),
        str(scale_factor)
    ]
    
    print(f"Running RDFGraphGen...")
    print(f"Shape file: {shape_file}")
    print(f"Output file: {output_full_path}")
    print(f"Scale factor: {scale_factor}")
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
        
        # Count triples in output
        triples_count = count_triples(output_full_path)
        file_size_mb = output_full_path.stat().st_size / (1024 * 1024)
        
        # Print summary
        print("\n" + "=" * 60)
        print("✅ RDFGraphGen Generation Complete!")
        print("=" * 60)
        print(f"⏱️  Execution Time: {execution_time:.3f} seconds")
        print(f"📈 Scale Factor: {scale_factor}")
        print(f"🔢 Total Triples: {triples_count:,}")
        print(f"⚡ Triples/sec: {triples_count / execution_time:,.0f}")
        print(f"📁 Output File: {output_full_path}")
        print(f"💾 File Size: {file_size_mb:.2f} MB")
        print("=" * 60)
        
        # Create detailed report
        report = create_benchmark_report(
            shape_file, scale_factor, execution_time, 
            triples_count, file_size_mb, output_file
        )
        
        # Save report
        report_path = output_path / "benchmark_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Detailed report saved to: {report_path}")
        
        return report
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running RDFGraphGen:")
        print(f"Exit code: {e.returncode}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        raise
    except FileNotFoundError as e:
        print(f"\n❌ Error: RDFGraphGen not found!")
        print(f"Please install it first: pip install rdf-graph-gen")
        raise


def count_triples(ttl_file_path):
    """Count triples in a Turtle file"""
    try:
        with open(ttl_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count lines that look like triples (contain a period at the end)
        lines = content.split('\n')
        triple_count = 0
        
        for line in lines:
            line = line.strip()
            # Skip comments and prefixes
            if line and not line.startswith('#') and not line.startswith('@'):
                # Count lines ending with . or lines with predicate-object patterns
                if line.endswith('.') or line.endswith(';'):
                    triple_count += 1
        
        return triple_count
        
    except Exception as e:
        print(f"Warning: Could not count triples: {e}")
        return 0


def create_benchmark_report(shape_file, scale_factor, execution_time, 
                           triples_count, file_size_mb, output_file):
    """Create a comprehensive benchmark report"""
    
    report = {
        "benchmark": "RDFGraphGen",
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "shape_file": shape_file,
            "scale_factor": scale_factor,
            "output_file": output_file
        },
        "execution": {
            "time_seconds": round(execution_time, 3),
            "time_milliseconds": round(execution_time * 1000, 3),
            "time_formatted": str(timedelta(seconds=execution_time))
        },
        "generated_data": {
            "triples_total": triples_count,
            "file_size_mb": round(file_size_mb, 2),
            "triples_per_mb": round(triples_count / file_size_mb, 2) if file_size_mb > 0 else 0
        },
        "performance_metrics": {
            "triples_per_second": round(triples_count / execution_time, 2) if execution_time > 0 else 0
        }
    }
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description="RDFGraphGen Benchmark - Generate RDF data from SHACL shapes"
    )
    
    parser.add_argument(
        "-s", "--shape",
        default="input-shape.ttl",
        help="Path to SHACL shape file (default: input-shape.ttl)"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="output-graph.ttl",
        help="Output RDF graph filename (default: output-graph.ttl)"
    )
    
    parser.add_argument(
        "-f", "--scale-factor",
        type=int,
        default=100,
        help="Scale factor for graph size (default: 100)"
    )
    
    parser.add_argument(
        "-d", "--output-dir",
        default="output",
        help="Output directory (default: output)"
    )
    
    args = parser.parse_args()
    
    try:
        report = run_rdfgraphgen(
            shape_file=args.shape,
            output_file=args.output,
            scale_factor=args.scale_factor,
            output_dir=args.output_dir
        )
        
        print("\n✨ Benchmark execution completed successfully!")
        
    except Exception as e:
        print(f"\n💥 Benchmark execution failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
