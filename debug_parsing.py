from rdflib import Graph
import os

files = [
    ("LINKGEN", "1-Datasets/LINKGEN/run_1/data_T0_1", "nt"),
    ("RDFGRAPHGEN_LUBM", "1-Datasets/RDFGRAPHGEN_LUBM/run_1/output-graph.ttl", "turtle"),
    ("RUDOFGENERATE_LUBM_SHEX", "1-Datasets/RUDOFGENERATE_LUBM_SHEX/run_1/generated_data.ttl", "turtle")
]

for name, path, fmt in files:
    print(f"--- Testing {name} ---")
    if not os.path.exists(path):
        print(f"File not found: {path}")
        continue
        
    g = Graph()
    try:
        g.parse(path, format=fmt)
        print(f"Successfully parsed {name}. Triples: {len(g)}")
    except Exception as e:
        print(f"Error parsing {name}: {e}")
        # Try autodetect
        try:
            print("Retrying with autodetect...")
            g.parse(path)
            print(f"Successfully parsed {name} with autodetect. Triples: {len(g)}")
        except Exception as e2:
             print(f"Error with autodetect: {e2}")
