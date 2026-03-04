#!/usr/bin/env python3
"""
LINKGEN (Linked Data Generator) - Benchmark Execution Script
Generates synthetic RDF data based on ontologies with statistical distributions
"""

import subprocess
import json
import time
import argparse
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path


def create_config_file(args, script_dir, output_dir):
    """
    Create a config.properties file based on command-line arguments
    
    Args:
        args: Parsed command-line arguments
        script_dir: Directory where the script is located
        output_dir: Directory for output files
        
    Returns:
        Path to the created config file
    """
    config_content = f"""# LINKGEN Configuration - Auto-generated
# Generated at: {datetime.now().isoformat()}

# Namespace
namespace=http://edu.wright.daselab.linkgen/generator/

# Debug and stream mode
debug.mode=false
stream.mode=false
quad.format={str(args.format == 'nq').lower()}
max.thread={args.threads}

# File paths
file.basedir={script_dir}
file.log4j.properties={script_dir}/log4j.properties

# Ontology file
file.input.ontology={script_dir}/{args.ontology}

# Output directory
file.output.prefix={output_dir}
file.output.data.prefix={output_dir}/{args.output_name}_
file.output.log={output_dir}/out.log

# Number of triples
num.distinct.triples={args.triples}
num.triples.per.stream=10000
num.triples.per.output={args.triples_per_file}
max.file.size={args.max_file_size}
num.avg.frequency.subject={args.avg_frequency}

# Statistical distribution
distribution.function={args.distribution}
zipf.exponent={args.zipf_exponent}
gaussian.mean={int(args.gaussian_mean)}
gaussian.deviation={int(args.gaussian_deviation)}

# Noise generation
gen.noise={str(args.noise).lower()}
noise.data.total={args.noise_total}
noise.data.num.notype={args.noise_notype}
noise.data.num.invalid={args.noise_invalid}
noise.data.num.duplicate={args.noise_duplicate}

# SameAs/Alignment
gen.sameas={str(args.sameas).lower()}
file.entity={script_dir}/entity.nt

# VoID
file.output.void={output_dir}/void.ttl

# Datatypes - random seeds
randseed.xsd.string=10
randseed.xsd.boolean=1
randseed.xsd.int=2
randseed.xsd.float=1
randseed.xsd.double=2
randseed.xsd.long=2
randseed.xsd.others=5

# Number of unique values for datatypes
num.string={args.num_strings}
num.float=10
num.int=10
num.double=10
num.long=10
num.others=10
"""
    
    # Create temporary config file
    config_file = script_dir / "config_temp.properties"
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    return config_file


def create_log4j_properties(script_dir):
    """Create a simple log4j.properties file"""
    log4j_content = """# Log4j Configuration for LINKGEN
log4j.rootLogger=INFO, stdout, file

# Console appender
log4j.appender.stdout=org.apache.log4j.ConsoleAppender
log4j.appender.stdout.Target=System.out
log4j.appender.stdout.layout=org.apache.log4j.PatternLayout
log4j.appender.stdout.layout.ConversionPattern=%d{yyyy-MM-dd HH:mm:ss} %-5p %c{1}:%L - %m%n

# File appender
log4j.appender.file=org.apache.log4j.FileAppender
log4j.appender.file.File=output/linkgen.log
log4j.appender.file.layout=org.apache.log4j.PatternLayout
log4j.appender.file.layout.ConversionPattern=%d{yyyy-MM-dd HH:mm:ss} %-5p %c{1}:%L - %m%n
"""
    
    log4j_file = script_dir / "log4j.properties"
    if not log4j_file.exists():
        with open(log4j_file, 'w') as f:
            f.write(log4j_content)
    
    return log4j_file


def parse_void_triples(void_file_path):
    """Parse void.ttl file to extract the total triples count"""
    if not void_file_path.exists():
        return 0
    
    try:
        content = void_file_path.read_text()
        # Look for void:triples 2928 ; pattern
        # Handles potential whitespace variations
        match = re.search(r'void:triples\s+(\d+)\s*;', content)
        if match:
            return int(match.group(1))
    except Exception as e:
        print(f"Warning: Failed to parse void.ttl: {e}")
    
    return 0


def run_linkgen_generator(args):
    """
    Run LINKGEN generator and collect metrics
    
    Args:
        args: Parsed command-line arguments
    """
    
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.resolve()
    
    # Prepare output directory
    output_dir = script_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Clean old output files to ensure we detect generation failures
    # Keep the directory but remove data files and void.ttl
    for old_file in output_dir.glob("data_*"):
        old_file.unlink()
    void_file_old = output_dir / "void.ttl"
    if void_file_old.exists():
        void_file_old.unlink()
    
    # Create log4j properties if it doesn't exist
    create_log4j_properties(script_dir)
    
    # Create configuration file
    config_file = create_config_file(args, script_dir, output_dir)
    
    # Build classpath with all JAR files
    lib_dir = script_dir / "lib"
    classpath_parts = [str(script_dir / "linkgen.jar")]
    if lib_dir.exists():
        classpath_parts.extend([str(jar) for jar in lib_dir.glob("*.jar")])
    classpath = ":".join(classpath_parts)
    
    # Build command
    cmd = [
        "java",
        "-Xmx4G",
        "-cp", classpath,
        "edu.wright.daselab.linkgen.Generator",
        "-c", str(config_file)
    ]
    
    print(f"Running LINKGEN Generator...")
    print(f"Ontology: {args.ontology}")
    print(f"Triples: {args.triples:,}")
    print(f"Distribution: {args.distribution}")
    print(f"Threads: {args.threads}")
    print("=" * 60)
    
    # Run generator
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception on non-zero exit
            cwd=script_dir
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Check if generation actually succeeded by looking for output files
        # LINKGEN may return exit code 1 even on success
        file_stats = count_output_files(output_dir, args.output_name, args.format)
        if file_stats['file_count'] == 0 and result.returncode != 0:
            # No files generated and non-zero exit - real error
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        
        # Parse output to extract metrics
        metrics = parse_generator_output(result.stdout, result.stderr)
        
        # Parse void.ttl for accurate triple count
        void_file = output_dir / "void.ttl"
        actual_triples = parse_void_triples(void_file)
        if actual_triples > 0:
            metrics['triples_generated'] = actual_triples
            # Override args.triples for throughput calculation if we have actual data
            # But we keep args.triples in 'triples_requested'
        
        # Print summary
        print("\n" + "=" * 60)
        print("✅ LINKGEN Generation Complete!")
        print("=" * 60)
        print(f"⏱️  Execution Time: {execution_time:.2f} seconds")
        print(f"🔢 Triples Requested: {args.triples:,}")
        print(f"🔢 Triples Generated (VoID): {metrics.get('triples_generated', 0):,}")
        print(f"📊 Files Generated: {file_stats['file_count']}")
        print(f"💾 Total Size: {file_stats['total_size_mb']:.2f} MB")
        
        # Calculate throughput using actual triples if available, else requested
        throughput_triples = metrics.get('triples_generated', args.triples)
        if execution_time > 0:
            print(f"⚡ Throughput: {throughput_triples / execution_time:,.0f} triples/sec")
            
        print(f"📁 Output Format: {args.format.upper()}")
        print(f"📂 Output Location: {output_dir}")
        print("=" * 60)
        
        # Create detailed report
        report = create_benchmark_report(
            args, execution_time, metrics, file_stats
        )
        
        # Save report
        report_path = output_dir / "benchmark_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Detailed report saved to: {report_path}")
        
        # Clean up temporary config file
        if config_file.exists():
            config_file.unlink()
        
        return report
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running LINKGEN generator:")
        print(f"Exit code: {e.returncode}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        
        # Clean up temporary config file
        if config_file.exists():
            config_file.unlink()
        
        raise


def parse_generator_output(stdout, stderr):
    """Parse LINKGEN generator output to extract metrics"""
    metrics = {
        'classes_processed': 0,
        'instances_generated': 0,
        'triples_generated': 0
    }
    
    combined_output = stdout + "\n" + stderr
    lines = combined_output.split('\n')
    
    for line in lines:
        # Try to extract various metrics from the output
        if 'class' in line.lower() and 'instance' in line.lower():
            # Extract class and instance counts
            numbers = re.findall(r'\d+', line)
            if numbers:
                metrics['instances_generated'] = int(numbers[-1])
        
        if 'triple' in line.lower() or 'quad' in line.lower():
            numbers = re.findall(r'\d+', line)
            if numbers:
                metrics['triples_generated'] = int(numbers[-1])
    
    return metrics


def count_output_files(output_dir, output_name, format_type):
    """Count and measure generated output files"""
    stats = {
        'file_count': 0,
        'total_size': 0,
        'total_size_mb': 0,
        'files': []
    }
    
    # Find all output files matching the pattern
    pattern = f"{output_name}_*"
    for file_path in output_dir.glob(pattern):
        if file_path.is_file() and not file_path.name.endswith('.log'):
            size = file_path.stat().st_size
            stats['file_count'] += 1
            stats['total_size'] += size
            stats['files'].append({
                'name': file_path.name,
                'size': size,
                'size_mb': size / (1024 * 1024)
            })
    
    stats['total_size_mb'] = stats['total_size'] / (1024 * 1024)
    
    return stats


def create_benchmark_report(args, execution_time, metrics, file_stats):
    """Create a comprehensive benchmark report"""
    
    # Use actual generated triples if available, otherwise fallback to requested
    triples_count = metrics.get('triples_generated', 0)
    if triples_count == 0:
        triples_count = args.triples

    report = {
        "benchmark": "LINKGEN",
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "ontology": args.ontology,
            "triples": args.triples,
            "distribution": args.distribution,
            "zipf_exponent": args.zipf_exponent if args.distribution == "zipf" else None,
            "gaussian_mean": args.gaussian_mean if args.distribution == "gaussian" else None,
            "gaussian_deviation": args.gaussian_deviation if args.distribution == "gaussian" else None,
            "format": args.format,
            "threads": args.threads,
            "output_name": args.output_name,
            "noise_enabled": args.noise,
            "sameas_enabled": args.sameas
        },
        "execution": {
            "time_seconds": round(execution_time, 3),
            "time_formatted": f"{execution_time:.2f}s"
        },
        "generated_data": {
            "triples_requested": args.triples,
            "triples_total": triples_count,
            "files_generated": file_stats['file_count'],
            "total_size_bytes": file_stats['total_size'],
            "total_size_mb": round(file_stats['total_size_mb'], 2)
        },
        "performance_metrics": {
            "triples_per_second": round(triples_count / execution_time, 2) if execution_time > 0 else 0,
            "mb_per_second": round(file_stats['total_size_mb'] / execution_time, 2) if execution_time > 0 else 0
        },
        "files": file_stats['files'][:10]  # Include first 10 files
    }
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description='LINKGEN Benchmark - Synthetic Linked Data Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 100K triples with DBpedia ontology
  python execute_benchmark.py --triples 100000 --ontology dbpedia_2015.owl
  
  # Generate with Schema.org and Gaussian distribution
  python execute_benchmark.py --triples 50000 --ontology schemaorg.owl --distribution gaussian
  
  # Generate with custom Zipf exponent and 4 threads
  python execute_benchmark.py --triples 200000 --zipf-exponent 2.5 --threads 4
        """
    )
    
    # Core parameters
    parser.add_argument('--triples', type=int, default=100000,
                        help='Number of distinct triples to generate (default: 100000)')
    
    parser.add_argument('--ontology', type=str, default='dbpedia_2015.owl',
                        choices=['dbpedia_2015.owl', 'schemaorg.owl', 'univ-bench.owl'],
                        help='Ontology file to use (default: dbpedia_2015.owl)')
    
    parser.add_argument('--distribution', type=str, default='zipf',
                        choices=['zipf', 'gaussian'],
                        help='Statistical distribution function (default: zipf)')
    
    parser.add_argument('--zipf-exponent', type=float, default=2.1,
                        help='Zipf exponent value (default: 2.1, range: 2.0-3.0)')
    
    parser.add_argument('--gaussian-mean', type=float, default=200,
                        help='Gaussian mean value (default: 200)')
    
    parser.add_argument('--gaussian-deviation', type=float, default=15,
                        help='Gaussian standard deviation (default: 15)')
    
    parser.add_argument('--threads', type=int, default=2,
                        help='Number of threads to use (default: 2)')
    
    parser.add_argument('--format', type=str, default='nt',
                        choices=['nt', 'nq'],
                        help='Output format: nt (N-Triples) or nq (N-Quads) (default: nt)')
    
    parser.add_argument('--output-name', type=str, default='data',
                        help='Base name for output files (default: data)')
    
    # Advanced parameters
    parser.add_argument('--triples-per-file', type=int, default=100000,
                        help='Number of triples per output file (default: 100000)')
    
    parser.add_argument('--max-file-size', type=int, default=100000000,
                        help='Maximum file size in bytes (default: 100000000 = 100MB)')
    
    parser.add_argument('--avg-frequency', type=int, default=5,
                        help='Average frequency of subject (default: 5)')
    
    parser.add_argument('--num-strings', type=int, default=10,
                        help='Number of unique string values (default: 10)')
    
    # Noise parameters
    parser.add_argument('--noise', type=bool, default=True,
                        help='Generate noise data (default: True)')
    
    parser.add_argument('--noise-total', type=int, default=10000,
                        help='Total noise data instances (default: 10000)')
    
    parser.add_argument('--noise-notype', type=int, default=100,
                        help='Noise instances without type (default: 100)')
    
    parser.add_argument('--noise-invalid', type=int, default=100,
                        help='Invalid noise instances (default: 100)')
    
    parser.add_argument('--noise-duplicate', type=int, default=1000,
                        help='Duplicate noise instances (default: 1000)')
    
    # SameAs linking
    parser.add_argument('--sameas', type=bool, default=False,
                        help='Generate sameAs links (default: False)')
    
    args = parser.parse_args()
    
    try:
        run_linkgen_generator(args)
    except Exception as e:
        print(f"\n❌ Benchmark execution failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
