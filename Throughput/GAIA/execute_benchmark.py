#!/usr/bin/env python3
"""
Script to execute the GAIA generator with LUBM ontology
"""

import subprocess
import os
import sys
import argparse
import time
import json
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta

# LUBM ontology URL
LUBM_ONTOLOGY_URL = "http://swat.cse.lehigh.edu/onto/univ-bench.owl"
LUBM_ONTOLOGY_FILE = "univ-bench.owl"

def download_lubm_ontology():
    """Download LUBM ontology if not present"""
    if not os.path.exists(LUBM_ONTOLOGY_FILE):
        print(f"Downloading LUBM ontology from {LUBM_ONTOLOGY_URL}...")
        try:
            urllib.request.urlretrieve(LUBM_ONTOLOGY_URL, LUBM_ONTOLOGY_FILE)
            print(f"✅ Downloaded LUBM ontology to {LUBM_ONTOLOGY_FILE}")
        except Exception as e:
            print(f"❌ Failed to download LUBM ontology: {e}")
            print("Please manually download the LUBM ontology file.")
            sys.exit(1)
    else:
        print(f"✅ LUBM ontology found: {LUBM_ONTOLOGY_FILE}")

def parse_output_stats(output_text):
    """
    Parse statistics from GAIA output
    
    Args:
        output_text (str): The stdout from GAIA generator
    
    Returns:
        dict: Dictionary with generation statistics
    """
    stats = {
        "instances_generated": 0,
        "classes_processed": 0,
        "execution_time": 0
    }
    
    lines = output_text.split('\n')
    for line in lines:
        if "instances generated" in line.lower():
            # Try to extract number of instances
            import re
            numbers = re.findall(r'\d+', line)
            if numbers:
                stats["instances_generated"] = int(numbers[-1])
        elif "classes" in line.lower() and "processed" in line.lower():
            import re
            numbers = re.findall(r'\d+', line)
            if numbers:
                stats["classes_processed"] = int(numbers[-1])
    
    return stats

def run_gaia_generator(instances_per_class=3, limit=None, materialization=False, threads=None, output_file=None):
    """
    Run the GAIA generator with specified parameters
    
    Args:
        instances_per_class (int): Number of instances per class
        limit (int): Maximum number of instances per class
        materialization (bool): Use materialization
        threads (int): Number of threads to use
        output_file (str): Output file path
    
    Returns:
        dict: Benchmark results
    """
    
    # Ensure LUBM ontology is available
    download_lubm_ontology()
    
    # Prepare output file
    if output_file is None:
        output_file = "output/gaia_instances.owl"
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Build command
    cmd = ["java", "-Xmx8g", "-jar", "OWLGenerator.jar"]
    cmd.extend(["-F", LUBM_ONTOLOGY_FILE])
    cmd.extend(["-O", output_file])
    cmd.extend(["-N", str(instances_per_class)])
    
    if limit:
        cmd.extend(["-L", str(limit)])
    
    if materialization:
        cmd.append("-M")
    
    if threads:
        cmd.extend(["-T", str(threads)])
    
    print(f"🚀 Running GAIA Generator...")
    print(f"📁 Input ontology: {LUBM_ONTOLOGY_FILE}")
    print(f"📁 Output file: {output_file}")
    print(f"🔢 Instances per class: {instances_per_class}")
    if limit:
        print(f"🔢 Instance limit per class: {limit}")
    print(f"⚡ Materialization: {'Yes' if materialization else 'No'}")
    if threads:
        print(f"🧵 Threads: {threads}")
    print(f"💻 Command: {' '.join(cmd)}")
    print("=" * 50)
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        if result.returncode == 0:
            print("✅ GAIA generation completed successfully!")
        else:
            print(f"❌ GAIA generation failed with return code: {result.returncode}")
            print(f"Error output: {result.stderr}")
            return None
            
        # Parse output statistics
        stats = parse_output_stats(result.stdout)
        stats["execution_time"] = execution_time
        
        # Get file size
        output_size = 0
        if os.path.exists(output_file):
            output_size = os.path.getsize(output_file)
        
        # Prepare benchmark report
        report = {
            "benchmark_name": "GAIA",
            "generator_version": "3.1",
            "ontology": "LUBM",
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "instances_per_class": instances_per_class,
                "limit": limit,
                "materialization": materialization,
                "threads": threads
            },
            "results": {
                "execution_time_seconds": execution_time,
                "execution_time_formatted": str(timedelta(seconds=int(execution_time))),
                "instances_generated": stats["instances_generated"],
                "classes_processed": stats["classes_processed"],
                "output_file": output_file,
                "output_size_bytes": output_size,
                "output_size_mb": round(output_size / (1024 * 1024), 2)
            },
            "command_executed": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr if result.stderr else None
        }
        
        return report
        
    except subprocess.TimeoutExpired:
        print("❌ GAIA generation timed out (1 hour limit)")
        return None
    except Exception as e:
        print(f"❌ Error running GAIA generator: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Execute GAIA generator with LUBM ontology')
    parser.add_argument('--instances', '-n', type=int, default=3,
                      help='Number of instances per class (default: 3)')
    parser.add_argument('--limit', '-l', type=int,
                      help='Maximum number of instances per class')
    parser.add_argument('--materialization', '-m', action='store_true',
                      help='Use materialization during generation')
    parser.add_argument('--threads', '-t', type=int,
                      help='Number of threads to use')
    parser.add_argument('--output', '-o', type=str, default='output/gaia_instances.owl',
                      help='Output file path (default: output/gaia_instances.owl)')
    parser.add_argument('--json-output', type=str, default='output/benchmark_report.json',
                      help='JSON report output file (default: output/benchmark_report.json)')
    
    args = parser.parse_args()
    
    print("🎯 GAIA Generator with LUBM Ontology")
    print("=" * 40)
    
    # Run the benchmark
    report = run_gaia_generator(
        instances_per_class=args.instances,
        limit=args.limit,
        materialization=args.materialization,
        threads=args.threads,
        output_file=args.output
    )
    
    if report:
        # Save JSON report
        with open(args.json_output, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Benchmark Results:")
        print(f"⏱️  Execution Time: {report['results']['execution_time_formatted']}")
        print(f"🔢 Instances Generated: {report['results']['instances_generated']}")
        print(f"📁 Output Size: {report['results']['output_size_mb']} MB")
        print(f"📄 Report saved to: {args.json_output}")
        print(f"💾 Output saved to: {args.output}")
        
        return 0
    else:
        print("❌ Benchmark failed")
        return 1

if __name__ == "__main__":
    exit(main())
