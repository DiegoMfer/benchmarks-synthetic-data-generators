#!/usr/bin/env python3
"""
Comparison of the two FHIR-RDF datasets (rudof generate vs Synthea) at a
comparable size.

rudof is generated from the tuned schema at a larger entity budget
(RUDOFGENERATE/fhir_usecase/fhir_config_tuned_large.toml) so the two datasets are
the same order of magnitude, and the script contrasts two descriptive properties:

  * dataset scale     — total triples and resource instances;
  * resource-type mix — how instances are distributed across FHIR resource types.

Both are computed with a single memory-safe streaming pass (no in-memory RDF
graph): resource-type instances are counted from the rdf:type declarations, and
triple totals are read from each dataset's generator report.

Outputs:
  * output_charts/fhir_scale_comparison.pdf

Usage:
    python3 fhir_scale_comparison.py
"""

import json
import re
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Canonical FHIR R4 resource type names, used to tell a genuine resource instance
# apart from the backbone-element / datatype shapes that rudof also materializes.
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

BASE = Path(__file__).parent


def read_triples(run_dir):
    """Total triples from the generator's report (rudof stats / Synthea report)."""
    stats = run_dir / 'generated_data.stats.json'
    if stats.exists():
        d = json.loads(stats.read_text())
        if 'total_triples' in d:
            return d['total_triples']
    report = run_dir / 'benchmark_report.json'
    if report.exists():
        d = json.loads(report.read_text())
        for path in (('generated_data', 'triples_total'), ('triples_total',)):
            cur = d
            for k in path:
                cur = cur.get(k, {}) if isinstance(cur, dict) else {}
            if isinstance(cur, int):
                return cur
    return 0


def largest_run(generator_dir):
    """The run_* with the most triples (i.e. the largest generated dataset)."""
    runs = sorted(Path(generator_dir).glob('run_*'))
    return max(runs, key=read_triples) if runs else None


# Compare the largest available run of each generator (rudof at its large,
# Synthea-comparable scale vs Synthea).
RUDOF = largest_run(BASE / '2-fhir' / 'RUDOFGENERATE_FHIR')
SYNTHEA = largest_run(BASE / '2-fhir' / 'SYNTHEA_FHIR')

# rdf:type declarations: rudof writes full URIs ('a <.../shape/Patient>'),
# Synthea writes the prefixed form ('a fhir:Patient').
RUDOF_TYPE = re.compile(r'a <http://hl7\.org/fhir/shape/([A-Za-z]+)>')
SYNTHEA_TYPE = re.compile(r'\ba fhir:([A-Za-z]+)\b')


def count_resource_types(ttl_path, pattern):
    """Stream the file and count instances per genuine FHIR R4 resource type."""
    counts = Counter()
    with open(ttl_path, 'r', encoding='utf-8') as f:
        for line in f:
            for name in pattern.findall(line):
                if name in R4_RESOURCES:
                    counts[name] += 1
    return counts


LABELS = ['rudof (tuned, large)', 'Synthea']
COLORS = ['#dd8452', '#4c72b0']


def write_chart(stats, path):
    try:
        import seaborn as sns
        sns.set_theme(style='whitegrid')
    except Exception:
        pass

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(12, 5.2))
    fig.suptitle('FHIR datasets at comparable scale — rudof generate (tuned) vs Synthea',
                 fontsize=13, fontweight='bold')

    # Panel A: dataset scale (log y; triples and resources differ by ~100x)
    cats = ['Triples', 'Resource\ninstances']
    x = np.arange(len(cats))
    w = 0.38
    for i, lab in enumerate(LABELS):
        vals = [stats[lab]['triples'], stats[lab]['resources']]
        bars = axA.bar(x + (i - 0.5) * w, vals, w, label=lab, color=COLORS[i], zorder=3)
        for rect, v in zip(bars, vals):
            axA.annotate(f'{v:,}', (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                         ha='center', va='bottom', fontsize=8, fontweight='bold',
                         xytext=(0, 2), textcoords='offset points')
    axA.set_yscale('log')
    axA.set_xticks(x)
    axA.set_xticklabels(cats, fontsize=9)
    axA.set_ylabel('count (log scale)', fontsize=9)
    axA.set_title('Dataset scale', fontsize=11)
    axA.legend(fontsize=8)
    axA.grid(axis='y', alpha=0.35, zorder=0)
    axA.set_axisbelow(True)

    # Panel B: resource-type distribution (rank vs instance count, log y)
    for i, lab in enumerate(LABELS):
        counts = sorted(stats[lab]['type_counts'].values(), reverse=True)
        ranks = np.arange(1, len(counts) + 1)
        axB.plot(ranks, counts, marker='o', ms=3, lw=1.4, color=COLORS[i],
                 label=f"{lab}: {len(counts)} resource types")
    axB.set_yscale('log')
    axB.set_xlabel('resource type, ranked by instance count', fontsize=9)
    axB.set_ylabel('instances of that type (log scale)', fontsize=9)
    axB.set_title('Resource-type distribution', fontsize=11)
    axB.legend(fontsize=8)
    axB.grid(alpha=0.35, zorder=0)
    axB.set_axisbelow(True)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    print(f"Wrote {path}")


def main():
    stats = {}
    for lab, run, pat in [(LABELS[0], RUDOF, RUDOF_TYPE), (LABELS[1], SYNTHEA, SYNTHEA_TYPE)]:
        ttl = run / 'generated_data.ttl'
        if not ttl.exists():
            print(f"!! missing {ttl}")
            return 1
        print(f"== {lab}: streaming {ttl.name} ({ttl.stat().st_size/1e6:.0f} MB) ==")
        tc = count_resource_types(ttl, pat)
        stats[lab] = {
            'triples': read_triples(run),
            'resources': sum(tc.values()),
            'type_counts': dict(tc),
        }
        print(f"   triples={stats[lab]['triples']:,}  resources={stats[lab]['resources']:,}  "
              f"distinct types={len(tc)}  top={tc.most_common(3)}")

    write_chart(stats, BASE / 'output_charts' / 'fhir_scale_comparison.pdf')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
