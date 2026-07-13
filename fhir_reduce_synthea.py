#!/usr/bin/env python3
"""
Reduce a large Synthea FHIR-RDF (Turtle) dump to a smaller, representative
subset so it can be compared comfortably against the (smaller) rudof datasets.

Synthea emits one '@prefix fhir:'-led turtle document per resource. We stream
the file, and keep one document every `stride` (stride = total // target), which
samples evenly across the whole file and therefore preserves Synthea's mix of
resource types (patients, encounters, observations, ...). References to dropped
resources survive as plain IRI/string objects, which is fine for the structural
metrics computed downstream.

Usage:
    python3 fhir_reduce_synthea.py IN.ttl OUT.ttl --target 1614
"""
import argparse
from pathlib import Path


def split_docs(path):
    buf = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('@prefix fhir:'):
                if buf:
                    yield ''.join(buf)
                buf = [line]
            else:
                buf.append(line)
    if buf:
        yield ''.join(buf)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('infile')
    ap.add_argument('outfile')
    ap.add_argument('--target', type=int, default=1614, help='approx. number of documents to keep')
    args = ap.parse_args()

    total = sum(1 for _ in split_docs(args.infile))
    stride = max(1, total // args.target)
    kept = 0
    with open(args.outfile, 'w', encoding='utf-8') as out:
        for i, doc in enumerate(split_docs(args.infile)):
            if i % stride == 0:
                out.write(doc)
                kept += 1
    print(f"total docs={total:,}  stride={stride}  kept={kept:,}  -> {args.outfile}")
    print(f"size: {Path(args.outfile).stat().st_size / (1024*1024):.1f} MB")


if __name__ == '__main__':
    main()
