"""Streaming RDF parsers that never materialise a graph.

Two paths, both feeding :class:`~rdfbench.metrics.accumulator.MetricsAccumulator`
directly:

* **N-Triples** -- line-based, so it is read with plain file iteration. Much
  faster than rdflib and bounded by one line of memory.
* **Everything else** -- parsed by rdflib through :class:`CallbackStore`, a
  ``Store`` implementation that forwards each triple to a callback and stores
  nothing. Peak memory is the parser's own buffers plus the accumulator.

Ported from the original ``generate_csv_metrics.py``.
"""

from __future__ import annotations

import gc
import os
from pathlib import Path
from typing import Iterator, Protocol

try:  # rdflib is only needed for non-N-Triples formats
    from rdflib import Graph
    from rdflib.store import Store

    RDFLIB_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only in minimal installs
    RDFLIB_AVAILABLE = False
    Store = object  # type: ignore[assignment,misc]


class TripleSink(Protocol):
    """Anything that can absorb triples -- in practice the accumulator."""

    num_triples: int

    def add_triple(self, s: str, p: str, o: str) -> None: ...


class CallbackStore(Store):  # type: ignore[misc]
    """An rdflib ``Store`` that keeps nothing.

    rdflib's parsers push triples into a store; by making the store a pure
    forwarder we get streaming parse behaviour for Turtle and RDF/XML without
    reimplementing either format.
    """

    context_aware = False
    formula_aware = False
    transaction_aware = False
    graph_aware = False

    def __init__(self, configuration=None, identifier=None):
        super().__init__(configuration, identifier)
        self._callback = None
        self._count = 0
        self._ns: dict[str, str] = {}

    # -- lifecycle --------------------------------------------------------
    def open(self, configuration, create=False):
        return 1  # VALID_STORE

    def close(self, commit_pending_transaction=False):
        pass

    def destroy(self, configuration):
        pass

    # -- callback ---------------------------------------------------------
    def set_callback(self, callback) -> None:
        self._callback = callback

    # -- triple API (only `add` is called during parsing) -----------------
    def add(self, triple, context, quoted=False):
        self._count += 1
        if self._callback:
            self._callback(*triple)

    def remove(self, triple, context):
        pass

    def triples(self, triple, context=None):
        return iter([])

    def __len__(self, context=None):
        return self._count

    # -- namespace helpers (required by NamespaceManager) -----------------
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
        yield from self._ns.items()


def stream_ntriples(file_path: Path | str) -> Iterator[tuple[str, str, str]]:
    """Yield ``(subject, predicate, object)`` strings from an N-Triples file.

    Subjects and predicates never contain unescaped spaces, so a 3-way split is
    sufficient and avoids the cost of a real parser.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 2)
            if len(parts) < 3:
                continue
            obj = parts[2]
            # Strip the trailing triple terminator " ."
            dot_pos = obj.rfind(" .")
            if dot_pos >= 0:
                obj = obj[:dot_pos]
            elif obj.endswith("."):
                obj = obj[:-1].rstrip()
            yield parts[0], parts[1], obj


def parse_into(file_path: Path, rdf_format: str, sink: TripleSink, *, verbose: bool = True) -> int:
    """Parse one file into *sink*. Returns the number of triples added."""
    before = sink.num_triples

    if rdf_format == "nt":
        for triple in stream_ntriples(file_path):
            sink.add_triple(*triple)
    else:
        _parse_with_rdflib(file_path, rdf_format, sink)

    added = sink.num_triples - before
    if verbose:
        print(f"    parsed {os.path.basename(file_path)} ({added:,} triples)", flush=True)
    return added


def _parse_with_rdflib(file_path: Path, rdf_format: str, sink: TripleSink) -> None:
    if not RDFLIB_AVAILABLE:
        raise RuntimeError(
            f"rdflib is required to parse {rdf_format!r} files but is not installed"
        )

    store = CallbackStore()
    store.set_callback(lambda s, p, o: sink.add_triple(str(s), str(p), str(o)))
    graph = Graph(store=store)

    try:
        graph.parse(str(file_path), format=rdf_format)
    except Exception:
        # Fall back to rdflib's own format sniffing; some generators emit
        # extensions that do not match their actual serialisation.
        graph.parse(str(file_path))
    finally:
        try:
            graph.close()
        except Exception:
            pass
        del graph, store
        gc.collect()
