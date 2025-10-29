#!/usr/bin/env python3
"""
Script to execute the LUBM (Lehigh University Benchmark) generator
"""

import subprocess
import os
import sys
from pathlib import Path

def execute_lubm_generator(univ_num=1, starting_index=0, seed=0, ontology_url=None, output_format="owl"):
    """
    Execute the LUBM generator with specified parameters
    
    Args:
        univ_num (int): Number of universities to generate (default: 1)
        starting_index (int): Starting index of universities (default: 0)
        seed (int): Seed for random data generation (default: 0)
        ontology_url (str): URL of the univ-bench ontology (required)
        output_format (str): Output format - "owl" or "daml" (default: "owl")
    """
    
    # Path to the LUBM generator jar file
    jar_path = Path(__file__).parent / "LUBM" / "uba1.7" / "lubm-generator-fixed.jar"
    
    if not jar_path.exists():
        print(f"Error: LUBM generator jar file not found at {jar_path}")
        return False
    
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
        return False
    
    print(f"Executing LUBM generator with command:")
    print(" ".join(cmd))
    print()
    
    try:
        # Execute the command
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=jar_path.parent)
        
        if result.returncode == 0:
            print("LUBM generator executed successfully!")
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
        
        return result.returncode == 0
        
    except FileNotFoundError:
        print("Error: Java not found. Please make sure Java is installed and in your PATH.")
        return False
    except Exception as e:
        print(f"Error executing LUBM generator: {e}")
        return False

def main():
    """Main function to run the LUBM generator with default or custom parameters"""
    
    # Example ontology URL (you may need to adjust this)
    # The LUBM benchmark typically uses this ontology
    default_ontology_url = "http://www.lehigh.edu/~yug2/Research/SemanticWeb/LUBM/univ-bench.owl"
    
    print("LUBM Generator Executor")
    print("======================")
    
    # You can modify these parameters as needed
    univ_count = 1  # Generate data for 1 university
    start_index = 0
    random_seed = 0
    ontology_url = default_ontology_url
    format_type = "owl"  # or "daml"
    
    print(f"Configuration:")
    print(f"  Universities: {univ_count}")
    print(f"  Starting index: {start_index}")
    print(f"  Random seed: {random_seed}")
    print(f"  Ontology URL: {ontology_url}")
    print(f"  Output format: {format_type}")
    print()
    
    success = execute_lubm_generator(
        univ_num=univ_count,
        starting_index=start_index,
        seed=random_seed,
        ontology_url=ontology_url,
        output_format=format_type
    )
    
    if success:
        print("\nLUBM generator completed successfully!")
    else:
        print("\nLUBM generator failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()