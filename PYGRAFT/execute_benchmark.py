#!/usr/bin/env python3
"""
PyGraft Benchmark - Synthetic Knowledge Graph Generator
Generates schemas and knowledge graphs using PyGraft
"""

import json
import time
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


def create_yaml_config(args, work_dir):
    """
    Create a PyGraft YAML configuration file based on command-line arguments
    
    Args:
        args: Parsed command-line arguments
        work_dir: Working directory where config file will be created
        
    Returns:
        Path to the created config file
    """
    
    # Determine mode-specific output folder name
    if args.mode == 'full':
        mode_name = 'full'
    elif args.mode == 'schema':
        mode_name = 'schema'
    else:
        mode_name = 'kg'
    
    config_content = f"""# PyGraft Configuration - Auto-generated
# Generated at: {datetime.now().isoformat()}

# GENERAL ARGS #
schema_name: config
format: xml
verbose: {str(args.verbosity >= 1).lower()}

# SCHEMA ARGS #
## CLASSES ##
num_classes: {args.n_classes}
max_hierarchy_depth: {args.max_depth}
avg_class_depth: {args.max_depth / 2}
class_inheritance_ratio: {args.p_subclass * 10}
avg_disjointness: {args.p_disjoint}

## RELATIONS ##
num_relations: {args.n_relations}
relation_specificity: 2.5
prop_profiled_relations: 0.9
profile_side: both
prop_symmetric_relations: {args.p_symmetric}
prop_inverse_relations: {args.p_inverse}
prop_transitive_relations: {args.p_transitive}
prop_asymmetric_relations: {args.p_asymmetric}
prop_reflexive_relations: {args.p_reflexive}
prop_irreflexive_relations: {args.p_irreflexive}
prop_functional_relations: {args.p_functional}
prop_inverse_functional_relations: {args.p_inverse_functional}
prop_subproperties: {args.p_subproperty}

# KNOWLEDGE GRAPH ARGS ##
num_entities: {args.avg_instances * args.n_classes}
num_triples: {args.avg_relations * args.avg_instances * args.n_classes}
fast_gen: true
oversample: false
relation_balance_ratio: 0.9
prop_untyped_entities: 0.0
avg_depth_specific_class: {args.avg_instances / 25}
multityping: false
avg_multityping: 1.5
"""
    
    # Create config file in working directory
    config_file = Path(work_dir) / "config.yml"
    
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    return config_file


def run_pygraft_generator(args):
    """
    Run PyGraft generator with specified parameters
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        dict: Benchmark results with execution metrics
    """
    
    # Import PyGraft
    try:
        import pygraft
    except ImportError:
        print("❌ Error: PyGraft not installed. Install with: pip install pygraft")
        sys.exit(1)
    
    script_dir = Path(__file__).parent.absolute()
    final_output_dir = script_dir / args.output_dir
    
    # PyGraft creates its own output/ directory, so we work in script_dir
    # and will move files to final_output_dir after generation
    work_dir = script_dir
    
    print("=" * 60)
    print("🎯 PyGraft - Knowledge Graph Generator")
    print("=" * 60)
    print(f"Configuration:")
    print(f"  Mode: {args.mode}")
    print(f"  Classes: {args.n_classes}")
    print(f"  Relations: {args.n_relations}")
    print(f"  Avg Instances/Class: {args.avg_instances}")
    print(f"  Output Directory: {final_output_dir}")
    print(f"  Check Consistency: {args.check_consistency}")
    print(f"  Multitask: {args.multitask}")
    print(f"  Random Seed: {args.seed}")
    print("=" * 60)
    
    # Create configuration file in working directory
    print("\n📝 Creating configuration file...")
    config_file = create_yaml_config(args, work_dir)
    print(f"   Config saved to: {config_file}")
    
    # Set Java home if provided
    if args.java_home:
        os.environ['JAVA_HOME'] = args.java_home
        print(f"   JAVA_HOME set to: {args.java_home}")
    
    # Check JAVA_HOME
    java_home = os.environ.get('JAVA_HOME')
    if not java_home:
        print("\n⚠️  Warning: JAVA_HOME not set. PyGraft requires Java for HermiT reasoner.")
        print("   Set JAVA_HOME or disable consistency checking with --no-check-consistency")
    
    # Run PyGraft generation
    print(f"\n🚀 Starting PyGraft generation ({args.mode} mode)...")
    print("   This may take a few minutes depending on size...\n")
    
    start_time = time.time()
    
    try:
        # Change to working directory for PyGraft (it expects config in current directory)
        original_dir = os.getcwd()
        os.chdir(work_dir)
        
        # Run generation based on mode
        # PyGraft expects just the filename, not the full path
        config_filename = config_file.name
        
        if args.mode == 'schema':
            pygraft.generate_schema(config_filename)
            print("✅ Schema generation completed!")
        elif args.mode == 'kg':
            pygraft.generate_kg(config_filename)
            print("✅ Knowledge graph generation completed!")
        else:  # full
            pygraft.generate(config_filename)
            print("✅ Full pipeline (schema + KG) completed!")
        
        # Move PyGraft's output/config/ to our final_output_dir
        import shutil
        pygraft_output = work_dir / "output" / "config"
        if pygraft_output.exists():
            # Ensure final output directory exists
            os.makedirs(final_output_dir, exist_ok=True)
            
            # Move all files from PyGraft's output/config/ to final_output_dir
            for item in pygraft_output.glob('*'):
                dest = final_output_dir / item.name
                if dest.exists():
                    dest.unlink()
                shutil.move(str(item), str(final_output_dir))
            
            # Clean up PyGraft's output directory (but not if it's a mounted volume)
            try:
                # Remove the config subdirectory
                if pygraft_output.exists():
                    pygraft_output.rmdir()
                # Try to remove output directory if it's not a mount point
                output_parent = work_dir / "output"
                if output_parent.exists() and output_parent != final_output_dir:
                    # Only remove if empty
                    try:
                        output_parent.rmdir()
                    except OSError:
                        # Directory not empty or is a mount point, that's ok
                        pass
            except OSError:
                # Can't remove, probably a mount point
                pass
            print(f"   ✓ Moved generated files to {final_output_dir}")
        
        # Move config.yml to output directory
        if config_file.exists():
            dest_config = final_output_dir / config_file.name
            if dest_config.exists():
                dest_config.unlink()
            shutil.move(str(config_file), str(dest_config))
        
        os.chdir(original_dir)
        
    except Exception as e:
        print(f"\n❌ Error during PyGraft generation: {e}")
        os.chdir(original_dir)
        raise
    
    execution_time = time.time() - start_time
    
    # Collect output statistics
    print(f"\n⏱️  Execution time: {execution_time:.2f}s")
    print("\n📊 Analyzing generated files...")
    
    stats = analyze_output(final_output_dir, args.mode)
    
    # Create benchmark report
    report = create_benchmark_report(args, execution_time, stats, final_output_dir)
    
    return report


def analyze_output(output_dir, mode):
    """
    Analyze generated output files and collect statistics
    
    Args:
        output_dir: Directory containing output files
        mode: Generation mode (schema, kg, full)
        
    Returns:
        dict: Statistics about generated files
    """
    
    stats = {
        'files': [],
        'total_size_mb': 0,
        'triples_count': 0
    }
    
    # Find output subdirectory (PyGraft creates output/config/ structure)
    config_output = output_dir / "config"
    if config_output.exists():
        output_path = config_output
    else:
        output_path = output_dir
    
    # Check for generated files
    for file_path in output_path.glob('*'):
        if file_path.is_file():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            stats['files'].append({
                'name': file_path.name,
                'size_mb': round(size_mb, 2)
            })
            stats['total_size_mb'] += size_mb
            
            # Count triples in RDF files
            if file_path.suffix in ['.rdf', '.owl', '.ttl', '.nt']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Rough estimate: count lines with triple patterns
                        # For RDF/XML, count rdf:Description or similar tags
                        if file_path.suffix == '.rdf' or file_path.suffix == '.owl':
                            stats['triples_count'] += content.count('rdf:Description')
                            stats['triples_count'] += content.count('owl:Class')
                            stats['triples_count'] += content.count('owl:ObjectProperty')
                            stats['triples_count'] += content.count('owl:NamedIndividual')
                        else:
                            # For Turtle/N-Triples, count non-comment lines
                            lines = [l.strip() for l in content.split('\n') 
                                   if l.strip() and not l.strip().startswith('#')]
                            stats['triples_count'] += len(lines)
                except Exception as e:
                    print(f"   Warning: Could not analyze {file_path.name}: {e}")
    
    stats['total_size_mb'] = round(stats['total_size_mb'], 2)
    
    print(f"   Files generated: {len(stats['files'])}")
    print(f"   Total size: {stats['total_size_mb']} MB")
    print(f"   Estimated triples: {stats['triples_count']:,}")
    
    return stats


def create_benchmark_report(args, execution_time, stats, output_dir):
    """
    Create a comprehensive benchmark report in JSON format
    
    Args:
        args: Command-line arguments
        execution_time: Total execution time in seconds
        stats: Statistics from analyze_output()
        output_dir: Output directory path
        
    Returns:
        dict: Complete benchmark report
    """
    
    report = {
        "benchmark": "PYGRAFT",
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "mode": args.mode,
            "n_classes": args.n_classes,
            "n_relations": args.n_relations,
            "avg_instances_per_class": args.avg_instances,
            "std_instances_per_class": args.std_instances,
            "avg_relations_per_individual": args.avg_relations,
            "std_relations_per_individual": args.std_relations,
            "max_hierarchy_depth": args.max_depth,
            "check_consistency": args.check_consistency,
            "multitask": args.multitask,
            "seed": args.seed,
            "output_dir": str(output_dir)
        },
        "probabilities": {
            "subclass": args.p_subclass,
            "disjoint": args.p_disjoint,
            "subproperty": args.p_subproperty,
            "inverse": args.p_inverse,
            "functional": args.p_functional,
            "inverse_functional": args.p_inverse_functional,
            "symmetric": args.p_symmetric,
            "asymmetric": args.p_asymmetric,
            "transitive": args.p_transitive,
            "reflexive": args.p_reflexive,
            "irreflexive": args.p_irreflexive
        },
        "execution": {
            "time_seconds": round(execution_time, 2),
            "time_formatted": f"{execution_time:.2f}s"
        },
        "generated_data": {
            "files_generated": len(stats['files']),
            "total_size_mb": stats['total_size_mb'],
            "estimated_triples": stats['triples_count'],
            "files": stats['files']
        },
        "performance": {
            "triples_per_second": round(stats['triples_count'] / execution_time, 2) if execution_time > 0 else 0
        }
    }
    
    # Save report
    report_file = output_dir / "benchmark_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Benchmark report saved to: {report_file}")
    print("\n" + "=" * 60)
    print("✅ BENCHMARK COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"⏱️  Total time: {report['execution']['time_formatted']}")
    print(f"📊 Files: {report['generated_data']['files_generated']}")
    print(f"💾 Total size: {report['generated_data']['total_size_mb']} MB")
    print(f"📈 Estimated triples: {report['generated_data']['estimated_triples']:,}")
    print(f"⚡ Throughput: {report['performance']['triples_per_second']:,.2f} triples/sec")
    print("=" * 60)
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description='PyGraft Benchmark - Synthetic Knowledge Graph Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate schema with 50 classes
  python execute_benchmark.py --mode schema --n-classes 50
  
  # Generate full KG with 100 classes and 50 relations
  python execute_benchmark.py --mode full --n-classes 100 --n-relations 50
  
  # Large KG with high instance count
  python execute_benchmark.py --n-classes 200 --avg-instances 100 --multitask
        """
    )
    
    # Core parameters
    parser.add_argument('--mode', type=str, default='full',
                        choices=['schema', 'kg', 'full'],
                        help='Generation mode: schema, kg, or full (default: full)')
    
    parser.add_argument('--n-classes', type=int, default=50,
                        help='Number of classes in schema (default: 50)')
    
    parser.add_argument('--n-relations', type=int, default=30,
                        help='Number of relations/properties (default: 30)')
    
    parser.add_argument('--avg-instances', type=int, default=50,
                        help='Average instances per class (default: 50)')
    
    parser.add_argument('--std-instances', type=int, default=10,
                        help='Std deviation for instances per class (default: 10)')
    
    parser.add_argument('--avg-relations', type=int, default=3,
                        help='Average relations per individual (default: 3)')
    
    parser.add_argument('--std-relations', type=int, default=1,
                        help='Std deviation for relations per individual (default: 1)')
    
    # Schema structure parameters
    parser.add_argument('--max-depth', type=int, default=5,
                        help='Maximum hierarchy depth (default: 5)')
    
    parser.add_argument('--p-subclass', type=float, default=0.15,
                        help='Probability of subclass assertion (default: 0.15)')
    
    parser.add_argument('--p-disjoint', type=float, default=0.05,
                        help='Probability of disjoint classes (default: 0.05)')
    
    parser.add_argument('--p-subproperty', type=float, default=0.0,
                        help='Probability of sub-property (default: 0.0, conflicts with functional)')
    
    # Property characteristics
    parser.add_argument('--p-inverse', type=float, default=0.2,
                        help='Probability of inverse property (default: 0.2)')
    
    parser.add_argument('--p-functional', type=float, default=0.2,
                        help='Probability of functional property (default: 0.2)')
    
    parser.add_argument('--p-inverse-functional', type=float, default=0.1,
                        help='Probability of inverse functional (default: 0.1, conflicts with subproperty)')
    
    parser.add_argument('--p-symmetric', type=float, default=0.1,
                        help='Probability of symmetric property (default: 0.1)')
    
    parser.add_argument('--p-asymmetric', type=float, default=0.05,
                        help='Probability of asymmetric property (default: 0.05)')
    
    parser.add_argument('--p-transitive', type=float, default=0.1,
                        help='Probability of transitive property (default: 0.1)')
    
    parser.add_argument('--p-reflexive', type=float, default=0.05,
                        help='Probability of reflexive property (default: 0.05)')
    
    parser.add_argument('--p-irreflexive', type=float, default=0.05,
                        help='Probability of irreflexive property (default: 0.05)')
    
    # Advanced options
    parser.add_argument('--check-consistency', action='store_true', default=True,
                        help='Check logical consistency with HermiT (default: True)')
    
    parser.add_argument('--no-check-consistency', action='store_false', dest='check_consistency',
                        help='Disable consistency checking (faster but may produce inconsistent KGs)')
    
    parser.add_argument('--multitask', action='store_true', default=False,
                        help='Enable parallel processing (default: False)')
    
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility (default: 42)')
    
    parser.add_argument('--verbosity', type=int, default=1, choices=[0, 1, 2],
                        help='Log verbosity: 0=minimal, 1=normal, 2=verbose (default: 1)')
    
    parser.add_argument('--output-dir', type=str, default='output',
                        help='Output directory (default: output)')
    
    parser.add_argument('--java-home', type=str,
                        help='Path to JAVA_HOME (required for consistency checking)')
    
    args = parser.parse_args()
    
    try:
        run_pygraft_generator(args)
    except Exception as e:
        print(f"\n❌ Benchmark execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
