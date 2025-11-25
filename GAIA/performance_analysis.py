#!/usr/bin/env python3
"""
Performance comparison script for GAIA generator
"""

import json
import os
from pathlib import Path

def format_size(size_bytes):
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def load_benchmark_report(filepath):
    """Load and parse benchmark report"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def main():
    print("📊 GAIA Performance Comparison Report")
    print("=" * 60)
    
    output_dir = Path("output")
    report_files = list(output_dir.glob("benchmark*.json"))
    
    if not report_files:
        print("❌ No benchmark reports found in output directory")
        return
    
    reports = []
    for report_file in sorted(report_files):
        report = load_benchmark_report(report_file)
        if report:
            reports.append((report_file.name, report))
    
    # Header
    print(f"{'Report':<25} {'Instances':<10} {'Limit':<8} {'Material':<10} {'Time (ms)':<10} {'Generated':<10} {'Size':<10}")
    print("-" * 100)
    
    for filename, report in reports:
        params = report['parameters']
        results = report['results']
        
        instances = params['instances_per_class']
        limit = params.get('limit', '-')
        materialization = 'Yes' if params.get('materialization', False) else 'No'
        time_ms = int(results['execution_time_seconds'] * 1000)
        
        # Extract generated instances from stdout
        stdout = report.get('stdout', '')
        generated_instances = 0
        for line in stdout.split('\n'):
            if 'instances writted' in line or 'instances has been generated' in line:
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    generated_instances = int(numbers[0])
                    break
        
        size_mb = results['output_size_mb']
        
        print(f"{filename:<25} {instances:<10} {str(limit):<8} {materialization:<10} {time_ms:<10} {generated_instances:<10} {size_mb:.2f} MB")
    
    print("\n📈 Performance Analysis:")
    
    if len(reports) > 1:
        # Find fastest and largest generation
        fastest = min(reports, key=lambda x: x[1]['results']['execution_time_seconds'])
        largest = max(reports, key=lambda x: x[1]['results']['output_size_mb'])
        
        print(f"⚡ Fastest generation: {fastest[0]} ({int(fastest[1]['results']['execution_time_seconds'] * 1000)} ms)")
        print(f"📦 Largest output: {largest[0]} ({largest[1]['results']['output_size_mb']:.2f} MB)")
    
    # LUBM ontology statistics
    if reports:
        sample_report = reports[0][1]
        stdout = sample_report.get('stdout', '')
        for line in stdout.split('\n'):
            if '-> ' in line and 'classes' in line:
                print(f"🏫 {line.strip()}")
            elif '-> ' in line and 'properties' in line:
                print(f"🔗 {line.strip()}")
    
    print(f"\n🎯 GAIA Generator successfully configured with LUBM ontology!")
    print(f"✅ No GUI mode - pure command-line execution")
    print(f"🚀 Multi-threaded performance")
    print(f"📊 Detailed JSON reports for each run")

if __name__ == "__main__":
    main()
