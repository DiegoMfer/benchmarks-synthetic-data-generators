"""FHIR-RDF specific metrics, for the E5 case study.

The general metrics engine is domain-blind by design: it counts triples, types
and property coverage and knows nothing about what the data means. E5 asks a
question that needs domain knowledge -- does the generated graph look like the
FHIR-RDF the specification describes -- so those metrics live here, behind a
namespace sniff, and never run for any other profile.

Two things are measured that the general engine cannot express:

**Coverage.** How many of the 145 canonical R4 resource types the dataset
instantiates. A schema-driven generator fed the published schema should reach
all of them; a clinical simulator emits whatever its patient model produces.

**Conformance to the FHIR-RDF paradigm** (Solbrig et al.). Two specific
requirements:

* every resource carries an ``a fhir:<Resource>`` arc -- *missing resourceType*
  counts those that do not;
* a primitive value is wrapped in a node carrying ``fhir:value`` rather than
  attached to the element property directly -- *malformed primitives* counts
  the (subject, property) pairs that attach one directly.

Both are failure counts, so lower is better, and they are the axis on which a
domain simulator beats a schema-driven generator.

This runs as a **second pass** over the same files. The shared
:class:`~rdfbench.metrics.parsers.TripleSink` receives ``str(term)``, which
collapses IRIs, blank nodes and literals into indistinguishable strings; every
metric here turns on that distinction, so it needs the real rdflib terms.
"""

from __future__ import annotations

import gc
from pathlib import Path
from typing import Any, Iterable

FHIR_NS = "http://hl7.org/fhir/"
#: rudof types its instances against the shape namespace rather than with the
#: canonical resource arc, which is exactly what *missing resourceType* detects.
SHAPE_NS = "http://hl7.org/fhir/shape/"

#: Properties whose literal object is structural rather than a stray primitive:
#: these are the wrapper arcs FHIR-RDF prescribes, not violations of it.
STRUCTURAL_LITERALS = {"value", "v", "index", "nodeRole"}

#: How much of a file to read when deciding whether this is FHIR data at all.
SNIFF_BYTES = 65536

#: The 145 canonical R4 resource types, matching the set the published results
#: were computed against. Spelled out rather than derived from whatever a
#: dataset contains -- deriving it would make 100% coverage true by
#: construction. ``Parameters`` is deliberately absent: it is an R4 resource but
#: an infrastructure envelope rather than clinical content, and it was excluded
#: from the published denominator, so including it here would silently shift
#: every coverage percentage against the numbers already in the paper.
R4_RESOURCES = frozenset("""
Account ActivityDefinition AdverseEvent AllergyIntolerance Appointment
AppointmentResponse AuditEvent Basic Binary BiologicallyDerivedProduct
BodyStructure Bundle CapabilityStatement CarePlan CareTeam CatalogEntry
ChargeItem ChargeItemDefinition Claim ClaimResponse ClinicalImpression
CodeSystem Communication CommunicationRequest CompartmentDefinition Composition
ConceptMap Condition Consent Contract Coverage CoverageEligibilityRequest
CoverageEligibilityResponse DetectedIssue Device DeviceDefinition DeviceMetric
DeviceRequest DeviceUseStatement DiagnosticReport DocumentManifest
DocumentReference EffectEvidenceSynthesis Encounter Endpoint EnrollmentRequest
EnrollmentResponse EpisodeOfCare EventDefinition Evidence EvidenceVariable
ExampleScenario ExplanationOfBenefit FamilyMemberHistory Flag Goal
GraphDefinition Group GuidanceResponse HealthcareService ImagingStudy
Immunization ImmunizationEvaluation ImmunizationRecommendation
ImplementationGuide InsurancePlan Invoice Library Linkage List Location
Measure MeasureReport Media Medication MedicationAdministration
MedicationDispense MedicationKnowledge MedicationRequest MedicationStatement
MedicinalProduct MedicinalProductAuthorization MedicinalProductContraindication
MedicinalProductIndication MedicinalProductIngredient MedicinalProductInteraction
MedicinalProductManufactured MedicinalProductPackaged MedicinalProductPharmaceutical
MedicinalProductUndesirableEffect MessageDefinition MessageHeader MolecularSequence
NamingSystem NutritionOrder Observation ObservationDefinition OperationDefinition
OperationOutcome Organization OrganizationAffiliation Patient
PaymentNotice PaymentReconciliation Person PlanDefinition Practitioner
PractitionerRole Procedure Provenance Questionnaire QuestionnaireResponse
RelatedPerson RequestGroup ResearchDefinition ResearchElementDefinition
ResearchStudy ResearchSubject RiskAssessment RiskEvidenceSynthesis Schedule
SearchParameter ServiceRequest Slot Specimen SpecimenDefinition
StructureDefinition StructureMap Subscription Substance SubstanceNucleicAcid
SubstancePolymer SubstanceProtein SubstanceReferenceInformation
SubstanceSourceMaterial SubstanceSpecification SupplyDelivery SupplyRequest
Task TerminologyCapabilities TestReport TestScript ValueSet VerificationResult
VisionPrescription
""".split())

N_R4 = len(R4_RESOURCES)

#: CSV column name per computed field.
FHIR_FIELDS: dict[str, str] = {
    "resource_instances": "FHIR_Resource_Instances",
    "resource_type_count": "FHIR_Resource_Types",
    "resource_type_coverage_pct": "FHIR_R4_Coverage_Pct",
    "triple_to_resource": "FHIR_Triples_Per_Resource",
    "value_literals": "FHIR_Value_Literals",
    "literals_per_resource": "FHIR_Literals_Per_Resource",
    "missing_resourcetype_pct": "FHIR_Missing_ResourceType_Pct",
    "malformed_primitives": "FHIR_Malformed_Primitives",
    "blank_nodes": "FHIR_Blank_Nodes",
    "total_nodes": "FHIR_Total_Nodes",
    "anonymity_index": "FHIR_Anonymity_Index",
}


def looks_like_fhir(paths: Iterable[Path]) -> bool:
    """Cheap text sniff for the FHIR namespace in the first file's header.

    Gating on the data rather than on a profile flag keeps these columns out of
    every other experiment without adding configuration nobody would otherwise
    need. A prefix declaration or a first IRI is well inside the first block of
    any serialisation this benchmark produces.
    """
    for path in paths:
        try:
            with open(path, "rb") as fh:
                return FHIR_NS.encode() in fh.read(SNIFF_BYTES)
        except OSError:
            return False
    return False


def _localname(uri: str) -> str:
    for sep in ("#", "/"):
        if sep in uri:
            uri = uri.rsplit(sep, 1)[1]
    return uri


class _FhirCounter:
    """Accumulates the FHIR-specific counts from typed rdflib terms."""

    def __init__(self) -> None:
        from rdflib import BNode, Literal, URIRef

        self._BNode, self._Literal, self._URIRef = BNode, Literal, URIRef
        self.triples = 0
        self.value_literals = 0
        self.resource_types: set[str] = set()
        #: subject -> whether it carries the canonical `a fhir:<Resource>` arc
        self.resources: dict[Any, bool] = {}
        self.malformed: set[tuple[Any, Any]] = set()
        self.nodes: set[Any] = set()
        self.blanks: set[Any] = set()

    def add(self, s, p, o) -> None:
        from rdflib.namespace import RDF

        self.triples += 1

        for term in (s, o):
            if isinstance(term, (self._URIRef, self._BNode)):
                self.nodes.add(term)
                if isinstance(term, self._BNode):
                    self.blanks.add(term)

        if isinstance(o, self._Literal):
            self.value_literals += 1

        if p == RDF.type:
            name = _localname(str(o))
            if name in R4_RESOURCES:
                canonical = str(o) == FHIR_NS + name
                # A subject counts as conformant if *any* of its type arcs is the
                # canonical one; rudof emits a shape-namespace type instead.
                self.resources[s] = self.resources.get(s, False) or canonical
                if canonical or str(o).startswith(SHAPE_NS):
                    self.resource_types.add(name)
            return

        # A primitive attached straight to a FHIR element property, rather than
        # wrapped in a node carrying fhir:value as FHIR-RDF prescribes.
        ps = str(p)
        if isinstance(o, self._Literal) and ps.startswith(FHIR_NS) and not ps.startswith(SHAPE_NS):
            if _localname(ps) not in STRUCTURAL_LITERALS:
                self.malformed.add((s, p))

    def finalize(self) -> dict[str, Any]:
        resources = len(self.resources) or 1
        nodes = len(self.nodes) or 1
        missing = sum(1 for canonical in self.resources.values() if not canonical)
        return {
            "resource_instances": len(self.resources),
            "resource_type_count": len(self.resource_types),
            "resource_type_coverage_pct": 100.0 * len(self.resource_types) / N_R4,
            "triple_to_resource": self.triples / resources,
            "value_literals": self.value_literals,
            "literals_per_resource": self.value_literals / resources,
            "missing_resourcetype_pct": 100.0 * missing / resources,
            "malformed_primitives": len(self.malformed),
            "blank_nodes": len(self.blanks),
            "total_nodes": len(self.nodes),
            "anonymity_index": len(self.blanks) / nodes,
        }


def analyse(paths: Iterable[Path], rdf_format: str) -> dict[str, Any]:
    """Return the FHIR metrics keyed by CSV column name, or ``{}`` if not FHIR."""
    paths = list(paths)
    if not paths or not looks_like_fhir(paths):
        return {}

    try:
        from rdflib import Graph
    except ImportError:  # pragma: no cover
        return {}

    from .parsers import CallbackStore

    counter = _FhirCounter()
    for path in paths:
        store = CallbackStore()
        store.set_callback(counter.add)
        graph = Graph(store=store)
        try:
            graph.parse(str(path), format=rdf_format)
        except Exception:
            try:
                graph.parse(str(path))
            except Exception:
                continue
        finally:
            try:
                graph.close()
            except Exception:
                pass
            del graph, store
            gc.collect()

    computed = counter.finalize()
    del counter
    gc.collect()
    return {FHIR_FIELDS[k]: v for k, v in computed.items() if k in FHIR_FIELDS}


__all__ = ["analyse", "looks_like_fhir", "FHIR_FIELDS", "R4_RESOURCES", "N_R4"]
