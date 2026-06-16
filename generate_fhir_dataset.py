#!/usr/bin/env python3
"""
FHIR Dataset Generation Script (RUDOF Generate)

Generates a synthetic FHIR R5 RDF dataset with the RUDOFGENERATE generator
using the schema and configuration shipped in
RUDOFGENERATE/fhir_usecase/ (fhir.shex + fhir_config.toml).

The output is organized exactly like the benchmark's 1-Datasets/ folder, but
dumped into a separate 2-fhir/ folder:

    2-fhir/
      RUDOFGENERATE_FHIR/
        run_1/
          generated_data.ttl
          generated_data.stats.json
          benchmark_report.json
          metadata.json
        INDEX.md

Usage:
    python3 generate_fhir_dataset.py                 # 1 run (default)
    python3 generate_fhir_dataset.py --runs 3        # multiple runs
    python3 generate_fhir_dataset.py --dataset-dir 2-fhir
"""

import subprocess
import json
import shutil
import argparse
import os
from pathlib import Path
from datetime import datetime
import sys


# Files live inside RUDOFGENERATE/ so docker-compose can mount them via
# ./${SCHEMA_FILE} and ./${CONFIG_FILE}. Paths are relative to RUDOFGENERATE/.
SCHEMA_FILE = 'fhir_usecase/fhir.shex'
CONFIG_FILE = 'fhir_usecase/fhir_config.toml'
GENERATOR_NAME = 'RUDOFGENERATE_FHIR'


class FHIRDatasetGenerator:
    """RUDOF Generate dataset generator for the FHIR use case.

    Mirrors the run_N/ + metadata.json layout produced by
    generate_all_datasets.py's DatasetGenerator/RUDOFGenerateGenerator.
    """

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
                    run_numbers.append(int(run_folder.name.split('_')[1]))
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

    def copy_files(self, file_patterns):
        """Copy generated files to the run directory."""
        output_dir = self.source_dir / 'output'
        copied = []
        for pattern in file_patterns:
            for file_path in output_dir.glob(pattern):
                dest = self.dataset_dir / file_path.name
                shutil.copy2(file_path, dest)
                copied.append(file_path.name)
                print(f"  📁 Copied: {file_path.name}")
        return copied

    def save_metadata(self, metadata):
        """Save metadata JSON file."""
        metadata_file = self.dataset_dir / 'metadata.json'
        metadata['generator'] = self.name
        metadata['run_number'] = self.run_number
        metadata['generated_at'] = datetime.now().isoformat()

        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"✅ Metadata saved to {metadata_file}")

    def generate(self, schema=SCHEMA_FILE, config_file=CONFIG_FILE):
        print(f"\n{'='*80}")
        print(f"🟠 GENERATING FHIR DATASET — RUDOF Generate (Binary v0.2.20)")
        print(f"{'='*80}")
        print(f"Schema: {schema}")
        print(f"Config file: {config_file}")

        # Build first to ensure the image is up to date
        print("Building Docker image...")
        try:
            subprocess.run(['docker', 'compose', 'build'],
                           cwd=self.source_dir, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Docker build failed: {e.stderr.decode()}")
            return False

        # Clean prior output files to avoid "file already exists" errors
        output_dir = self.source_dir / 'output'
        if output_dir.exists():
            for pattern in ['generated_data.*', '*.stats.json', 'benchmark_report.json']:
                for file_path in output_dir.glob(pattern):
                    try:
                        file_path.unlink()
                    except Exception:
                        pass

        # docker-compose reads CONFIG_FILE / SCHEMA_FILE from the environment
        env = os.environ.copy()
        env['CONFIG_FILE'] = config_file
        env['SCHEMA_FILE'] = schema

        cmd = ['docker', 'compose', 'run', '--rm', 'rudofgenerate']
        result = subprocess.run(cmd, capture_output=True, text=True,
                                cwd=self.source_dir, env=env)

        if result.returncode == 0:
            print(result.stdout)

            files = self.copy_files(['generated_data.*', 'benchmark_report.json', '*.stats.json'])

            metadata = {
                'configuration': {
                    'schema': schema,
                    'config_file': config_file,
                    'version': 'v0.2.20-prerelease',
                },
                'files': files,
                'description': 'Synthetic FHIR R5 RDF dataset generated from fhir.shex (1,286 shapes) '
                               'with RUDOF Generate using fhir_config.toml (Maximum cardinality, '
                               'full property fill).'
            }
            self.save_metadata(metadata)
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            print(f"Stdout: {result.stdout}")
            return False


def write_index(dataset_dir):
    """Create an INDEX.md describing the generated runs (mirrors the benchmark)."""
    index_file = dataset_dir / 'INDEX.md'
    with open(index_file, 'w') as f:
        f.write("# FHIR Synthetic Dataset Index (RUDOF Generate)\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Available Datasets\n\n")

        for generator_name in sorted([d.name for d in dataset_dir.iterdir()
                                      if d.is_dir() and not d.name.startswith('.')]):
            f.write(f"### {generator_name}\n\n")
            generator_folder = dataset_dir / generator_name
            runs = sorted([d for d in generator_folder.iterdir()
                          if d.is_dir() and d.name.startswith('run_')],
                         key=lambda x: int(x.name.split('_')[1]))
            if runs:
                f.write(f"**Total runs**: {len(runs)}\n\n")
                for run_folder in runs:
                    run_num = run_folder.name.split('_')[1]
                    f.write(f"#### Run {run_num}\n")
                    f.write(f"- **Location**: `{generator_name}/{run_folder.name}/`\n")
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


def main():
    parser = argparse.ArgumentParser(
        description='Generate a synthetic FHIR RDF dataset with RUDOF Generate')
    parser.add_argument('--runs', type=int, default=1,
                        help='Number of generation runs (default: 1)')
    parser.add_argument('--dataset-dir', type=str, default='2-fhir',
                        help='Directory to save datasets (default: 2-fhir)')
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    dataset_dir = base_dir / args.dataset_dir
    source_dir = base_dir / 'RUDOFGENERATE'

    dataset_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"🚀 FHIR DATASET GENERATION")
    print(f"{'='*80}")
    print(f"Dataset directory: {dataset_dir.absolute()}")
    print(f"Source generator : {source_dir}")
    print(f"Runs             : {args.runs}")
    print(f"{'='*80}\n")

    success = True
    try:
        for i in range(args.runs):
            if args.runs > 1:
                print(f"\n   ▶ Run {i+1}/{args.runs}")
            gen = FHIRDatasetGenerator(GENERATOR_NAME, source_dir, dataset_dir)
            if not gen.generate():
                success = False
                print(f"   ❌ Run {i+1} failed")
    except KeyboardInterrupt:
        print("\n\n⚠️  Generation interrupted by user")
        sys.exit(1)

    write_index(dataset_dir)

    print(f"\n{'='*80}")
    print(f"📊 {'SUCCESS' if success else 'COMPLETED WITH ERRORS'}")
    print(f"📁 Datasets saved to: {dataset_dir.absolute()}")
    print(f"{'='*80}\n")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
