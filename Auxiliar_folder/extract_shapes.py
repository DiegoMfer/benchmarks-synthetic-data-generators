from shexer.shaper import Shaper
from shexer.consts import SHEXC, SHACL_TURTLE

def extract_shapes():
    target_file = "lubm.ttl"
    
    # Define namespaces to make shapes more readable
    namespaces = {
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
        "http://www.w3.org/2000/01/rdf-schema#": "rdfs",
        "http://www.w3.org/2002/07/owl#": "owl",
        "http://www.lehigh.edu/~yug2/Research/SemanticWeb/LUBM/univ-bench.owl#": "ub",
        "http://xsd.org/": "xsd"
    }

    print("Initializing Shaper...")
    shaper = Shaper(target_classes=None,  # Extract for all classes
                   graph_file_input=target_file,
                   namespaces_dict=namespaces,
                   all_classes_mode=True,
                   input_format="turtle",
                   disable_comments=True)

    # 1. Extract ShEx
    print("Extracting ShEx shapes...")
    output_shex = "lubm.shex"
    shaper.shex_graph(output_file=output_shex,
                      acceptance_threshold=0.9) # 90% confidence for shape inclusion
    print(f"ShEx shapes saved to {output_shex}")

    # 2. Extract SHACL
    # Note: Shexer keeps internal state, but it is safer/cleaner to just call shex_graph and shacl_graph separately
    # The shaper instance 'learns' from the data during the first call usually, but let's see.
    # Actually, shexer methods trigger the whole process.
    
    print("Extracting SHACL shapes...")
    output_shacl = "lubm_shacl.ttl"
    shaper.shex_graph(output_file=output_shacl,
                      output_format=SHACL_TURTLE,
                      acceptance_threshold=0.9)
    print(f"SHACL shapes saved to {output_shacl}")

if __name__ == "__main__":
    extract_shapes()
