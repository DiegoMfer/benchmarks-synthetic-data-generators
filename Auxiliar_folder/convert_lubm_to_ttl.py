import os
import glob
from rdflib import Graph
from pathlib import Path

def convert_lubm_to_ttl():
    # Paths
    lubm_output_dir = Path("/home/diego/Documents/benchmarks-synthetic-data-generators/LUBM/output")
    auxiliar_folder = Path("/home/diego/Documents/benchmarks-synthetic-data-generators/Auxiliar_folder")
    output_file = auxiliar_folder / "lubm.ttl"

    # Ensure output directory exists
    auxiliar_folder.mkdir(exist_ok=True)

    # Initialize graph
    g = Graph()

    # Find all .owl files
    owl_files = sorted(list(lubm_output_dir.glob("*.owl")))
    
    if not owl_files:
        print(f"No .owl files found in {lubm_output_dir}")
        return

    print(f"Found {len(owl_files)} .owl files.")

    # Parse each file
    for owl_file in owl_files:
        print(f"Parsing {owl_file.name}...")
        try:
            g.parse(str(owl_file), format="xml")
        except Exception as e:
            print(f"Error parsing {owl_file.name}: {e}")

    print("Parsing complete.")
    print(f"Total triples: {len(g)}")
    
    # Serialize to Turtle
    print(f"Serializing to {output_file}...")
    g.serialize(destination=str(output_file), format="turtle")
    print("Done!")

if __name__ == "__main__":
    convert_lubm_to_ttl()
