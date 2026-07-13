#!/usr/bin/env python3
"""
Three-way structural comparison of FHIR-RDF (Turtle) datasets.

Compares, side by side, an arbitrary number of FHIR-RDF datasets using three
families of metrics:

  * graph-structure metrics  -- distinct predicates / classes, mean degrees and
                                coherence (weighted structuredness), computed
                                with the SAME MetricsAccumulator the general RDF
                                benchmark uses (generate_csv_metrics.py), so the
                                FHIR case study and Section 4 speak one language;
  * FHIR-RDF conformance     -- canonical resource typing and primitive wrapping
                                (Solbrig et al. 2017), i.e. whether each dataset
                                follows the FHIR-RDF serialization idioms;
  * coverage & footprint     -- distinct FHIR R4 resource types and % of the
                                canonical R4 resource set (how much of the spec
                                the dataset exercises), value literals (real data
                                values vs empty placeholder nodes), and the
                                blank-node / total-node footprint.

Each dataset is parsed one FHIR-RDF document at a time (split on the leading
'@prefix fhir:' that both Synthea and rudof emit per resource block, with the
whole-file fallback used when there is a single document), so the full graph is
never held in memory at once.

Usage:
    python3 fhir_three_way.py LABEL=path.ttl [LABEL=path.ttl ...] [--csv out.csv]
"""

import argparse
import csv
import os
import sys
from collections import Counter
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF

# Reuse the SAME metric engine as the general benchmark (Section 4) so that
# coherence / structuredness and the other graph-structure metrics are computed
# identically here and there.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_csv_metrics import MetricsAccumulator  # noqa: E402

FHIR_NS = 'http://hl7.org/fhir/'
SHAPE_NS = 'http://hl7.org/fhir/shape/'
STRUCTURAL_LITERAL_LOCALNAMES = {'value', 'v', 'index', 'nodeRole'}

R4_RESOURCES = {
    'Account', 'ActivityDefinition', 'AdverseEvent', 'AllergyIntolerance', 'Appointment',
    'AppointmentResponse', 'AuditEvent', 'Basic', 'Binary', 'BiologicallyDerivedProduct',
    'BodyStructure', 'Bundle', 'CapabilityStatement', 'CarePlan', 'CareTeam', 'CatalogEntry',
    'ChargeItem', 'ChargeItemDefinition', 'Claim', 'ClaimResponse', 'ClinicalImpression',
    'CodeSystem', 'Communication', 'CommunicationRequest', 'CompartmentDefinition', 'Composition',
    'ConceptMap', 'Condition', 'Consent', 'Contract', 'Coverage', 'CoverageEligibilityRequest',
    'CoverageEligibilityResponse', 'DetectedIssue', 'Device', 'DeviceDefinition', 'DeviceMetric',
    'DeviceRequest', 'DeviceUseStatement', 'DiagnosticReport', 'DocumentManifest', 'DocumentReference',
    'EffectEvidenceSynthesis', 'Encounter', 'Endpoint', 'EnrollmentRequest', 'EnrollmentResponse',
    'EpisodeOfCare', 'EventDefinition', 'Evidence', 'EvidenceVariable', 'ExampleScenario',
    'ExplanationOfBenefit', 'FamilyMemberHistory', 'Flag', 'Goal', 'GraphDefinition', 'Group',
    'GuidanceResponse', 'HealthcareService', 'ImagingStudy', 'Immunization', 'ImmunizationEvaluation',
    'ImmunizationRecommendation', 'ImplementationGuide', 'InsurancePlan', 'Invoice', 'Library',
    'Linkage', 'List', 'Location', 'Measure', 'MeasureReport', 'Media', 'Medication',
    'MedicationAdministration', 'MedicationDispense', 'MedicationKnowledge', 'MedicationRequest',
    'MedicationStatement', 'MedicinalProduct', 'MedicinalProductAuthorization',
    'MedicinalProductContraindication', 'MedicinalProductIndication', 'MedicinalProductIngredient',
    'MedicinalProductInteraction', 'MedicinalProductManufactured', 'MedicinalProductPackaged',
    'MedicinalProductPharmaceutical', 'MedicinalProductUndesirableEffect', 'MessageDefinition',
    'MessageHeader', 'MolecularSequence', 'NamingSystem', 'NutritionOrder', 'Observation',
    'ObservationDefinition', 'OperationDefinition', 'OperationOutcome', 'Organization',
    'OrganizationAffiliation', 'Patient', 'PaymentNotice', 'PaymentReconciliation', 'Person',
    'PlanDefinition', 'Practitioner', 'PractitionerRole', 'Procedure', 'Provenance', 'Questionnaire',
    'QuestionnaireResponse', 'RelatedPerson', 'RequestGroup', 'ResearchDefinition',
    'ResearchElementDefinition', 'ResearchStudy', 'ResearchSubject', 'RiskAssessment',
    'RiskEvidenceSynthesis', 'Schedule', 'SearchParameter', 'ServiceRequest', 'Slot', 'Specimen',
    'SpecimenDefinition', 'StructureDefinition', 'StructureMap', 'Subscription', 'Substance',
    'SubstanceNucleicAcid', 'SubstancePolymer', 'SubstanceProtein', 'SubstanceReferenceInformation',
    'SubstanceSourceMaterial', 'SubstanceSpecification', 'SupplyDelivery', 'SupplyRequest', 'Task',
    'TerminologyCapabilities', 'TestReport', 'TestScript', 'ValueSet', 'VerificationResult',
    'VisionPrescription',
}
N_R4 = len(R4_RESOURCES)


def localname(uri):
    s = str(uri)
    for sep in ('#', '/'):
        if sep in s:
            s = s.rsplit(sep, 1)[1]
    return s


def iter_resource_docs(path):
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


def term_key(term, doc_idx):
    """Globally-unique key for a node fed to the MetricsAccumulator.

    IRIs and literals keep their lexical form (so identical IRIs/literals merge
    across documents, exactly as in generate_csv_metrics.py). Blank nodes are
    namespaced by the document index, because rdflib re-mints blank-node ids on
    every parse and we parse one FHIR-RDF document at a time -- without this,
    blank nodes from different resources would be conflated.
    """
    if isinstance(term, BNode):
        return f"_:d{doc_idx}_{term}"
    return str(term)


def analyze(label, ttl_path):
    triples = 0
    resource_types = Counter()
    resource_instances = 0
    missing_resourcetype = 0
    malformed_primitives = 0
    value_literals = 0          # all RDF literals (real data values)
    blank_nodes = 0
    total_nodes = 0

    # Same single-pass engine the general benchmark uses for coherence etc.
    acc = MetricsAccumulator()

    n_docs = 0
    for doc in iter_resource_docs(ttl_path):
        if not doc.strip():
            continue
        g = Graph()
        try:
            g.parse(data=doc, format='turtle')
        except Exception:
            continue
        n_docs += 1
        if n_docs % 5000 == 0:
            print(f"    [{label}] parsed {n_docs} documents ...")

        triples += len(g)
        nodes, blanks = set(), set()
        res_subjects = {}
        malformed_pairs = set()

        for s, p, o in g:
            acc.add_triple(term_key(s, n_docs), str(p), term_key(o, n_docs))

            for term in (s, o):
                if isinstance(term, (URIRef, BNode)):
                    nodes.add(term)
                    if isinstance(term, BNode):
                        blanks.add(term)

            if isinstance(o, Literal):
                value_literals += 1

            ps = str(p)
            pn = localname(p)

            if p == RDF.type:
                ln = localname(o)
                os_ = str(o)
                if ln in R4_RESOURCES:
                    canonical = (os_ == FHIR_NS + ln)
                    res_subjects[s] = res_subjects.get(s, False) or canonical
                    if canonical or os_.startswith(SHAPE_NS):
                        resource_types[ln] += 1
                continue

            if isinstance(o, Literal) and ps.startswith(FHIR_NS) and not ps.startswith(SHAPE_NS):
                if pn not in STRUCTURAL_LITERAL_LOCALNAMES:
                    malformed_pairs.add((s, p))

        total_nodes += len(nodes)
        blank_nodes += len(blanks)
        resource_instances += len(res_subjects)
        missing_resourcetype += sum(1 for has in res_subjects.values() if not has)
        malformed_primitives += len(malformed_pairs)

    gen = acc.finalize()
    del acc

    print(f"   [{label}] {n_docs} document(s), {triples:,} triples, "
          f"{resource_instances:,} resources, {len(resource_types)} types")

    res = resource_instances or 1
    nodes = total_nodes or 1
    return {
        'distinct_predicates': gen.get('RDF_Predicates'),
        'distinct_classes': gen.get('RDF_Classes'),
        'mean_outdegree': gen.get('RDF_Mean_Outdegree'),
        'mean_indegree': gen.get('RDF_Mean_Indegree'),
        'coherence': gen.get('RDF_Coherence'),
        'type_coverage_avg': gen.get('RDF_Type_Coverage_Avg'),
        'file_bytes': Path(ttl_path).stat().st_size,
        'triples': triples,
        'resource_instances': resource_instances,
        'resource_type_count': len(resource_types),
        'resource_type_coverage_pct': 100.0 * len(resource_types) / N_R4,
        'missing_resourcetype': missing_resourcetype,
        'missing_resourcetype_pct': 100.0 * missing_resourcetype / res,
        'malformed_primitives': malformed_primitives,
        'value_literals': value_literals,
        'literals_per_resource': value_literals / res,
        'blank_nodes': blank_nodes,
        'total_nodes': total_nodes,
        'anonymity_index': blank_nodes / nodes,
        'triple_to_resource': triples / res,
    }


_GRAPH = '0. Graph structure (shared with general benchmark)'

METRICS = [
    ('distinct_predicates', 'Distinct predicates', _GRAPH, 'int'),
    ('distinct_classes', 'Distinct rdf:type classes', _GRAPH, 'int'),
    ('mean_outdegree', 'Mean out-degree', _GRAPH, 'float'),
    ('mean_indegree', 'Mean in-degree', _GRAPH, 'float'),
    ('coherence', 'Coherence (weighted structuredness)', _GRAPH, 'float'),
    ('type_coverage_avg', 'Type coverage (mean per class)', _GRAPH, 'float'),
    ('resource_instances', 'Resource instances', '1. Coverage & scale', 'int'),
    ('resource_type_count', 'Distinct FHIR resource types', '1. Coverage & scale', 'int'),
    ('resource_type_coverage_pct', 'R4 resource-type coverage (%)', '1. Coverage & scale', 'pct'),
    ('triples', 'Total triples', '1. Coverage & scale', 'int'),
    ('file_bytes', 'RDF file size (MB)', '1. Coverage & scale', 'mb'),
    ('triple_to_resource', 'Triple-to-resource ratio', '1. Coverage & scale', 'float'),
    ('value_literals', 'Value literals (data values)', '2. Data content', 'int'),
    ('literals_per_resource', 'Literals per resource', '2. Data content', 'float'),
    ('missing_resourcetype', 'Missing resourceType (count)', '3. FHIR-RDF conformance', 'int'),
    ('missing_resourcetype_pct', 'Missing resourceType (%)', '3. FHIR-RDF conformance', 'pct'),
    ('malformed_primitives', 'Malformed primitives (count)', '3. FHIR-RDF conformance', 'int'),
    ('blank_nodes', 'Blank nodes', '4. Structural footprint', 'int'),
    ('total_nodes', 'Total nodes', '4. Structural footprint', 'int'),
    ('anonymity_index', 'Anonymity index (blank/total)', '4. Structural footprint', 'float'),
]


def fmt(v, kind):
    if v is None:
        return 'n/a'
    if kind == 'mb':
        return f'{v / (1024 * 1024):,.1f}'
    if kind == 'pct':
        return f'{v:.1f}'
    if kind == 'float':
        return f'{v:.4f}' if abs(v) < 1 else f'{v:,.2f}'
    return f'{v:,}'


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('datasets', nargs='+', help='LABEL=path.ttl (2 or more)')
    ap.add_argument('--csv', default=None)
    args = ap.parse_args()

    labels, paths = [], []
    for spec in args.datasets:
        if '=' not in spec:
            print(f"!! expected LABEL=path, got {spec!r}")
            return 1
        lbl, p = spec.split('=', 1)
        if not Path(p).exists():
            print(f"!! missing TTL: {p}")
            return 1
        labels.append(lbl)
        paths.append(p)

    results = []
    for lbl, p in zip(labels, paths):
        print(f"== {lbl}: {p}")
        results.append(analyze(lbl, p))

    colw = 30
    valw = 16
    line = '=' * (colw + valw * len(labels))
    print('\n' + line)
    header = 'METRIC'.ljust(colw) + ''.join(l.rjust(valw) for l in labels)
    print(header)
    print(line)
    section = None
    for key, name, sec, kind in METRICS:
        if sec != section:
            section = sec
            print(f"\n-- {sec} --")
        row = name.ljust(colw) + ''.join(fmt(r[key], kind).rjust(valw) for r in results)
        print(row)
    print(line)

    if args.csv:
        with open(args.csv, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['metric'] + labels)
            for key, name, sec, kind in METRICS:
                w.writerow([name] + [r[key] for r in results])
        print(f"\nWrote {args.csv}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
