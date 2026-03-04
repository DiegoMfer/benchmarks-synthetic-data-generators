#!/usr/bin/env python3
"""
Generate CSV metrics from RDF benchmark datasets.

Optimised for low memory usage
-------------------------------
* N-Triples files are parsed line-by-line -- no rdflib graph is ever built.
* Turtle / RDF-XML files are parsed through a **CallbackStore** that never
  stores any triple; the parser emits them and they flow straight into the
  metrics accumulator.
* All counting structures use compact integer IDs instead of full URI strings.
* Multi-file generators (e.g. LUBM with 1 000+ .owl files) are processed one
  file at a time with ``gc.collect()`` between files.
* pandas / numpy are replaced by stdlib ``csv`` and plain arithmetic.
"""

import csv
import gc
import glob
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATASETS_DIR = "1-Datasets"
OUTPUT_CSV = "metrics_comparison.csv"

RDF_TYPE_BRACKETED = "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"
RDF_TYPE_PLAIN = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

# ---------------------------------------------------------------------------
# CallbackStore -- an rdflib Store that stores *nothing*
# ---------------------------------------------------------------------------
_rdflib_available = False
try:
    from rdflib import Graph, RDF
    from rdflib.store import Store

    _rdflib_available = True

    class CallbackStore(Store):
        """rdflib Store that never keeps triples in memory.

        Every triple the parser emits is forwarded to a user-supplied callback
        and then discarded, so peak memory equals only the parser's own buffers
        plus our accumulator.
        """

        context_aware = False
        formula_aware = False
        transaction_aware = False
        graph_aware = False

        def __init__(self, configuration=None, identifier=None):
            super().__init__(configuration, identifier)
            self._callback = None
            self._count = 0
            self._ns = {}

        # -- lifecycle ---------------------------------------------------
        def open(self, configuration, create=False):
            return 1  # VALID_STORE

        def close(self, commit_pending_transaction=False):
            pass

        def destroy(self, configuration):
            pass

        # -- callback ----------------------------------------------------
        def set_callback(self, callback):
            self._callback = callback

        # -- triple API (only add is ever called during parsing) ---------
        def add(self, triple, context, quoted=False):
            self._count += 1
            if self._callback:
                self._callback(*triple)

        def remove(self, triple, context):
            pass

        def triples(self, triple, context=None):
            return iter([])

        def __len__(self):
            return self._count

        # -- namespace helpers (needed by NamespaceManager) --------------
        def bind(self, prefix, namespace, override=True):
            self._ns[str(prefix)] = str(namespace)

        def namespace(self, prefix):
            return self._ns.get(str(prefix))

        def prefix(self, namespace):
            ns = str(namespace)
            for p, n in self._ns.items():
                if n == ns:
                    return p
            return None

        def namespaces(self):
            for p, n in self._ns.items():
                yield p, n

except ImportError:
    pass  # rdflib will only be needed for non-NT formats


# ---------------------------------------------------------------------------
# MetricsAccumulator -- single-pass, integer-ID-based metric computation
# ---------------------------------------------------------------------------
class MetricsAccumulator:
    """Compute all RDF metrics in a single pass using compact integer IDs.

    Instead of storing full URI strings in every set / dict, each unique
    string is mapped to an ``int`` the first time it is seen.  Python ``set``
    and ``dict`` operations on ints are both faster and *far* smaller in
    memory than on arbitrary-length strings.
    """

    __slots__ = (
        "num_triples",
        "_str_to_id",
        "_next_id",
        "_rdf_type_id",
        "subject_ids",
        "predicate_ids",
        "object_ids",
        "class_ids",
        "out_degrees",
        "in_degrees",
        "type_instances",
        "instance_properties",
    )

    def __init__(self):
        self.num_triples = 0
        self._str_to_id = {}
        self._next_id = 0

        # Pre-register rdf:type under both its representations so that
        # N-Triples (angle-bracketed) and rdflib str() (plain) both resolve
        # to the same integer ID.
        rt_id = self._intern(RDF_TYPE_BRACKETED)
        self._str_to_id[RDF_TYPE_PLAIN] = rt_id
        self._rdf_type_id = rt_id

        self.subject_ids = set()
        self.predicate_ids = set()
        self.object_ids = set()
        self.class_ids = set()

        self.out_degrees = defaultdict(int)
        self.in_degrees = defaultdict(int)
        self.type_instances = defaultdict(set)       # class_id -> {subject_ids}
        self.instance_properties = defaultdict(set)  # subject_id -> {pred_ids}

    # ---------------------------------------------------------------- helpers
    def _intern(self, s):
        uid = self._str_to_id.get(s)
        if uid is None:
            uid = self._next_id
            self._str_to_id[s] = uid
            self._next_id += 1
        return uid

    # ----------------------------------------------------------- public API
    def add_triple(self, s_str, p_str, o_str):
        s_id = self._intern(s_str)
        p_id = self._intern(p_str)
        o_id = self._intern(o_str)

        self.num_triples += 1
        self.subject_ids.add(s_id)
        self.predicate_ids.add(p_id)
        self.object_ids.add(o_id)

        self.out_degrees[s_id] += 1
        self.in_degrees[o_id] += 1
        self.instance_properties[s_id].add(p_id)

        if p_id == self._rdf_type_id:
            self.class_ids.add(o_id)
            self.type_instances[o_id].add(s_id)

    def finalize(self):
        """Return the final metrics dict and free heavy internal structures."""
        if self.num_triples == 0:
            return {}

        num_triples = self.num_triples
        num_subjects = len(self.subject_ids)
        num_predicates = len(self.predicate_ids)
        num_objects = len(self.object_ids)
        num_classes = len(self.class_ids)

        # Free counting-only sets immediately
        del self.subject_ids, self.predicate_ids, self.object_ids, self.class_ids

        # --- Degree means -----------------------------------------------
        mean_out = (
            sum(self.out_degrees.values()) / len(self.out_degrees)
            if self.out_degrees
            else 0.0
        )
        mean_in = (
            sum(self.in_degrees.values()) / len(self.in_degrees)
            if self.in_degrees
            else 0.0
        )
        del self.out_degrees, self.in_degrees

        # --- Structuredness / Coherence ---------------------------------
        total_typed = sum(len(insts) for insts in self.type_instances.values())
        weighted_cv_sum = 0.0
        cv_values = []

        for _t_id, instances in self.type_instances.items():
            i_t_size = len(instances)
            if i_t_size == 0:
                continue

            p_t = set()
            numerator = 0
            for s_id in instances:
                props = self.instance_properties.get(s_id, set())
                p_t.update(props)
                numerator += len(props)

            denom = len(p_t) * i_t_size
            cv_t = numerator / denom if denom > 0 else 0.0
            cv_values.append(cv_t)

            if total_typed > 0:
                weighted_cv_sum += (i_t_size / total_typed) * cv_t

        # Free remaining heavy structures
        del self.type_instances, self.instance_properties, self._str_to_id
        gc.collect()

        coherence = weighted_cv_sum
        avg_coverage = sum(cv_values) / len(cv_values) if cv_values else 0.0

        return {
            "RDF_Triples": num_triples,
            "RDF_Subjects": num_subjects,
            "RDF_Predicates": num_predicates,
            "RDF_Objects": num_objects,
            "RDF_Classes": num_classes,
            "RDF_Mean_Outdegree": mean_out,
            "RDF_Mean_Indegree": mean_in,
            "RDF_Coherence": coherence,
            "RDF_Type_Coverage_Avg": avg_coverage,
        }


# ---------------------------------------------------------------------------
# Streaming parsers
# ---------------------------------------------------------------------------

def _stream_nt_file(file_path):
    """Yield ``(subject, predicate, object)`` string tuples from an N-Triples
    file **without loading the file into memory**.

    N-Triples is line-based, so we simply iterate the file line by line.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # N-Triples: <subject> <predicate> <object-or-literal> .
            # Subject and predicate never contain unescaped spaces.
            parts = line.split(None, 2)
            if len(parts) < 3:
                continue
            obj = parts[2]
            # Remove the trailing triple-terminator " ."
            dot_pos = obj.rfind(" .")
            if dot_pos >= 0:
                obj = obj[:dot_pos]
            elif obj.endswith("."):
                obj = obj[:-1].rstrip()
            yield parts[0], parts[1], obj


def _parse_with_callback_store(file_path, rdf_format, acc):
    """Parse *one* file through a ``CallbackStore`` so no triples are ever
    retained in the rdflib graph.  Peak memory is only the parser's buffers
    plus our accumulator.
    """
    if not _rdflib_available:
        print(f"    rdflib not available -- cannot parse {file_path}")
        return

    store = CallbackStore()
    store.set_callback(lambda s, p, o: acc.add_triple(str(s), str(p), str(o)))
    g = Graph(store=store)

    before = acc.num_triples
    try:
        g.parse(file_path, format=rdf_format)
    except Exception:
        # Fallback: let rdflib auto-detect the format
        try:
            g.parse(file_path)
        except Exception as exc:
            print(f"    Error parsing {file_path}: {exc}")
    after = acc.num_triples
    print(f"    Parsed {os.path.basename(file_path)} ({after - before:,} triples)")

    # Explicitly tear down
    try:
        g.close()
    except Exception:
        pass
    del g, store
    gc.collect()


# ---------------------------------------------------------------------------
# Per-generator file discovery (logic unchanged from original)
# ---------------------------------------------------------------------------

def _discover_files(run_path, generator_name):
    """Return ``(file_list, rdf_format)`` for a generator run folder."""
    fmt = "turtle"
    files = []

    if generator_name.startswith("BSBM"):
        files = glob.glob(os.path.join(run_path, "dataset.ttl"))
    elif generator_name.startswith("GAIA"):
        files = glob.glob(os.path.join(run_path, "gaia_instances.owl"))
        fmt = "xml"
    elif generator_name.startswith("LINKGEN"):
        files = [
            f
            for f in glob.glob(os.path.join(run_path, "data_*"))
            if os.path.isfile(f)
        ]
        fmt = "nt"
    elif generator_name.startswith("LUBM"):
        files = glob.glob(os.path.join(run_path, "*.owl"))
        fmt = "xml"
    elif generator_name.startswith("PYGRAFT"):
        files = glob.glob(os.path.join(run_path, "full_graph.ttl"))
        if not files:
            files = glob.glob(os.path.join(run_path, "full_graph.rdf"))
            fmt = "xml"
    elif "RDFGRAPHGEN" in generator_name:
        files = glob.glob(os.path.join(run_path, "output-graph.ttl"))
    elif "RUDOF" in generator_name:
        files = glob.glob(os.path.join(run_path, "generated_data.ttl"))
    else:
        files = glob.glob(os.path.join(run_path, "*.ttl"))

    return files, fmt


# ---------------------------------------------------------------------------
# Compute RDF metrics for one run (streaming / low-memory)
# ---------------------------------------------------------------------------

def compute_rdf_metrics(run_path, generator_name):
    """Compute RDF metrics for a single run folder."""
    files, fmt = _discover_files(run_path, generator_name)
    if not files:
        print(f"  Warning: No data files found in {run_path} for {generator_name}")
        return {}

    print(f"  Loading {len(files)} file(s) from {run_path} ...")
    acc = MetricsAccumulator()

    for fpath in sorted(files):
        if fmt == "nt":
            print(f"    Streaming NT {os.path.basename(fpath)} ...")
            for triple in _stream_nt_file(fpath):
                acc.add_triple(*triple)
            print(f"    ... {acc.num_triples:,} triples so far")
        else:
            _parse_with_callback_store(fpath, fmt, acc)

    print(f"  Graph complete: {acc.num_triples:,} triples. Computing metrics ...")
    metrics = acc.finalize()
    del acc
    gc.collect()
    return metrics


# ---------------------------------------------------------------------------
# Performance metrics from benchmark_report.json  (logic unchanged)
# ---------------------------------------------------------------------------

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
                triples = instances * 3  # Approximation

        # LINKGEN Special Case checking void.ttl
        linkgen_void = os.path.join(run_path, 'void.ttl')
        if os.path.exists(linkgen_void):
            try:
                with open(linkgen_void, 'r') as vf:
                    vcontent = vf.read()
                    vmatch = re.search(r'void:triples\s+(\d+)\s*;', vcontent)
                    if vmatch:
                        triples = int(vmatch.group(1))
            except Exception:
                pass

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


# ---------------------------------------------------------------------------
# CSV helpers (stdlib csv -- no pandas overhead)
# ---------------------------------------------------------------------------

COLUMN_ORDER = [
    "Generator",
    "Run_ID",
    "Perf_Throughput",
    "Perf_Total_Triples",
    "Perf_Execution_Time",
    "RDF_Triples",
    "RDF_Subjects",
    "RDF_Predicates",
    "RDF_Objects",
    "RDF_Classes",
    "RDF_Mean_Outdegree",
    "RDF_Mean_Indegree",
    "RDF_Coherence",
    "RDF_Type_Coverage_Avg",
]


def _save_results(all_results):
    """Write results to CSV using stdlib csv (avoids pandas memory overhead)."""
    if not all_results:
        return

    # Build ordered column list
    seen = set()
    cols = []
    for c in COLUMN_ORDER:
        if c not in seen:
            cols.append(c)
            seen.add(c)
    for row in all_results:
        for k in row:
            if k not in seen:
                cols.append(k)
                seen.add(k)

    sorted_results = sorted(
        all_results, key=lambda r: (r.get("Generator", ""), r.get("Run_ID", ""))
    )

    with open(OUTPUT_CSV, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted_results)

    print(f"  Saved progress to {OUTPUT_CSV}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not os.path.exists(DATASETS_DIR):
        print(f"Error: Datasets directory '{DATASETS_DIR}' not found.")
        return

    print(f"Overwriting mode: Will generate fresh {OUTPUT_CSV}")
    if os.path.exists(OUTPUT_CSV):
        os.remove(OUTPUT_CSV)

    all_results = []
    datasets_path = Path(DATASETS_DIR)

    # Process LINKGEN last (largest datasets, highest OOM risk)
    dirs = sorted(
        d for d in datasets_path.iterdir() if d.is_dir() and not d.name.startswith(".")
    )
    linkgen_dirs = [d for d in dirs if "LINKGEN" in d.name]
    other_dirs = [d for d in dirs if "LINKGEN" not in d.name]
    sorted_dirs = other_dirs + linkgen_dirs

    for generator_folder in sorted_dirs:
        generator_name = generator_folder.name
        print(f"\n{'=' * 60}")
        print(f"Processing Generator: {generator_name}")
        print(f"{'=' * 60}")

        for run_folder in sorted(generator_folder.iterdir()):
            if not run_folder.is_dir() or not run_folder.name.startswith("run_"):
                continue

            run_id = run_folder.name
            print(f"  Processing {run_id} ...")

            # 1. Performance metrics (lightweight -- just JSON parsing)
            perf_metrics = extract_performance_metrics(str(run_folder))

            # 2. RDF metrics (streaming / low-memory)
            rdf_metrics = compute_rdf_metrics(str(run_folder), generator_name)

            # Recalculate throughput from actual loaded triples
            if "RDF_Triples" in rdf_metrics:
                exec_time = perf_metrics.get("Perf_Execution_Time")
                if exec_time and exec_time > 0:
                    perf_metrics["Perf_Throughput"] = (
                        rdf_metrics["RDF_Triples"] / exec_time
                    )

            run_data = {
                "Generator": generator_name,
                "Run_ID": run_id,
                **perf_metrics,
                **rdf_metrics,
            }

            # Replace stale entry if re-processing
            all_results = [
                r
                for r in all_results
                if not (r["Generator"] == generator_name and r["Run_ID"] == run_id)
            ]
            all_results.append(run_data)

            # Save progressively
            _save_results(all_results)

            # Force GC between runs
            gc.collect()

    print(f"\nDone. Results written to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
