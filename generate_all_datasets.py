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
        print(f"🔵 GENERATING BSBM DATASET")
        print(f"{'='*80}")
        print(f"Products: {products:,}")
        print(f"Format: {format}")
        
        cmd = [
            'python3', 
            str(self.source_dir / 'execute_benchmark.py'),
            '--products', str(products),
            '--format', format
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
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
            return False


class LUBMGenerator(DatasetGenerator):
    """LUBM University benchmark generator"""
    
    def generate(self, universities=10, seed=0):
        print(f"\n{'='*80}")
        print(f"🔴 GENERATING LUBM DATASET")
        print(f"{'='*80}")
        print(f"Universities: {universities}")
        print(f"Seed: {seed}")
        
        cmd = [
            'python3',
            str(self.source_dir / 'execute_benchmark.py'),
            '--universities', str(universities),
            '--seed', str(seed)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
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
            return False


class GAIAGenerator(DatasetGenerator):
    """GAIA ontology instance generator"""
    
    def generate(self, instances=1000, materialization=True):
        print(f"\n{'='*80}")
        print(f"🟢 GENERATING GAIA DATASET")
        print(f"{'='*80}")
        print(f"Instances per class: {instances}")
        print(f"Materialization: {materialization}")
        
        cmd = [
            'python3',
            'execute_benchmark.py',
            '--instances', str(instances)
        ]
        
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
            return False


class LINKGENGenerator(DatasetGenerator):
    """LINKGEN flexible linked data generator"""
    
    def generate(self, triples=2000000, ontology='dbpedia_2015.owl', distribution='zipf', threads=4):
        print(f"\n{'='*80}")
        print(f"🟡 GENERATING LINKGEN DATASET")
        print(f"{'='*80}")
        print(f"Triples: {triples:,}")
        print(f"Ontology: {ontology}")
        print(f"Distribution: {distribution}")
        
        cmd = [
            'python3',
            str(self.source_dir / 'execute_benchmark.py'),
            '--triples', str(triples),
            '--ontology', ontology,
            '--distribution', distribution,
            '--threads', str(threads)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
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
            return False


class PyGraftGenerator(DatasetGenerator):
    """PyGraft schema and knowledge graph generator"""
    
    def generate(self, mode='full', classes=30, relations=20, avg_instances=80):
        print(f"\n{'='*80}")
        print(f"🟣 GENERATING PYGRAFT DATASET")
        print(f"{'='*80}")
        print(f"Mode: {mode}")
        print(f"Classes: {classes}")
        print(f"Relations: {relations}")
        print(f"Avg instances: {avg_instances}")
        
        cmd = [
            'docker', 'run', '--rm',
            '-v', f"{self.source_dir / 'output'}:/app/output",
            'pygraft-benchmark:latest',
            'python', 'execute_benchmark.py',
            '--mode', mode,
            '--n-classes', str(classes),
            '--n-relations', str(relations),
            '--avg-instances', str(avg_instances),
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
                    'avg_instances': avg_instances
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
        print(f"🟢 GENERATING RDFGRAPHGEN DATASET")
        print(f"{'='*80}")
        print(f"Shape: {shape}")
        print(f"Scale factor: {scale_factor}")
        
        cmd = [
            'python3',
            str(self.source_dir / 'execute_benchmark.py'),
            '--shape', shape,
            '--output', 'output-graph.ttl',
            '--scale-factor', str(scale_factor)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
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
        
        # Run using docker compose
        cmd = [
            'docker', 'compose', 'run', '--rm',
            '-e', f"CONFIG_FILE={config_file}",
            'rudofgenerate'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.source_dir)
        
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


def get_benchmark_configurations():
    """
    Returns the configuration parameters for each benchmark generator.
    Edit the values in this dictionary to configure the datasets.
    """
    return {
        'BSBM': {
            'runs': 1,
            'products': 100,
            'format': 'ttl'
        },
        'LUBM': {
            'runs': 1,
            'universities': 1,
            'seed': 0
        },
        'GAIA': {
            'runs': 1,
            'instances': 10,
            'materialization': True
        },
        'LINKGEN': {
            'runs': 1,
            'triples': 3000,
            'ontology': 'dbpedia_2015.owl',
            'distribution': 'zipf',
            'threads': 4
        },
        'PYGRAFT': {
            'runs': 1,
            'mode': 'full',
            'classes': 30,
            'relations': 20,
            'avg_instances': 80
        },
        'RDFGRAPHGEN': {
            'runs': 1,
            'shape': 'input-shape.ttl',
            'scale_factor': 10
        },
        'RDFGRAPHGEN_LUBM': {
            'runs': 1,
            'shape': 'lubm_shacl.ttl',
            'scale_factor': 10
        },
        'RUDOFGENERATE': {
            'runs': 1,
            'schema': 'example_schema.shex',
            'config_file': 'benchmark_config.toml'
        },
        'RUDOFGENERATE_LUBM_SHEX': {
            'runs': 1,
            'schema': 'lubm.shex',
            'config_file': 'benchmark_config.toml'
        },
        'RUDOFGENERATE_LUBM_SHACL': {
            'runs': 1,
            'schema': 'lubm_shacl.ttl',
            'config_file': 'benchmark_config.toml'
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
                       choices=['BSBM', 'LUBM', 'GAIA', 'LINKGEN', 'PYGRAFT', 
                               'RDFGRAPHGEN', 'RDFGRAPHGEN_LUBM', 
                               'RUDOFGENERATE', 'RUDOFGENERATE_LUBM_SHEX', 'RUDOFGENERATE_LUBM_SHACL', 'ALL'],
                       default=['ALL'],
                       help='Generators to run (default: ALL)')
    
    parser.add_argument('--dataset-dir', type=str, default='1-Datasets',
                       help='Directory to save datasets (default: 1-Datasets)')
    
    args = parser.parse_args()
    
    # Determine which generators to run
    if not args.generators or 'ALL' in args.generators:
        selected_generators = ['BSBM', 'LUBM', 'GAIA', 'LINKGEN', 'PYGRAFT', 
                               'RDFGRAPHGEN', 'RDFGRAPHGEN_LUBM', 
                               'RUDOFGENERATE', 'RUDOFGENERATE_LUBM_SHEX', 'RUDOFGENERATE_LUBM_SHACL']
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
        'BSBM': BSBMGenerator,
        'LUBM': LUBMGenerator,
        'GAIA': GAIAGenerator,
        'LINKGEN': LINKGENGenerator,
        'PYGRAFT': PyGraftGenerator,
        'RDFGRAPHGEN': RDFGraphGenGenerator,
        'RDFGRAPHGEN_LUBM': RDFGraphGenGenerator,
        'RUDOFGENERATE': RUDOFGenerateGenerator,
        'RUDOFGENERATE_LUBM_SHEX': RUDOFGenerateGenerator,
        'RUDOFGENERATE_LUBM_SHACL': RUDOFGenerateGenerator
    }

    # Generate datasets
    try:
        for gen_name in selected_generators:
            if gen_name in generator_classes and gen_name in configs:
                # Get config and extract runs
                config = configs[gen_name].copy()
                runs = config.pop('runs', 1)
                
                gen_class = generator_classes[gen_name]
                
                # Determine source directory (handle variants)
                source_dir_name = gen_name
                if gen_name.startswith('RUDOFGENERATE'):
                    source_dir_name = 'RUDOFGENERATE'
                elif gen_name == 'RDFGRAPHGEN_LUBM':
                    source_dir_name = 'RDFGRAPHGEN'
                
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
