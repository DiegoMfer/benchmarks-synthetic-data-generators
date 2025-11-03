#!/usr/bin/env python3
"""
BSBM (Berlin SPARQL Benchmark) Generator - Benchmark Execution Script
Generates synthetic RDF data for benchmarking SPARQL databases
"""

import subprocess
import json
import time
import argparse
from datetime import datetime
from pathlib import Path


def run_bsbm_generator(products=1000, format_type="ttl", forward_chaining=True, 
                       output_name="dataset", output_dir="output"):
    """
    Run BSBM generator and collect metrics
    
    Args:
        products: Number of products to generate
        format_type: Output format (ttl, nt, n3, trig)
        forward_chaining: Enable forward chaining/reasoning
        output_name: Base name for output files
        output_dir: Directory for output files
    """
    
    # Get the directory where this script is located (BSBM directory)
    script_dir = Path(__file__).parent.resolve()
    
    # Prepare output directory (relative to script directory)
    output_path = script_dir / output_dir
    output_path.mkdir(exist_ok=True)
    
    # Build command (use relative path since we run from script_dir)
    cmd = [
        "java", "-cp", "bsbm.jar:ssj.jar",
        "-Xmx2G",
        "benchmark.generator.Generator",
        "-pc", str(products),
        "-s", format_type,
        "-fn", f"{output_dir}/{output_name}"
    ]
    
    if forward_chaining:
        cmd.append("-fc")
    
    print(f"Running BSBM Generator...")
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
        
        # Parse output to extract metrics
        output_lines = result.stdout.split('\n')
        metrics = parse_generator_output(output_lines)
        
        # Print summary
        print("\n" + "=" * 60)
        print("✅ BSBM Generation Complete!")
        print("=" * 60)
        print(f"⏱️  Execution Time: {execution_time:.2f} seconds")
        print(f"📦 Products Generated: {metrics.get('products', products)}")
        print(f"🔢 Total Triples: {metrics.get('triples', 'N/A'):,}")
        print(f"⚡ Triples/sec: {metrics.get('triples', 0) / execution_time:,.0f}")
        print(f"📁 Output Format: {format_type.upper()}")
        print(f"📂 Output Location: {output_path / output_name}.{format_type}")
        print("=" * 60)
        
        # Create detailed report
        report = create_benchmark_report(
            products, format_type, forward_chaining, 
            execution_time, metrics, output_name
        )
        
        # Save report
        report_path = output_path / "benchmark_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Detailed report saved to: {report_path}")
        
        return report
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running BSBM generator:")
        print(f"Exit code: {e.returncode}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        raise


def parse_generator_output(lines):
    """Parse BSBM generator output to extract metrics"""
    metrics = {}
    
    for line in lines:
        line = line.strip()
        
        # Extract number of products
        if "Products have been generated" in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if "Products" in part and i > 0:
                    try:
                        metrics['products'] = int(parts[i-1])
                    except ValueError:
                        pass
        
        # Extract producers
        if "Producers and" in line:
            parts = line.split()
            try:
                metrics['producers'] = int(parts[0])
            except ValueError:
                pass
        
        # Extract vendors and offers
        if "Vendors and" in line and "Offers" in line:
            parts = line.split()
            try:
                metrics['vendors'] = int(parts[0])
                # Find offers number
                for i, part in enumerate(parts):
                    if "Offers" in part and i > 0:
                        metrics['offers'] = int(parts[i-1])
            except ValueError:
                pass
        
        # Extract rating sites and reviews
        if "Rating Sites with" in line:
            parts = line.split()
            try:
                metrics['rating_sites'] = int(parts[0])
                # Find persons and reviews
                if "Persons and" in line:
                    for i, part in enumerate(parts):
                        if "Persons" in part and i > 0:
                            metrics['reviewers'] = int(parts[i-1])
                        if "Reviews" in part and i > 0:
                            metrics['reviews'] = int(parts[i-1])
            except ValueError:
                pass
        
        # Extract total triples
        if "triples generated" in line:
            parts = line.split()
            try:
                metrics['triples'] = int(parts[0])
            except ValueError:
                pass
        
        # Extract product types
        if "Product Types generated" in line:
            parts = line.split()
            try:
                metrics['product_types'] = int(parts[0])
            except ValueError:
                pass
        
        # Extract product features
        if "Product Features generated" in line:
            parts = line.split()
            try:
                metrics['product_features'] = int(parts[0])
            except ValueError:
                pass
    
    return metrics


def create_benchmark_report(products, format_type, forward_chaining, 
                           execution_time, metrics, output_name):
    """Create a comprehensive benchmark report"""
    
    report = {
        "benchmark": "BSBM",
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "products": products,
            "format": format_type,
            "forward_chaining": forward_chaining,
            "output_name": output_name
        },
        "execution": {
            "time_seconds": round(execution_time, 3),
            "time_formatted": f"{execution_time:.2f}s"
        },
        "generated_data": {
            "triples_total": metrics.get('triples', 0),
            "triples_per_second": round(metrics.get('triples', 0) / execution_time, 2) if execution_time > 0 else 0,
        },
        "entities": {
            "products": metrics.get('products', products),
            "producers": metrics.get('producers', 0),
            "vendors": metrics.get('vendors', 0),
            "offers": metrics.get('offers', 0),
            "rating_sites": metrics.get('rating_sites', 0),
            "reviewers": metrics.get('reviewers', 0),
            "reviews": metrics.get('reviews', 0),
            "product_types": metrics.get('product_types', 0),
            "product_features": metrics.get('product_features', 0)
        }
    }
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description="BSBM Benchmark Generator - Generate synthetic RDF e-commerce data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 1000 products in Turtle format:
  python3 execute_benchmark.py --products 1000
  
  # Generate 100000 products in N-Triples format:
  python3 execute_benchmark.py --products 100000 --format nt
  
  # Generate without forward chaining:
  python3 execute_benchmark.py --products 5000 --no-fc
        """
    )
    
    parser.add_argument(
        "-p", "--products",
        type=int,
        default=1000,
        help="Number of products to generate (default: 1000)"
    )
    
    parser.add_argument(
        "-f", "--format",
        type=str,
        default="ttl",
        choices=["ttl", "nt", "n3", "trig"],
        help="Output format (default: ttl for Turtle)"
    )
    
    parser.add_argument(
        "--no-fc",
        action="store_true",
        help="Disable forward chaining (reasoning)"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="dataset",
        help="Base name for output files (default: dataset)"
    )
    
    parser.add_argument(
        "-d", "--output-dir",
        type=str,
        default="output",
        help="Output directory (default: output)"
    )
    
    args = parser.parse_args()
    
    # Run benchmark
    run_bsbm_generator(
        products=args.products,
        format_type=args.format,
        forward_chaining=not args.no_fc,
        output_name=args.output,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()
