#!/usr/bin/env python3
"""
Synthea FHIR Dataset Generation Script

Generates a synthetic FHIR R4 dataset with Synthea and converts it to RDF
Turtle using the official org.hl7.fhir.core validator/converter library
(all inside the SYNTHEA/ Docker image).

Since Synthea also produces FHIR data, its dataset is dumped into the same
2-fhir/ folder as the RUDOFGENERATE FHIR dataset (under its own SYNTHEA_FHIR
subfolder) so the two FHIR datasets sit side by side and can be compared:

    2-fhir/
      RUDOFGENERATE_FHIR/
        run_1/ ...
      SYNTHEA_FHIR/
        run_1/
          generated_data.ttl
          generated_data.stats.json
          benchmark_report.json
          metadata.json
        INDEX.md

Usage:
    python3 generate_synthea_dataset.py                       # 1 run, 20 patients
    python3 generate_synthea_dataset.py --population 100      # larger population
    python3 generate_synthea_dataset.py --runs 3 --seed 7
"""

import subprocess
import json
import shutil
import argparse
import os
from pathlib import Path
from datetime import datetime
import sys

GENERATOR_NAME = 'SYNTHEA_FHIR'


class SyntheaDatasetGenerator:
    """Synthea -> FHIR -> Turtle dataset generator.

    Mirrors the run_N/ + metadata.json layout produced by
    generate_fhir_dataset.py / generate_all_datasets.py.
    """

    def __init__(self, name, source_dir, dataset_dir):
        self.name = name
        self.source_dir = Path(source_dir)

        generator_folder = Path(dataset_dir) / name
        generator_folder.mkdir(parents=True, exist_ok=True)

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

        self.dataset_dir = generator_folder / f'run_{next_run}'
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.run_number = next_run

        print(f"📂 Creating {name}/run_{next_run}/")

    def copy_files(self, file_patterns):
        output_dir = self.source_dir / 'output'
        copied = []
        for pattern in file_patterns:
            for file_path in output_dir.glob(pattern):
                if file_path.is_file() and file_path.name not in copied:
                    dest = self.dataset_dir / file_path.name
                    shutil.copy2(file_path, dest)
                    copied.append(file_path.name)
                    print(f"  📁 Copied: {file_path.name}")
        return copied

    def save_metadata(self, metadata):
        metadata_file = self.dataset_dir / 'metadata.json'
        metadata['generator'] = self.name
        metadata['run_number'] = self.run_number
        metadata['generated_at'] = datetime.now().isoformat()
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"✅ Metadata saved to {metadata_file}")

    def generate(self, population=20, seed=42):
        print(f"\n{'='*80}")
        print(f"🩺 GENERATING SYNTHEA FHIR DATASET (Docker)")
        print(f"{'='*80}")
        print(f"Population: {population}")
        print(f"Seed: {seed}")

        print("Building Docker image...")
        try:
            subprocess.run(['docker', 'compose', 'build'],
                           cwd=self.source_dir, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Docker build failed: {e.stderr.decode()}")
            return False

        # Clean prior output to avoid stale/merged data
        output_dir = self.source_dir / 'output'
        if output_dir.exists():
            for pattern in ['generated_data.*', '*.stats.json', 'benchmark_report.json']:
                for file_path in output_dir.glob(pattern):
                    try:
                        file_path.unlink()
                    except Exception:
                        pass
            for sub in ['synthea_raw', 'ttl_bundles']:
                shutil.rmtree(output_dir / sub, ignore_errors=True)

        env = os.environ.copy()
        env['POPULATION'] = str(population)
        env['SEED'] = str(seed)

        cmd = ['docker', 'compose', 'run', '--rm', 'synthea']
        result = subprocess.run(cmd, capture_output=True, text=True,
                                cwd=self.source_dir, env=env)

        if result.returncode == 0:
            print(result.stdout)
            files = self.copy_files(['generated_data.*', 'benchmark_report.json', '*.stats.json'])
            metadata = {
                'configuration': {
                    'population': population,
                    'seed': seed,
                    'fhir_version': 'R4',
                    'generator': 'Synthea',
                    'converter': 'org.hl7.fhir.core (org.hl7.fhir.r4.formats.RdfParser)',
                },
                'files': files,
                'description': 'Synthetic FHIR R4 patient population generated with Synthea and '
                               'converted to RDF Turtle using the official org.hl7.fhir.core '
                               'library (org.hl7.fhir.r4.formats.RdfParser).'
            }
            self.save_metadata(metadata)
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            print(f"Stdout: {result.stdout}")
            return False


def write_index(dataset_dir):
    index_file = dataset_dir / 'INDEX.md'
    with open(index_file, 'w') as f:
        f.write("# Synthea FHIR Synthetic Dataset Index\n\n")
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
        description='Generate a synthetic FHIR RDF dataset with Synthea + org.hl7.fhir.core')
    parser.add_argument('--population', type=int, default=20,
                        help='Number of patients to generate (default: 20)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducible generation (default: 42)')
    parser.add_argument('--runs', type=int, default=1,
                        help='Number of generation runs (default: 1)')
    parser.add_argument('--dataset-dir', type=str, default='2-fhir',
                        help='Directory to save datasets (default: 2-fhir, alongside the RUDOF FHIR dataset)')
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    dataset_dir = base_dir / args.dataset_dir
    source_dir = base_dir / 'SYNTHEA'
    dataset_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"🚀 SYNTHEA FHIR DATASET GENERATION")
    print(f"{'='*80}")
    print(f"Dataset directory: {dataset_dir.absolute()}")
    print(f"Source generator : {source_dir}")
    print(f"Population        : {args.population}")
    print(f"Seed             : {args.seed}")
    print(f"Runs             : {args.runs}")
    print(f"{'='*80}\n")

    success = True
    try:
        for i in range(args.runs):
            if args.runs > 1:
                print(f"\n   ▶ Run {i+1}/{args.runs}")
            gen = SyntheaDatasetGenerator(GENERATOR_NAME, source_dir, dataset_dir)
            if not gen.generate(population=args.population, seed=args.seed):
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
