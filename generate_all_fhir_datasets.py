#!/usr/bin/env python3
"""
FHIR Dataset Generation Script (part 2 of the benchmark)

Generates the FHIR use-case datasets from both generators and saves them, side
by side, in the 2-fhir/ folder — mirroring how generate_all_benchmark_datasets.py
fills 1-Datasets/:

    RUDOFGENERATE -> 2-fhir/RUDOFGENERATE_FHIR/run_N/   (ShEx-driven, fhir_r4.shex)
    Synthea       -> 2-fhir/SYNTHEA_FHIR/run_N/         (Synthea + org.hl7.fhir.core)

Both datasets are FHIR R4 RDF (Turtle) so they can be compared directly. The
resulting 2-fhir/ folder is consumed by fhir_scale_comparison.py.

Usage:
    python3 generate_all_fhir_datasets.py                       # both generators, 1 run
    python3 generate_all_fhir_datasets.py --generators RUDOFGENERATE
    python3 generate_all_fhir_datasets.py --generators SYNTHEA --population 100
    python3 generate_all_fhir_datasets.py --population 100 --runs 3
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# --- RUDOF Generate (ShEx-driven) settings -------------------------------
# Files live inside RUDOFGENERATE/ so docker-compose can mount them via
# ./${SCHEMA_FILE} and ./${CONFIG_FILE}. Paths are relative to RUDOFGENERATE/.
# FHIR R4 schema is used to match Synthea (which only exports R4/STU3/DSTU2).
SCHEMA_FILE = 'fhir_usecase/fhir_r4.shex'
CONFIG_FILE = 'fhir_usecase/fhir_config.toml'
RUDOF_NAME = 'RUDOFGENERATE_FHIR'
SYNTHEA_NAME = 'SYNTHEA_FHIR'


class FHIRRunFolder:
    """Shared run_N/ + metadata.json bookkeeping for a FHIR generator.

    Mirrors the run-folder layout produced by generate_all_benchmark_datasets.py.
    """

    def __init__(self, name, source_dir, dataset_dir):
        self.name = name
        self.source_dir = Path(source_dir)

        generator_folder = Path(dataset_dir) / name
        generator_folder.mkdir(parents=True, exist_ok=True)

        # Find the next run number
        run_numbers = []
        for run_folder in generator_folder.glob('run_*'):
            try:
                run_numbers.append(int(run_folder.name.split('_')[1]))
            except (IndexError, ValueError):
                continue
        next_run = max(run_numbers) + 1 if run_numbers else 1

        self.dataset_dir = generator_folder / f'run_{next_run}'
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.run_number = next_run
        print(f"📂 Creating {name}/run_{next_run}/")

    def clean_output(self, extra_subdirs=()):
        """Remove prior output files so a fresh run can't merge with stale data."""
        output_dir = self.source_dir / 'output'
        if not output_dir.exists():
            return
        for pattern in ['generated_data.*', '*.stats.json', 'benchmark_report.json']:
            for file_path in output_dir.glob(pattern):
                try:
                    file_path.unlink()
                except Exception:
                    pass
        for sub in extra_subdirs:
            shutil.rmtree(output_dir / sub, ignore_errors=True)

    def copy_files(self, file_patterns):
        output_dir = self.source_dir / 'output'
        copied = []
        for pattern in file_patterns:
            for file_path in output_dir.glob(pattern):
                if file_path.is_file() and file_path.name not in copied:
                    shutil.copy2(file_path, self.dataset_dir / file_path.name)
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

    def _docker_build(self):
        print("Building Docker image...")
        try:
            subprocess.run(['docker', 'compose', 'build'],
                           cwd=self.source_dir, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Docker build failed: {e.stderr.decode()}")
            return False


class RudofFHIRGenerator(FHIRRunFolder):
    """RUDOF Generate dataset generator for the FHIR use case (ShEx-driven)."""

    def generate(self, schema=SCHEMA_FILE, config_file=CONFIG_FILE):
        print(f"\n{'='*80}")
        print(f"🟠 GENERATING FHIR DATASET — RUDOF Generate (Binary v0.2.20)")
        print(f"{'='*80}")
        print(f"Schema: {schema}")
        print(f"Config file: {config_file}")

        if not self._docker_build():
            return False
        self.clean_output()

        # docker-compose reads CONFIG_FILE / SCHEMA_FILE from the environment
        env = os.environ.copy()
        env['CONFIG_FILE'] = config_file
        env['SCHEMA_FILE'] = schema

        result = subprocess.run(['docker', 'compose', 'run', '--rm', 'rudofgenerate'],
                                capture_output=True, text=True, cwd=self.source_dir, env=env)
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            print(f"Stdout: {result.stdout}")
            return False

        print(result.stdout)
        files = self.copy_files(['generated_data.*', 'benchmark_report.json', '*.stats.json'])
        self.save_metadata({
            'configuration': {
                'schema': schema,
                'config_file': config_file,
                'fhir_version': 'R4',
                'version': 'v0.2.20-prerelease',
            },
            'files': files,
            'description': 'Synthetic FHIR R4 RDF dataset generated from fhir_r4.shex (684 shapes) '
                           'with RUDOF Generate using fhir_config.toml (Maximum cardinality, '
                           'full property fill). FHIR R4 chosen to match the Synthea dataset.',
        })
        return True


class SyntheaFHIRGenerator(FHIRRunFolder):
    """Synthea -> FHIR -> Turtle dataset generator (clinical)."""

    def generate(self, population=20, seed=42):
        print(f"\n{'='*80}")
        print(f"🩺 GENERATING SYNTHEA FHIR DATASET (Docker)")
        print(f"{'='*80}")
        print(f"Population: {population}")
        print(f"Seed: {seed}")

        if not self._docker_build():
            return False
        self.clean_output(extra_subdirs=['synthea_raw', 'ttl_bundles'])

        env = os.environ.copy()
        env['POPULATION'] = str(population)
        env['SEED'] = str(seed)

        result = subprocess.run(['docker', 'compose', 'run', '--rm', 'synthea'],
                                capture_output=True, text=True, cwd=self.source_dir, env=env)
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            print(f"Stdout: {result.stdout}")
            return False

        print(result.stdout)
        files = self.copy_files(['generated_data.*', 'benchmark_report.json', '*.stats.json'])
        self.save_metadata({
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
                           'library (org.hl7.fhir.r4.formats.RdfParser).',
        })
        return True


# Generator key -> source folder under the project root
GENERATORS = ['RUDOFGENERATE', 'SYNTHEA']


def write_index(dataset_dir):
    """Create a combined INDEX.md describing every generated FHIR run."""
    index_file = dataset_dir / 'INDEX.md'
    with open(index_file, 'w') as f:
        f.write("# FHIR Synthetic Dataset Index\n\n")
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
        description='Generate the FHIR use-case datasets from all generators',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Generate all FHIR datasets:
    python3 generate_all_fhir_datasets.py

  Generate only one generator:
    python3 generate_all_fhir_datasets.py --generators RUDOFGENERATE

  Larger Synthea population, multiple runs:
    python3 generate_all_fhir_datasets.py --population 100 --runs 3
        """,
    )
    parser.add_argument('--generators', nargs='*', default=['ALL'],
                        help="Generators to run: RUDOFGENERATE, SYNTHEA, or ALL (default: ALL)")
    parser.add_argument('--runs', type=int, default=1,
                        help='Number of generation runs per generator (default: 1)')
    parser.add_argument('--population', type=int, default=20,
                        help='Synthea patient population (default: 20)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Synthea random seed (default: 42)')
    parser.add_argument('--schema', type=str, default=SCHEMA_FILE,
                        help=f'RUDOF schema file, relative to RUDOFGENERATE/ (default: {SCHEMA_FILE})')
    parser.add_argument('--config', type=str, default=CONFIG_FILE,
                        help=f'RUDOF config file, relative to RUDOFGENERATE/ (default: {CONFIG_FILE})')
    parser.add_argument('--dataset-dir', type=str, default='2-fhir',
                        help='Directory to save datasets (default: 2-fhir)')
    args = parser.parse_args()

    requested = [g.upper() for g in args.generators]
    selected = list(GENERATORS) if 'ALL' in requested else [g for g in requested if g in GENERATORS]
    unknown = [g for g in requested if g != 'ALL' and g not in GENERATORS]
    if unknown:
        print(f"⚠️  Ignoring unknown generators: {', '.join(unknown)}")
    if not selected:
        print("❌ No valid generators selected. Choose from: " + ', '.join(GENERATORS))
        return 1

    base_dir = Path(__file__).parent
    dataset_dir = base_dir / args.dataset_dir
    dataset_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"🚀 FHIR DATASET GENERATION")
    print(f"{'='*80}")
    print(f"Dataset directory: {dataset_dir.absolute()}")
    print(f"Generators       : {', '.join(selected)}")
    print(f"Runs             : {args.runs}")
    print(f"{'='*80}\n")

    success = True
    try:
        for i in range(args.runs):
            if args.runs > 1:
                print(f"\n   ▶ Run {i+1}/{args.runs}")

            if 'RUDOFGENERATE' in selected:
                gen = RudofFHIRGenerator(RUDOF_NAME, base_dir / 'RUDOFGENERATE', dataset_dir)
                if not gen.generate(schema=args.schema, config_file=args.config):
                    success = False
                    print(f"   ❌ RUDOFGENERATE run {i+1} failed")

            if 'SYNTHEA' in selected:
                gen = SyntheaFHIRGenerator(SYNTHEA_NAME, base_dir / 'SYNTHEA', dataset_dir)
                if not gen.generate(population=args.population, seed=args.seed):
                    success = False
                    print(f"   ❌ SYNTHEA run {i+1} failed")
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
