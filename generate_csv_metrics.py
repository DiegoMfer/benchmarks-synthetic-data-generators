import os
import glob
import json
import pandas as pd
import numpy as np
from rdflib import Graph, RDF
from collections import defaultdict
from pathlib import Path
import re
import sys

# Path to the datasets
DATASETS_DIR = "1-Datasets"
OUTPUT_CSV = "metrics_comparison.csv"

def calculate_rdf_metrics(g):
    """
    Calculates Primitive, Degree, and Structuredness metrics for an RDF graph.
    """
    print(f"Graph loaded with {len(g)} triples. Computing metrics...")
    
    # --- Primitive Metrics ---
    num_triples = len(g)
    subjects = set(g.subjects())
    predicates = set(g.predicates())
    objects = set(g.objects())
    
    # Classes (C): Objects of rdf:type statements
    classes = set(g.objects(predicate=RDF.type))
    
    num_subjects = len(subjects)
    num_predicates = len(predicates)
    num_objects = len(objects)
    num_classes = len(classes)
    
    # --- Degree Metrics ---
    out_degrees = defaultdict(int)
    in_degrees = defaultdict(int)
    
    # Structuredness helpers
    type_instances = defaultdict(set)
    instance_properties = defaultdict(set)
    
    for s, p, o in g:
        out_degrees[s] += 1
        in_degrees[o] += 1
        instance_properties[s].add(p)
        
        if p == RDF.type:
            type_instances[o].add(s)

    mean_outdegree = np.mean(list(out_degrees.values())) if out_degrees else 0
    mean_indegree = np.mean(list(in_degrees.values())) if in_degrees else 0
    
    # --- Structuredness Metrics ---
    cv_t_values = {}
    weighted_cv_sum = 0
    total_typed_instances_count = sum(len(instances) for instances in type_instances.values())
        
    for t, instances in type_instances.items():
        i_t_size = len(instances)
        if i_t_size == 0:
            continue
            
        p_t = set()
        numerator = 0
        
        for s in instances:
            props = instance_properties[s]
            p_t.update(props)
            numerator += len(props)
            
        p_t_size = len(p_t)
        denominator = p_t_size * i_t_size
        
        cv_t = numerator / denominator if denominator > 0 else 0
        cv_t_values[str(t)] = cv_t
        
        if total_typed_instances_count > 0:
            w_t = i_t_size / total_typed_instances_count
            weighted_cv_sum += w_t * cv_t
            
    coherence = weighted_cv_sum
    avg_coverage = np.mean(list(cv_t_values.values())) if cv_t_values else 0
    
    return {
        "RDF_Triples": num_triples,
        "RDF_Subjects": num_subjects,
        "RDF_Predicates": num_predicates,
        "RDF_Objects": num_objects,
        "RDF_Classes": num_classes,
        "RDF_Mean_Outdegree": mean_outdegree,
        "RDF_Mean_Indegree": mean_indegree,
        "RDF_Coherence": coherence,
        "RDF_Type_Coverage_Avg": avg_coverage
    }

def load_graph_for_run(run_path, generator_name):
    """
    Finds and loads the RDF dataset for a specific run.
    """
    files_to_load = []
    format = "turtle" # Default
    
    # Define file patterns based on generator type
    # Use exact matches or startswith to avoid substring collisions (e.g. LUBM in RDFGRAPHGEN_LUBM)
    
    if generator_name == "BSBM":
        files_to_load = glob.glob(os.path.join(run_path, "dataset.ttl"))
    elif generator_name == "LUBM":
        files_to_load = glob.glob(os.path.join(run_path, "*.owl"))
        format = "xml" 
    elif generator_name == "GAIA":
        files_to_load = glob.glob(os.path.join(run_path, "gaia_instances.owl"))
        format = "xml"
    elif generator_name == "LINKGEN":
        # LINKGEN produces extensionless files like data_T0_1, and a void.ttl
        # We want the data files.
        files_to_load = glob.glob(os.path.join(run_path, "data_*"))
        # Exclude if they are directories (unlikely but safe)
        files_to_load = [f for f in files_to_load if os.path.isfile(f)]
        format = "nt"
    elif generator_name == "PYGRAFT":
        files_to_load = glob.glob(os.path.join(run_path, "full_graph.ttl"))
        if not files_to_load:
             files_to_load = glob.glob(os.path.join(run_path, "full_graph.rdf"))
             format = "xml"
    elif "RDFGRAPHGEN" in generator_name:
        # Matches RDFGRAPHGEN and RDFGRAPHGEN_LUBM
        files_to_load = glob.glob(os.path.join(run_path, "output-graph.ttl"))
    elif "RUDOF" in generator_name:
        # Matches RUDOFGENERATE and its variants
        files_to_load = glob.glob(os.path.join(run_path, "generated_data.ttl"))
    else:
        # Generic fallback
        files_to_load = glob.glob(os.path.join(run_path, "*.ttl"))
    
    if not files_to_load:
        print(f"  Warning: No data files found in {run_path} for {generator_name}")
        return None

    g = Graph()
    print(f"  Loading {len(files_to_load)} file(s) from {run_path}...")
    
    for file_path in files_to_load:
        try:
            g.parse(file_path, format=format)
        except Exception as e:
            # Try autodetect if specified format fails
            try:
                g.parse(file_path)
            except Exception as e2:
                print(f"  Error parsing {file_path}: {e2}")
    
    return g

def extract_performance_metrics(run_path):
    """
    Parses benchmark_report.json to get performance metrics.
    """
    benchmark_file = os.path.join(run_path, 'benchmark_report.json')
    
    if not os.path.exists(benchmark_file):
        print(f"  Warning: No benchmark_report.json in {run_path}")
        return {}
        
    try:
        with open(benchmark_file, 'r') as f:
            benchmark = json.load(f)
        
        throughput = None
        triples = None
        exec_time = None
        
        # --- Throughput Extraction ---
        if 'performance_metrics' in benchmark:
            throughput = benchmark['performance_metrics'].get('triples_per_second')
        elif 'performance' in benchmark:
            throughput = benchmark['performance'].get('triples_per_second')
        elif 'throughput' in benchmark:
            if isinstance(benchmark['throughput'], dict):
                throughput = benchmark['throughput'].get('triples_per_second')
            else:
                throughput = benchmark['throughput']
        elif 'generated_data' in benchmark and 'triples_per_second' in benchmark['generated_data']:
            throughput = benchmark['generated_data']['triples_per_second']
        elif 'triples_per_second' in benchmark:
            throughput = benchmark['triples_per_second']
            
        # --- Triples Count Extraction ---
        if 'triples_generated' in benchmark and 'total_triples' in benchmark['triples_generated']:
             triples = benchmark['triples_generated']['total_triples']
        elif 'generated_data' in benchmark:
            if 'triples_total' in benchmark['generated_data']:
                triples = benchmark['generated_data']['triples_total']
            elif 'estimated_triples' in benchmark['generated_data']:
                triples = benchmark['generated_data']['estimated_triples']
            elif 'total_triples' in benchmark['generated_data']:
                triples = benchmark['generated_data']['total_triples']
        elif 'triples' in benchmark:
            if isinstance(benchmark['triples'], dict):
                triples = benchmark['triples'].get('total', benchmark['triples'].get('total_triples'))
            else:
                triples = benchmark['triples']
        elif 'total_triples' in benchmark:
            triples = benchmark['total_triples']
        elif 'estimated_triples' in benchmark:
            triples = benchmark['estimated_triples']
            
        # GAIA Special Case
        if 'results' in benchmark and 'instances_generated' in benchmark['results']:
            instances = benchmark['results']['instances_generated']
            if (instances is None or instances == 0) and 'stdout' in benchmark:
                match = re.search(r'(\d+)\s+instances\s+(?:has been generated|writted)', benchmark['stdout'])
                if match:
                    instances = int(match.group(1))
            if instances and instances > 0:
                triples = instances * 3 # Approximation
        
        # --- Execution Time Extraction ---
        if 'execution' in benchmark and 'time_seconds' in benchmark['execution']:
            exec_time = benchmark['execution']['time_seconds']
        elif 'results' in benchmark and 'execution_time_seconds' in benchmark['results']:
            exec_time = benchmark['results']['execution_time_seconds']
        elif 'execution_time' in benchmark:
            if isinstance(benchmark['execution_time'], dict):
                exec_time = benchmark['execution_time'].get('seconds', benchmark['execution_time'].get('time_seconds'))
            else:
                exec_time = benchmark['execution_time']
        elif 'execution_time_seconds' in benchmark:
            exec_time = benchmark['execution_time_seconds']
        elif 'time_seconds' in benchmark:
            exec_time = benchmark['time_seconds']
            
        # Backfill throughput
        if throughput is None and triples is not None and exec_time is not None and exec_time > 0:
            throughput = triples / exec_time
            
        return {
            "Perf_Throughput": throughput,
            "Perf_Total_Triples": triples,
            "Perf_Execution_Time": exec_time
        }
    except Exception as e:
        print(f"  Error reading benchmark report {benchmark_file}: {e}")
        return {}

def main():
    if not os.path.exists(DATASETS_DIR):
        print(f"Error: Datasets directory '{DATASETS_DIR}' not found.")
        return

    # Load existing results to avoid re-computation
    existing_results = {}
    if os.path.exists(OUTPUT_CSV):
        try:
            df_existing = pd.read_csv(OUTPUT_CSV)
            # Create a dict keyed by (Generator, Run_ID)
            for _, row in df_existing.iterrows():
                key = (row['Generator'], row['Run_ID'])
                # Only consider it "existing" if we have RDF metrics (check RDF_Triples)
                # If RDF_Triples is NaN/empty, we want to re-compute
                if pd.notna(row.get('RDF_Triples')) and row.get('RDF_Triples') != "":
                    existing_results[key] = row.to_dict()
            print(f"Loaded {len(existing_results)} existing complete runs from {OUTPUT_CSV}")
        except Exception as e:
            print(f"Error loading existing CSV: {e}")

    all_results = []
    # Initialize all_results with existing data so we don't lose it if we crash
    all_results.extend(list(existing_results.values()))
    
    datasets_path = Path(DATASETS_DIR)
    
    # Iterate through generators
    # Process LinkGen last because it is huge and might fail/OOM
    dirs = sorted([d for d in datasets_path.iterdir() if d.is_dir() and not d.name.startswith('.')])
    # Move LINKGEN to end
    linkgen_dirs = [d for d in dirs if "LINKGEN" in d.name]
    other_dirs = [d for d in dirs if "LINKGEN" not in d.name]
    sorted_dirs = other_dirs + linkgen_dirs
    
    for generator_folder in sorted_dirs:
        generator_name = generator_folder.name
        print(f"\nProcessing Generator: {generator_name}")
        
        # Iterate through runs
        for run_folder in sorted(generator_folder.iterdir()):
            if not run_folder.is_dir() or not run_folder.name.startswith('run_'):
                continue
                
            run_id = run_folder.name
            
            # Check if we already have this run completed
            # Force re-process for RUDOFGENERATE_LUBM variants (missing RDF) and LUBM (missing Perf Triples)
            is_rudof_variant = "RUDOFGENERATE_LUBM" in generator_name
            is_lubm = generator_name == "LUBM"
            if (generator_name, run_id) in existing_results and not is_rudof_variant and not is_lubm:
                print(f"  Skipping {run_id} (already complete)")
                continue

            print(f"  Processing {run_id}...")
            
            # 1. Get Performance Metrics
            perf_metrics = extract_performance_metrics(str(run_folder))
            
            # 2. Get RDF Metrics
            # Note: This can be slow for large datasets
            rdf_metrics = {}
            graph = load_graph_for_run(str(run_folder), generator_name)
            
            if graph and len(graph) > 0:
                try:
                    rdf_metrics = calculate_rdf_metrics(graph)
                except Exception as e:
                    print(f"  Error calculating RDF metrics: {e}")
            else:
                print("  Skipping RDF metrics (graph empty or not loaded).")
                
            # Combine
            run_data = {
                "Generator": generator_name,
                "Run_ID": run_id,
                **perf_metrics,
                **rdf_metrics
            }
            
            # Remove old entry if exists (incomplete one)
            all_results = [r for r in all_results if not (r['Generator'] == generator_name and r['Run_ID'] == run_id)]
            all_results.append(run_data)
            
            # Save progressively
            save_results(all_results)
            
def save_results(all_results):
    if all_results:
        df = pd.DataFrame(all_results)
        
        # Order columns nicely
        cols = ["Generator", "Run_ID"]
        perf_cols = [c for c in df.columns if c.startswith("Perf_")]
        rdf_cols = [c for c in df.columns if c.startswith("RDF_")]
        other_cols = [c for c in df.columns if c not in cols + perf_cols + rdf_cols]
        
        final_cols = cols + perf_cols + rdf_cols + other_cols
        # Use simple reindex to avoid errors if cols are missing
        df = df.reindex(columns=final_cols)
        
        df.sort_values(by=["Generator", "Run_ID"], inplace=True)
        df.to_csv(OUTPUT_CSV, index=False)
        print(f"  Saved progress to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()