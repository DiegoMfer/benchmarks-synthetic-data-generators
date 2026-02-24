#!/usr/bin/env python3
"""
Dataset Generation Script for RDF Synthetic Data Generators

This script generates datasets from all 8 RDF generators and saves them
in the 1-Datasets/ folder with proper organization and metadata.

Usage:
    python3 generate_all_datasets.py [--generators GENERATOR1 GENERATOR2 ...]
    
Examples:
    python3 generate_all_datasets.py                    # Generate all datasets
    python3 generate_all_datasets.py --generators BSBM LUBM  # Generate specific datasets
"""

import subprocess
import json
import shutil
import argparse
import os
from pathlib import Path
from datetime import datetime
import sys

class DatasetGenerator:
    """Base class for dataset generation"""
    
    def __init__(self, name, source_dir, dataset_dir):
        self.name = name
        self.source_dir = Path(source_dir)
        
        # Create generator folder
        generator_folder = Path(dataset_dir) / name
        generator_folder.mkdir(parents=True, exist_ok=True)
        
        # Find the next run number
        existing_runs = list(generator_folder.glob('run_*'))
        if existing_runs:
            run_numbers = []
            for run_folder in existing_runs:
                try:
                    num = int(run_folder.name.split('_')[1])
                    run_numbers.append(num)
                except (IndexError, ValueError):
                    continue
            next_run = max(run_numbers) + 1 if run_numbers else 1
        else:
            next_run = 1
        
        # Create the new run folder
        self.dataset_dir = generator_folder / f'run_{next_run}'
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.run_number = next_run
        
        print(f"📂 Creating {name}/run_{next_run}/")
        
    def generate(self):
        """Override in subclasses"""
        raise NotImplementedError
        
    def save_metadata(self, metadata):
        """Save metadata JSON file"""
        metadata_file = self.dataset_dir / 'metadata.json'
        metadata['generator'] = self.name
        metadata['run_number'] = self.run_number
        metadata['generated_at'] = datetime.now().isoformat()
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Metadata saved to {metadata_file}")
        
    def copy_files(self, file_patterns):
        """Copy generated files to dataset directory"""
        output_dir = self.source_dir / 'output'
        copied = []
        
        for pattern in file_patterns:
            for file_path in output_dir.glob(pattern):
                dest = self.dataset_dir / file_path.name
                shutil.copy2(file_path, dest)
                copied.append(file_path.name)
                print(f"  📁 Copied: {file_path.name}")
        
        return copied


class BSBMGenerator(DatasetGenerator):
    """BSBM E-commerce benchmark generator"""
    
    def generate(self, products=10000, format='ttl'):
        print(f"\n{'='*80}")
        print(f"🔵 GENERATING BSBM DATASET (Docker)")
        print(f"{'='*80}")
        print(f"Products: {products:,}")
        print(f"Format: {format}")
        
        # Build Docker image
        print("Building Docker image...")
        try:
            subprocess.run(['docker', 'compose', 'build'], cwd=self.source_dir, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Docker build failed: {e.stderr.decode()}")
            return False
        
        # Run using docker compose
        cmd = [
            'docker', 'compose', 'run', '--rm',
            'bsbm-benchmark',
            '--products', str(products),
            '--format', format
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.source_dir)
        
        if result.returncode == 0:
            print(result.stdout)
            
            # Copy generated files
            files = self.copy_files(['dataset.*', 'benchmark_report.json'])
            
            # Save metadata
            metadata = {
                'configuration': {
                    'products': products,
                    'format': format
                },
                'files': files,
                'description': 'E-commerce domain with products, vendors, offers, and reviews'
            }
            self.save_metadata(metadata)
            
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            print(f"Stdout: {result.stdout}")
            return False


class LUBMGenerator(DatasetGenerator):
    """LUBM University benchmark generator"""
    
    def generate(self, universities=10, seed=0):
        print(f"\n{'='*80}")
        print(f"🔴 GENERATING LUBM DATASET (Docker)")
        print(f"{'='*80}")
        print(f"Universities: {universities}")
        print(f"Seed: {seed}")
        
        # Build Docker image
        print("Building Docker image...")
        try:
            subprocess.run(['docker', 'compose', 'build'], cwd=self.source_dir, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Docker build failed: {e.stderr.decode()}")
            return False
        
        # Run using docker compose
        cmd = [
            'docker', 'compose', 'run', '--rm',
            'lubm-benchmark',
            '--universities', str(universities),
            '--seed', str(seed)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.source_dir)
        
        if result.returncode == 0:
            print(result.stdout)
            
            # Copy generated files (all University*.owl files)
            files = self.copy_files(['University*.owl', 'benchmark_report.json', 'log.txt'])
            
            # Save metadata
            metadata = {
                'configuration': {
                    'universities': universities,
                    'seed': seed
                },
                'files': files,
                'description': 'University domain with departments, professors, students, and courses'
            }
            self.save_metadata(metadata)
            
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            print(f"Stdout: {result.stdout}")
            return False


class GAIAGenerator(DatasetGenerator):
    """GAIA ontology instance generator"""
    
    def generate(self, instances=1000, materialization=True):
        print(f"\n{'='*80}")
        print(f"🟢 GENERATING GAIA DATASET (Docker)")
        print(f"{'='*80}")
        print(f"Instances per class: {instances}")
        print(f"Materialization: {materialization}")
        
        # Build Docker image
        print("Building Docker image...")
        try:
            subprocess.run(['docker', 'compose', 'build'], cwd=self.source_dir, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Docker build failed: {e.stderr.decode()}")
            return False
        
        # Build command with optional materialization flag
        cmd = ['docker', 'compose', 'run', '--rm', 'gaia-benchmark', '--instances', str(instances)]
        
        if materialization:
            cmd.append('--materialization')
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.source_dir)
        
        if result.returncode == 0:
            print(result.stdout)
            
            # Copy generated files
            files = self.copy_files(['gaia_instances.owl', 'benchmark_report.json'])
            
            # Save metadata
            metadata = {
                'configuration': {
                    'instances_per_class': instances,
                    'materialization': materialization
                },
                'files': files,
                'description': 'Ontology instance generator using LUBM ontology for university domain data'
            }
            self.save_metadata(metadata)
            
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            print(f"Stdout: {result.stdout}")
            return False


class LINKGENGenerator(DatasetGenerator):
    """LINKGEN flexible linked data generator"""
    
    def generate(self, triples=2000000, ontology='dbpedia_2015.owl', distribution='zipf', 
                 threads=4, gaussian_mean=50, gaussian_deviation=10, zipf_exponent=1.5):
        print(f"\n{'='*80}")
        print(f"🟡 GENERATING LINKGEN DATASET (Docker)")
        print(f"{'='*80}")
        print(f"Triples: {triples:,}")
        print(f"Ontology: {ontology}")
        print(f"Distribution: {distribution}")
        
        # Build Docker image
        print("Building Docker image...")
        try:
            subprocess.run(['docker', 'compose', 'build'], cwd=self.source_dir, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Docker build failed: {e.stderr.decode()}")
            return False
        
        # Run using docker compose
        cmd = [
            'docker', 'compose', 'run', '--rm',
            'linkgen-benchmark',
            '--triples', str(triples),
            '--ontology', ontology,
            '--distribution', distribution,
            '--threads', str(threads)
        ]
        
        # Add distribution-specific parameters
        if distribution == 'gaussian':
            cmd.extend(['--gaussian-mean', str(gaussian_mean)])
            cmd.extend(['--gaussian-deviation', str(gaussian_deviation)])
        elif distribution == 'zipf':
            cmd.extend(['--zipf-exponent', str(zipf_exponent)])
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.source_dir)
        
        if result.returncode == 0:
            print(result.stdout)
            
            # Copy generated files (all data files and VoID)
            files = self.copy_files(['data_*', 'void.ttl', 'benchmark_report.json'])
            
            # Save metadata
            metadata = {
                'configuration': {
                    'triples': triples,
                    'ontology': ontology,
                    'distribution': distribution,
                    'threads': threads
                },
                'files': files,
                'description': 'Flexible synthetic linked data generator with configurable distributions'
            }
            self.save_metadata(metadata)
            
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            print(f"Stdout: {result.stdout}")
            return False


class PyGraftGenerator(DatasetGenerator):
    """PyGraft schema and knowledge graph generator"""
    
    def generate(self, mode='full', classes=30, relations=20, avg_instances=80, max_depth=5, 
                 p_subclass=0.15, avg_relations=3, std_instances=10, std_relations=1,
                 p_disjoint=0.05, p_inverse=0.2, p_functional=0.2, p_symmetric=0.1,
                 p_transitive=0.1, seed=42):
        """
        Generate synthetic RDF data using PyGraft.
        
        Coherence-affecting parameters:
        - classes: Number of classes (fewer = higher coherence per type)
        - avg_instances: Instances per class (more = higher coherence)
        - max_depth: Hierarchy depth (shallow = higher coherence)
        - p_subclass: Subclass probability (lower = flatter, higher coherence)
        - avg_relations: Relations per individual (more = higher coherence)
        - std_instances/std_relations: Variation (lower = more uniform, higher coherence)
        """
        print(f"\n{'='*80}")
        print(f"🟣 GENERATING PYGRAFT DATASET")
        print(f"{'='*80}")
        print(f"Mode: {mode}")
        print(f"Classes: {classes}")
        print(f"Relations: {relations}")
        print(f"Avg instances/class: {avg_instances}")
        print(f"Std instances: {std_instances}")
        print(f"Avg relations/individual: {avg_relations}")
        print(f"Std relations: {std_relations}")
        print(f"Max depth: {max_depth}")
        print(f"Subclass prob: {p_subclass}")
        print(f"Seed: {seed}")
        
        cmd = [
            'docker', 'run', '--rm',
            '-v', f"{self.source_dir / 'output'}:/app/output",
            'pygraft-benchmark:latest',
            'python', 'execute_benchmark.py',
            '--mode', mode,
            '--n-classes', str(classes),
            '--n-relations', str(relations),
            '--avg-instances', str(avg_instances),
            '--std-instances', str(std_instances),
            '--avg-relations', str(avg_relations),
            '--std-relations', str(std_relations),
            '--max-depth', str(max_depth),
            '--p-subclass', str(p_subclass),
            '--p-disjoint', str(p_disjoint),
            '--p-inverse', str(p_inverse),
            '--p-functional', str(p_functional),
            '--p-symmetric', str(p_symmetric),
            '--p-transitive', str(p_transitive),
            '--seed', str(seed),
            '--no-check-consistency'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout)
            
            # Copy generated files (PyGraft uses .rdf format)
            files = self.copy_files(['*.rdf', '*.json', '*.yml'])
            
            # Convert RDF/XML to Turtle format for better compatibility
            try:
                from rdflib import Graph
                
                output_dir = self.source_dir / 'output'
                for rdf_file in output_dir.glob('*.rdf'):
                    ttl_file = self.dataset_dir / rdf_file.with_suffix('.ttl').name
                    g = Graph()
                    g.parse(str(rdf_file), format='xml')
                    g.serialize(str(ttl_file), format='turtle')
                    files.append(ttl_file.name)
                    print(f"  📄 Converted: {rdf_file.name} -> {ttl_file.name}")
            except Exception as e:
                print(f"  ⚠️  Could not convert RDF to Turtle: {e}")
            
            # Save metadata
            metadata = {
                'configuration': {
                    'mode': mode,
                    'classes': classes,
                    'relations': relations,
                    'avg_instances': avg_instances,
                    'std_instances': std_instances,
                    'avg_relations': avg_relations,
                    'std_relations': std_relations,
                    'max_depth': max_depth,
                    'p_subclass': p_subclass,
                    'p_disjoint': p_disjoint,
                    'p_inverse': p_inverse,
                    'p_functional': p_functional,
                    'p_symmetric': p_symmetric,
                    'p_transitive': p_transitive,
                    'seed': seed
                },
                'files': files,
                'description': 'Configurable schema and knowledge graph generator with RDFS/OWL constructs'
            }
            self.save_metadata(metadata)
            
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            return False


class RDFGraphGenGenerator(DatasetGenerator):
    """RDFGraphGen SHACL-based generator"""
    
    def generate(self, shape='input-shape.ttl', scale_factor=100):
        print(f"\n{'='*80}")
        print(f"🟢 GENERATING RDFGRAPHGEN DATASET (Docker)")
        print(f"{'='*80}")
        print(f"Shape: {shape}")
        print(f"Scale factor: {scale_factor}")
        
        # Build Docker image
        print("Building Docker image...")
        try:
            subprocess.run(['docker', 'compose', 'build'], cwd=self.source_dir, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Docker build failed: {e.stderr.decode()}")
            return False
        
        # Run using docker compose
        cmd = [
            'docker', 'compose', 'run', '--rm',
            'rdfgraphgen-benchmark',
            '--shape', shape,
            '--output', 'output-graph.ttl',
            '--scale-factor', str(scale_factor)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.source_dir)
        
        if result.returncode == 0:
            print(result.stdout)
            
            # Copy generated files
            files = self.copy_files(['output-graph.ttl', 'benchmark_report.json'])
            
            # Save metadata
            metadata = {
                'configuration': {
                    'shape': shape,
                    'scale_factor': scale_factor
                },
                'files': files,
                'description': 'SHACL-based synthetic data generator that generates RDF from shape definitions'
            }
            self.save_metadata(metadata)
            
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            print(f"Stdout: {result.stdout}")
            return False


class RUDOFGenerateGenerator(DatasetGenerator):
    """RUDOF Generate high-performance ShEx-based generator"""
    
    def generate(self, schema='example_schema.shex', config_file='benchmark_config.toml'):
        print(f"\n{'='*80}")
        print(f"🟠 GENERATING RUDOF GENERATE DATASET (Binary v0.1.142)")
        print(f"{'='*80}")
        print(f"Schema: {schema}")
        print(f"Config file: {config_file}")
        
        # Build first to ensure image is up to date
        print("Building Docker image...")
        try:
            subprocess.run(['docker', 'compose', 'build'], cwd=self.source_dir, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Docker build failed: {e.stderr.decode()}")
            return False
        
        # Set environment variables for docker-compose
        env = os.environ.copy()
        env['CONFIG_FILE'] = config_file
        env['SCHEMA_FILE'] = schema
        
        # Run using docker compose
        cmd = [
            'docker', 'compose', 'run', '--rm',
            'rudofgenerate'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.source_dir, env=env)
        
        if result.returncode == 0:
            print(result.stdout)
            
            # Copy generated files
            files = self.copy_files(['generated_data.*', 'benchmark_report.json', '*.stats.json'])
            
            # Save metadata
            metadata = {
                'configuration': {
                    'schema': schema,
                    'config_file': config_file,
                    'version': 'v0.1.142'
                },
                'files': files,
                'description': 'High-performance RDF generator using ShEx schemas (Binary version)'
            }
            self.save_metadata(metadata)
            
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            print(f"Stdout: {result.stdout}")
            return False


def get_benchmark_configurations2():
    """
    Returns the configuration parameters for each benchmark generator.
    Edit the values in this dictionary to configure the datasets.
    """
    return {
        'BSBM': {
            'runs': 3,
            'products': 50000,
            'format': 'ttl'
        },
        'LUBM': {
            'runs': 3,
            'universities': 10,
            'seed': 0
        },
        'GAIA': {
            'runs': 3,
            'instances': 10000,
            'materialization': True
        },
        'LINKGEN': {
            'runs': 3,
            'triples': 60000,
            'ontology': 'dbpedia_2015.owl',
            'distribution': 'zipf',
            'threads': 4
        },
        'LINKGEN_LUBM': {
            'runs': 3,
            'triples': 6000,
            'ontology': 'univ-bench.owl',
            'distribution': 'zipf',
            'threads': 4
        },
        'PYGRAFT': {
            'runs': 3,
            'mode': 'full',
            'classes': 32,
            'relations': 18,
            'avg_instances': 300,
            'max_depth': 3,
            'p_subclass': 0.1
        },
        'RDFGRAPHGEN_LUBM': {
            'runs': 3,
            'shape': 'lubm_shacl.ttl',
            'scale_factor': 2000
        },
        'RUDOFGENERATE_LUBM_SHEX': {
            'runs': 3,
            'schema': 'lubm.shex',
            'config_file': 'benchmark_config.toml'
        },
        'RUDOFGENERATE_LUBM_SHACL': {
            'runs': 3,
            'schema': 'lubm_shacl.ttl',
            'config_file': 'benchmark_config.toml'
        }
        
    }

def get_benchmark_configurations():
    """
    Returns the configuration parameters for each benchmark generator.
    Includes both HIGH COHERENCE and LOW COHERENCE configurations.
    
    Coherence measures structural regularity:
    - HIGH (~1): Instances have values for almost all properties (structured/complete)
    - LOW (~0): Properties vary significantly between instances (sparse/varied)
    
    Edit the values in this dictionary to configure the datasets.
    """
    return {
        # =======================================================================
        # BSBM - Berlin SPARQL Benchmark (E-commerce)
        # =======================================================================
        'BSBM_HIGH_COHERENCE': {
            'runs': 1,
            'products': 300000,
            'format': 'ttl',
            'description': 'High coherence: Dense product data with complete attributes'
        },
        'BSBM_LOW_COHERENCE': {
            'runs': 1,
            'products': 200000,  # Fewer products, more variation in attribute coverage
            'format': 'ttl',
            'description': 'Low coherence: Sparse product data with varied attributes'
        },
        
        # =======================================================================
        # LUBM - Lehigh University Benchmark
        # =======================================================================
        'LUBM_HIGH_COHERENCE': {
            'runs': 1,
            'universities': 50,
            'seed': 0,
            'description': 'High coherence: Standard LUBM with complete university structures'
        },
        'LUBM_LOW_COHERENCE': {
            'runs': 1,
            'universities': 30,
            'seed': 42,
            'description': 'Low coherence: Reduced universities for baseline comparison'
        },
        
        # =======================================================================
        # GAIA - Ontology Instance Generator
        # =======================================================================
        'GAIA_LUBM_HIGH_COHERENCE': {
            'runs': 1,
            'instances': 80000,
            'materialization': True,  # Full materialization = complete property coverage
            'description': 'High coherence: Full materialization ensures complete property sets'
        },
        'GAIA_LUBM_LOW_COHERENCE': {
            'runs': 1,
            'instances': 80000,
            'materialization': False,  # No materialization = sparse/incomplete properties
            'description': 'Low coherence: No materialization results in sparse property coverage'
        },
        
        # =======================================================================
        # LINKGEN - Flexible Linked Data Generator
        # =======================================================================
        'LINKGEN_LUBM_HIGH_COHERENCE': {
            'runs': 1,
            'triples': 2000000,
            'ontology': 'univ-bench.owl',
            'distribution': 'gaussian',  # Gaussian = more uniform distribution
            'gaussian_mean': 50,          # Centered mean for uniform-like coverage
            'gaussian_deviation': 10,     # Low deviation = consistent property usage
            'threads': 4,
            'description': 'High coherence: LUBM schema with gaussian distribution'
        },
        'LINKGEN_LUBM_LOW_COHERENCE': {
            'runs': 1,
            'triples': 2000000,
            'ontology': 'univ-bench.owl',
            'distribution': 'zipf',
            'threads': 4,
            'description': 'Low coherence: LUBM schema with Zipf distribution'
        },
        
        # =======================================================================
        # PYGRAFT - Schema and Knowledge Graph Generator
        # Configured to approximate LUBM ontology structure:
        # - LUBM has ~43 classes, ~32 properties, hierarchy depth ~3-4
        # =======================================================================
        'PYGRAFT_LUBM_HIGH_COHERENCE': {
            'runs': 1,
            'mode': 'full',
            # --- EXACT same schema as LOW_COHERENCE (which works) ---
            'classes': 43,              # Same as low coherence
            'relations': 32,            # Same as low coherence
            'max_depth': 4,             # Same as low coherence
            # --- HIGH COHERENCE: more instances, same proportions ---
            'avg_instances': 150,       # Increased from 50 for longer execution
            'std_instances': 40,        # SAME as low (required for stability)
            'avg_relations': 5,         # Higher than low (2) for more property coverage
            'std_relations': 1,         # Lower than low (2) = more consistent relations
            'p_subclass': 0.25,         # Same as low coherence
            'p_disjoint': 0.10,         # Same as low coherence
            'p_inverse': 0.25,          # Same as low coherence
            'p_functional': 0.05,       # Same as low coherence
            'p_symmetric': 0.15,        # Same as low coherence
            'p_transitive': 0.15,       # Same as low coherence
            'seed': 42,                 # Same seed
            'description': 'High coherence: Same schema, more relations per instance'
        },
        'PYGRAFT_LUBM_LOW_COHERENCE': {
            'runs': 1,
            'mode': 'full',
            # --- EXACT same schema as HIGH_COHERENCE (required for stability) ---
            'classes': 43,              # Same as high coherence
            'relations': 32,            # Same as high coherence
            'max_depth': 4,             # Same as high coherence
            # --- LOW COHERENCE parameters (differ in relations per instance) ---
            'avg_instances': 150,       # Increased from 50 for longer execution
            'std_instances': 40,        # Same as high (required for stability)
            'avg_relations': 2,         # Lower than high (5) = sparse property coverage
            'std_relations': 2,         # Higher than high (1) = varied relation counts
            'p_subclass': 0.25,         # Same as high coherence
            'p_disjoint': 0.10,         # Same as high coherence
            'p_inverse': 0.25,          # Same as high coherence
            'p_functional': 0.05,       # Same as high coherence
            'p_symmetric': 0.15,        # Same as high coherence
            'p_transitive': 0.15,       # Same as high coherence
            'seed': 42,                 # Same seed
            'description': 'Low coherence: Same schema, fewer relations per instance'
        },
        
        # =======================================================================
        # RDFGRAPHGEN - SHACL-based Generator
        # =======================================================================
        'RDFGRAPHGEN_LUBM_HIGH_COHERENCE': {
            'runs': 1,
            'shape': 'lubm_shacl.ttl',
            'scale_factor': 3000,    # Higher scale = more complete data per shape
            'description': 'High coherence: High scale factor ensures complete shape conformance'
        },
        'RDFGRAPHGEN_LUBM_LOW_COHERENCE': {
            'runs': 1,
            'shape': 'lubm_shacl.ttl',
            'scale_factor': 2500,    # Increased from 500 to balance execution time
            'description': 'Low coherence: Lower scale factor results in sparser data'
        },
        
        # =======================================================================
        # RUDOFGENERATE - ShEx/SHACL-based High-Performance Generator
        # =======================================================================
        'RUDOFGENERATE_LUBM_SHEX_HIGH_COHERENCE': {
            'runs': 1,
            'schema': 'lubm.shex',
            'config_file': 'benchmark_config_high_coherence.toml',
            'description': 'High coherence: ShEx schema with maximum property coverage config'
        },
        'RUDOFGENERATE_LUBM_SHEX_LOW_COHERENCE': {
            'runs': 1,
            'schema': 'lubm.shex',
            'config_file': 'benchmark_config_low_coherence.toml',
            'description': 'Low coherence: ShEx schema with minimum/random property coverage config'
        },
        'RUDOFGENERATE_LUBM_SHACL_HIGH_COHERENCE': {
            'runs': 1,
            'schema': 'lubm_shacl.ttl',
            'config_file': 'benchmark_config_high_coherence.toml',
            'description': 'High coherence: SHACL schema with maximum cardinality strategy'
        },
        'RUDOFGENERATE_LUBM_SHACL_LOW_COHERENCE': {
            'runs': 1,
            'schema': 'lubm_shacl.ttl',  # Same schema, different config
            'config_file': 'benchmark_config_low_coherence.toml',
            'description': 'Low coherence: SHACL schema with minimum cardinality strategy'
        }
        
        
    }

def main():
    parser = argparse.ArgumentParser(
        description='Generate datasets from all RDF synthetic data generators',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Generate all datasets:
    python3 generate_all_datasets.py
    
  Generate specific datasets:
    python3 generate_all_datasets.py --generators BSBM LUBM RUDOFGENERATE
    
  Generate with custom dataset directory:
    python3 generate_all_datasets.py --dataset-dir my-datasets
        """
    )
    
    parser.add_argument('--generators', nargs='*', 
                       choices=['BSBM_HIGH_COHERENCE', 'BSBM_LOW_COHERENCE',
                               'LUBM_HIGH_COHERENCE', 'LUBM_LOW_COHERENCE',
                               'GAIA_LUBM_HIGH_COHERENCE', 'GAIA_LUBM_LOW_COHERENCE',
                               'LINKGEN_LUBM_HIGH_COHERENCE', 'LINKGEN_LUBM_LOW_COHERENCE',
                               'PYGRAFT_LUBM_HIGH_COHERENCE', 'PYGRAFT_LUBM_LOW_COHERENCE',
                               'RDFGRAPHGEN_LUBM_HIGH_COHERENCE', 'RDFGRAPHGEN_LUBM_LOW_COHERENCE',
                               'RUDOFGENERATE_LUBM_SHEX_HIGH_COHERENCE', 'RUDOFGENERATE_LUBM_SHEX_LOW_COHERENCE',
                               'RUDOFGENERATE_LUBM_SHACL_HIGH_COHERENCE', 'RUDOFGENERATE_LUBM_SHACL_LOW_COHERENCE',
                               'ALL'],
                       default=['ALL'],
                       help='Generators to run (default: ALL)')
    
    parser.add_argument('--dataset-dir', type=str, default='1-Datasets',
                       help='Directory to save datasets (default: 1-Datasets)')
    
    args = parser.parse_args()
    
    # Determine which generators to run
    if not args.generators or 'ALL' in args.generators:
        selected_generators = ['BSBM_HIGH_COHERENCE', 'BSBM_LOW_COHERENCE',
                               'LUBM_HIGH_COHERENCE', 'LUBM_LOW_COHERENCE',
                               'GAIA_LUBM_HIGH_COHERENCE', 'GAIA_LUBM_LOW_COHERENCE',
                               'LINKGEN_LUBM_HIGH_COHERENCE', 'LINKGEN_LUBM_LOW_COHERENCE',
                               'PYGRAFT_LUBM_HIGH_COHERENCE', 'PYGRAFT_LUBM_LOW_COHERENCE',
                               'RDFGRAPHGEN_LUBM_HIGH_COHERENCE', 'RDFGRAPHGEN_LUBM_LOW_COHERENCE',
                               'RUDOFGENERATE_LUBM_SHEX_HIGH_COHERENCE', 'RUDOFGENERATE_LUBM_SHEX_LOW_COHERENCE',
                               'RUDOFGENERATE_LUBM_SHACL_HIGH_COHERENCE', 'RUDOFGENERATE_LUBM_SHACL_LOW_COHERENCE']
    else:
        selected_generators = args.generators
    
    # Base directory
    base_dir = Path(__file__).parent
    dataset_dir = base_dir / args.dataset_dir
    
    # Create dataset directory if it doesn't exist
    if not dataset_dir.exists():
        print(f"📁 Creating dataset directory: {dataset_dir}")
        dataset_dir.mkdir(parents=True, exist_ok=True)
    else:
        print(f"📁 Using existing dataset directory: {dataset_dir}")
    
    print(f"\n{'='*80}")
    print(f"🚀 RDF DATASET GENERATION")
    print(f"{'='*80}")
    print(f"Dataset directory: {dataset_dir.absolute()}")
    print(f"Generators: {', '.join(selected_generators)}")
    print(f"{'='*80}\n")
    
    results = {}
    
    # Get configurations
    configs = get_benchmark_configurations()
    
    # Generator class mapping
    generator_classes = {
        'BSBM_HIGH_COHERENCE': BSBMGenerator,
        'BSBM_LOW_COHERENCE': BSBMGenerator,
        'LUBM_HIGH_COHERENCE': LUBMGenerator,
        'LUBM_LOW_COHERENCE': LUBMGenerator,
        'GAIA_LUBM_HIGH_COHERENCE': GAIAGenerator,
        'GAIA_LUBM_LOW_COHERENCE': GAIAGenerator,
        'LINKGEN_LUBM_HIGH_COHERENCE': LINKGENGenerator,
        'LINKGEN_LUBM_LOW_COHERENCE': LINKGENGenerator,
        'PYGRAFT_LUBM_HIGH_COHERENCE': PyGraftGenerator,
        'PYGRAFT_LUBM_LOW_COHERENCE': PyGraftGenerator,
        'RDFGRAPHGEN_LUBM_HIGH_COHERENCE': RDFGraphGenGenerator,
        'RDFGRAPHGEN_LUBM_LOW_COHERENCE': RDFGraphGenGenerator,
        'RUDOFGENERATE_LUBM_SHEX_HIGH_COHERENCE': RUDOFGenerateGenerator,
        'RUDOFGENERATE_LUBM_SHEX_LOW_COHERENCE': RUDOFGenerateGenerator,
        'RUDOFGENERATE_LUBM_SHACL_HIGH_COHERENCE': RUDOFGenerateGenerator,
        'RUDOFGENERATE_LUBM_SHACL_LOW_COHERENCE': RUDOFGenerateGenerator,
    }

    # Generate datasets
    try:
        for gen_name in selected_generators:
            if gen_name in generator_classes and gen_name in configs:
                # Get config and extract runs
                config = configs[gen_name].copy()
                runs = config.pop('runs', 1)
                # Remove description from config (not a generator parameter)
                config.pop('description', None)
                
                gen_class = generator_classes[gen_name]
                
                # Determine source directory (handle variants)
                if 'RUDOFGENERATE' in gen_name:
                    source_dir_name = 'RUDOFGENERATE'
                elif 'RDFGRAPHGEN' in gen_name:
                    source_dir_name = 'RDFGRAPHGEN'
                elif 'LINKGEN' in gen_name:
                    source_dir_name = 'LINKGEN'
                elif 'GAIA' in gen_name:
                    source_dir_name = 'GAIA'
                elif 'PYGRAFT' in gen_name:
                    source_dir_name = 'PYGRAFT'
                elif 'LUBM' in gen_name:
                    source_dir_name = 'LUBM'
                elif 'BSBM' in gen_name:
                    source_dir_name = 'BSBM'
                else:
                    source_dir_name = gen_name
                
                print(f"\n🔄 Running {gen_name} generator ({runs} runs)...")
                
                # Execute runs
                gen_success = True
                for i in range(runs):
                    if runs > 1:
                        print(f"   ▶ Run {i+1}/{runs}")
                    
                    gen = gen_class(gen_name, base_dir / source_dir_name, dataset_dir)
                    success = gen.generate(**config)
                    
                    if not success:
                        gen_success = False
                        print(f"   ❌ Run {i+1} failed")
                
                results[gen_name] = gen_success

            elif gen_name not in generator_classes:
                print(f"⚠️  Unknown generator: {gen_name}")
            elif gen_name not in configs:
                print(f"⚠️  No configuration found for generator: {gen_name}")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"📊 GENERATION SUMMARY")
    print(f"{'='*80}")
    
    successful = [name for name, success in results.items() if success]
    failed = [name for name, success in results.items() if not success]
    
    print(f"\n✅ Successful: {len(successful)}/{len(results)}")
    for name in successful:
        # Find the run folder that was just created
        generator_folder = dataset_dir / name
        runs = sorted([d for d in generator_folder.iterdir() if d.is_dir() and d.name.startswith('run_')],
                     key=lambda x: int(x.name.split('_')[1]))
        if runs:
            latest_run = runs[-1].name
            print(f"   • {name} → {name}/{latest_run}/")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)}/{len(results)}")
        for name in failed:
            print(f"   • {name}")
    
    print(f"\n📁 Datasets saved to: {dataset_dir.absolute()}")
    print(f"{'='*80}\n")
    
    # Create index file
    index_file = dataset_dir / 'INDEX.md'
    with open(index_file, 'w') as f:
        f.write("# RDF Synthetic Data Generators - Dataset Index\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Available Datasets\n\n")
        
        # List all generators and their runs
        for generator_name in sorted([d.name for d in dataset_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]):
            f.write(f"### {generator_name}\n\n")
            
            generator_folder = dataset_dir / generator_name
            runs = sorted([d for d in generator_folder.iterdir() if d.is_dir() and d.name.startswith('run_')],
                         key=lambda x: int(x.name.split('_')[1]))
            
            if runs:
                f.write(f"**Total runs**: {len(runs)}\n\n")
                
                for run_folder in runs:
                    run_num = run_folder.name.split('_')[1]
                    f.write(f"#### Run {run_num}\n")
                    f.write(f"- **Location**: `{generator_name}/{run_folder.name}/`\n")
                    
                    # Read metadata
                    metadata_file = run_folder / 'metadata.json'
                    if metadata_file.exists():
                        with open(metadata_file) as mf:
                            metadata = json.load(mf)
                            f.write(f"- **Description**: {metadata.get('description', 'N/A')}\n")
                            f.write(f"- **Generated**: {metadata.get('generated_at', 'N/A')}\n")
                            if 'files' in metadata:
                                f.write(f"- **Files**: {', '.join(metadata.get('files', []))}\n")
                            if 'configuration' in metadata:
                                f.write(f"- **Configuration**: {metadata.get('configuration')}\n")
                    
                    f.write("\n")
            else:
                f.write("No runs available yet.\n\n")
    
    print(f"📋 Index file created: {index_file}")
    
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
