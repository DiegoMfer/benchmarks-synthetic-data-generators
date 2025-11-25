#!/usr/bin/env python3
"""
Script to execute the LUBM (Lehigh University Benchmark) generator
"""

import subprocess
import os
import sys
import argparse
import time
import json
from pathlib import Path
from datetime import datetime, timedelta

def parse_triples_from_output(output_text):
    """
    Parse the number of class and property instances (triples) from LUBM output
    
    Args:
        output_text (str): The stdout from LUBM generator
    
    Returns:
        dict: Dictionary with class_instances and property_instances counts
    """
    import re
    
    triples = {
        "class_instances": 0,
        "property_instances": 0,
        "total_triples": 0
    }
    
    # Look for the final counts in the output
    # Format: "CLASS INSTANCE #: 1147, TOTAL SO FAR: 20659"
    class_match = re.findall(r'CLASS INSTANCE #: \d+, TOTAL SO FAR: (\d+)', output_text)
    if class_match:
        triples["class_instances"] = int(class_match[-1])
    
    # Format: "PROPERTY INSTANCE #: 4321, TOTAL SO FAR: 82415"
    property_match = re.findall(r'PROPERTY INSTANCE #: \d+, TOTAL SO FAR: (\d+)', output_text)
    if property_match:
        triples["property_instances"] = int(property_match[-1])
    
    triples["total_triples"] = triples["class_instances"] + triples["property_instances"]
    
    return triples


def execute_lubm_generator(univ_num=1, starting_index=0, seed=0, ontology_url=None, output_format="owl"):
    """
    Execute the LUBM generator with specified parameters
    
    Args:
        univ_num (int): Number of universities to generate (default: 1)
        starting_index (int): Starting index of universities (default: 0)
        seed (int): Seed for random data generation (default: 0)
        ontology_url (str): URL of the univ-bench ontology (required)
        output_format (str): Output format - "owl" or "daml" (default: "owl")
    
    Returns:
        tuple: (success: bool, execution_time: float, triples: dict) - Success status, execution time, and triples info
    """
    
    # Path to the LUBM generator jar file
    jar_path = Path(__file__).parent / "lubm-generator-fixed.jar"
    
    if not jar_path.exists():
        print(f"Error: LUBM generator jar file not found at {jar_path}")
        return False, 0, {}
    
    # Set up output directory
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Build the command
    cmd = [
        "java",
        "-cp", str(jar_path),
        "edu.lehigh.swat.bench.uba.Generator",
        "-univ", str(univ_num),
        "-index", str(starting_index),
        "-seed", str(seed)
    ]
    
    # Add format option
    if output_format.lower() == "daml":
        cmd.append("-daml")
    
    # Add ontology URL (required)
    if ontology_url:
        cmd.extend(["-onto", ontology_url])
    else:
        print("Error: Ontology URL is required")
        return False, 0, {}
    
    print(f"Executing LUBM generator with command:")
    print(" ".join(cmd))
    print()
    
    try:
        # Measure execution time
        start_time = time.time()
        
        # Execute the command in the output directory so files are generated there
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(output_dir))
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Parse triples from output
        triples = parse_triples_from_output(result.stdout) if result.stdout else {}
        
        if result.returncode == 0:
            print(f"LUBM generator executed successfully in {execution_time:.6f} seconds ({execution_time * 1000:.3f}ms)!")
            if result.stdout:
                print("Output:")
                print(result.stdout)
        else:
            print("Error executing LUBM generator:")
            print(f"Return code: {result.returncode}")
            if result.stderr:
                print("Error output:")
                print(result.stderr)
            if result.stdout:
                print("Standard output:")
                print(result.stdout)
        
        return result.returncode == 0, execution_time, triples
        
    except FileNotFoundError:
        print("Error: Java not found. Please make sure Java is installed and in your PATH.")
        return False, 0, {}
    except Exception as e:
        print(f"Error executing LUBM generator: {e}")
        return False, 0, {}

def generate_report(config, execution_time, triples, output_file="benchmark_report.json"):
    """
    Generate a comprehensive benchmark report
    
    Args:
        config (dict): Configuration parameters used for generation
        execution_time (float): Time taken to generate the dataset in seconds
        triples (dict): Triples (class and property instances) information
        output_file (str): Output filename for the report
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "universities": config["universities"],
            "starting_index": config["starting_index"],
            "seed": config["seed"],
            "format": config["format"]
        },
        "execution": {
            "time_seconds": round(execution_time, 6),
            "time_milliseconds": round(execution_time * 1000, 3),
            "time_minutes": round(execution_time / 60, 4),
            "time_formatted": str(timedelta(seconds=execution_time))
        },
        "triples_generated": {
            "class_instances": triples.get("class_instances", 0),
            "property_instances": triples.get("property_instances", 0),
            "total_triples": triples.get("total_triples", 0)
        },
        "performance_metrics": {
            "triples_per_second": round(
                triples.get("total_triples", 0) / execution_time, 2
            ) if execution_time > 0 else 0
        }
    }
    
    # Save JSON report to output directory
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / output_file
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print formatted report
    print("\n" + "="*60)
    print("BENCHMARK REPORT")
    print("="*60)
    print(f"\nTimestamp: {report['timestamp']}")
    print(f"\nConfiguration:")
    print(f"  Universities: {config['universities']}")
    print(f"  Starting Index: {config['starting_index']}")
    print(f"  Random Seed: {config['seed']}")
    print(f"  Output Format: {config['format']}")
    
    print(f"\nExecution Time:")
    print(f"  Seconds: {report['execution']['time_seconds']:.6f}s")
    print(f"  Milliseconds: {report['execution']['time_milliseconds']:.3f}ms")
    print(f"  Minutes: {report['execution']['time_minutes']:.4f}min")
    print(f"  Formatted: {report['execution']['time_formatted']}")
    
    print(f"\nTriples Generated:")
    print(f"  Class Instances: {report['triples_generated']['class_instances']:,}")
    print(f"  Property Instances: {report['triples_generated']['property_instances']:,}")
    print(f"  Total Triples: {report['triples_generated']['total_triples']:,}")
    
    print(f"\nPerformance Metrics:")
    print(f"  Triples/Second: {report['performance_metrics']['triples_per_second']:,.2f}")
    
    print(f"\n{'='*60}")
    print(f"Report saved to: {report_path}")
    print("="*60 + "\n")
    
    return report

def main():
    """Main function to run the LUBM generator with CLI parameters"""
    
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Execute the LUBM (Lehigh University Benchmark) generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "-u", "--universities",
        type=int,
        default=1,
        help="Number of universities to generate"
    )
    
    parser.add_argument(
        "-i", "--index",
        type=int,
        default=0,
        help="Starting index of universities"
    )
    
    parser.add_argument(
        "-s", "--seed",
        type=int,
        default=0,
        help="Seed for random data generation"
    )
    
    parser.add_argument(
        "-o", "--ontology",
        type=str,
        default="http://www.lehigh.edu/~yug2/Research/SemanticWeb/LUBM/univ-bench.owl",
        help="URL of the univ-bench ontology"
    )
    
    parser.add_argument(
        "-f", "--format",
        type=str,
        choices=["owl", "daml"],
        default="owl",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    print("LUBM Generator Executor")
    print("======================")
    print(f"Configuration:")
    print(f"  Universities: {args.universities}")
    print(f"  Starting index: {args.index}")
    print(f"  Random seed: {args.seed}")
    print(f"  Ontology URL: {args.ontology}")
    print(f"  Output format: {args.format}")
    print()
    
    # Store configuration for report
    config = {
        "universities": args.universities,
        "starting_index": args.index,
        "seed": args.seed,
        "ontology_url": args.ontology,
        "format": args.format
    }
    
    # Execute the generator and measure time
    success, execution_time, triples = execute_lubm_generator(
        univ_num=args.universities,
        starting_index=args.index,
        seed=args.seed,
        ontology_url=args.ontology,
        output_format=args.format
    )
    
    if success:
        print("\nLUBM generator completed successfully!")
        
        # Generate comprehensive report
        generate_report(config, execution_time, triples)
    else:
        print("\nLUBM generator failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
