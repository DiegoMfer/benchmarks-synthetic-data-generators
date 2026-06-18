#!/usr/bin/env python3
"""
Clinical-Quality-Measure (CQM) readiness comparison: RUDOFGENERATE vs Synthea.

Operationalizes the evaluation framework of Chen et al. (2019),
"The validity of synthetic clinical data ... (Synthea) using clinical quality
measures" (BMC Med Inform Decis Mak, doi:10.1186/s12911-019-0793-0), which
maps clinical quality measures to SNOMED-CT/LOINC codes, computes the measure
rate on the synthetic population, and compares it against publicly reported
real-world benchmarks.

Because computing CQM *rates* requires a large population (the paper used
1.19M patients) and our R4 datasets are small, we assess the layer that is
robust at any scale and that the paper itself had to establish first:
  (1) terminology binding  -- which standard code systems are used, how many
      distinct codes, how many coded entries;
  (2) measure computability -- for each of the 4 CQMs, are the required
      resources + coded data elements expressible/present?
  (3) supporting clinical counts for whatever the sample does contain.

Fast and memory-safe: a single line-streaming pass (no in-memory RDF graph),
exploiting that org.hl7.fhir RdfParser writes each leaf as
`fhir:<Element> [ fhir:value "..." ]` on one line.

Usage:  python3 compare_cqm_quality.py
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).parent
DATASETS = {
    'RUDOFGENERATE': BASE / '2-fhir' / 'RUDOFGENERATE_FHIR' / 'run_1' / 'generated_data.ttl',
    'SYNTHEA':       BASE / '2-fhir' / 'SYNTHEA_FHIR' / 'run_1' / 'generated_data.ttl',
}

# fhir:<Element.path> [ fhir:value "literal" ]   (Synthea / RdfParser leaf form)
LEAF = re.compile(r'fhir:([A-Za-z][A-Za-z.]*)\s*\[\s*fhir:value\s*"([^"]*)"')
# full-URI leaf used by rudof:  <http://hl7.org/fhir/value> "literal"
URI_VAL = re.compile(r'<http://hl7\.org/fhir/value>\s*"([^"]*)"')
TYPE_PFX = re.compile(r'\ba fhir:([A-Za-z]+)\b')
TYPE_URI = re.compile(r'a <http://hl7\.org/fhir/shape/([A-Za-z]+)>')

STD_SYSTEMS = {
    'http://snomed.info/sct': 'SNOMED CT',
    'http://loinc.org': 'LOINC',
    'http://www.nlm.nih.gov/research/umls/rxnorm': 'RxNorm',
    'http://hl7.org/fhir/sid/cvx': 'CVX (vaccines)',
    'http://unitsofmeasure.org': 'UCUM',
    'http://hl7.org/fhir/sid/icd-10': 'ICD-10',
    'http://hl7.org/fhir/sid/icd-10-cm': 'ICD-10-CM',
}

# CQM target codes (Chen et al. 2019)
CQM_CODES = {
    'hypertension (SNOMED 38341003)': '38341003',
    'COPD bronchitis (SNOMED 185086009)': '185086009',
    'COPD emphysema (SNOMED 84733001)': '84733001',
    'knee replacement (SNOMED 609588000)': '609588000',
    'hip replacement (SNOMED 52734007)': '52734007',
    'systolic BP (LOINC 8480-6)': '8480-6',
    'diastolic BP (LOINC 8462-4)': '8462-4',
}


def analyze(path):
    res_types = Counter()
    system_occ = Counter()                 # system -> #occurrences
    codes_by_system = defaultdict(set)     # system -> {codes}
    total_codings = 0
    all_codes = Counter()                  # code value -> count (for CQM code lookup)
    birthdates = []
    deceased = 0
    last_system = None
    n_lines = 0

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            n_lines += 1
            m = TYPE_PFX.search(line) or TYPE_URI.search(line)
            if m:
                res_types[m.group(1)] += 1

            mv = LEAF.search(line)
            if mv:
                pred, val = mv.group(1), mv.group(2)
                pn = pred.rsplit('.', 1)[-1]
                if pn == 'system':
                    last_system = val
                    system_occ[val] += 1
                elif pn == 'code':
                    total_codings += 1
                    all_codes[val] += 1
                    if last_system is not None:
                        codes_by_system[last_system].add(val)
                elif pn == 'birthDate':
                    birthdates.append(val)
                elif pred.endswith('deceasedDateTime') or pred.endswith('deceasedBoolean'):
                    deceased += 1

    return {
        'resource_types': res_types,
        'system_occ': system_occ,
        'codes_by_system': {k: len(v) for k, v in codes_by_system.items()},
        'total_codings': total_codings,
        'all_codes': all_codes,
        'birthdates': birthdates,
        'deceased': deceased,
    }


def summarize(a):
    std = {}
    for sys_uri, occ in a['system_occ'].most_common():
        label = STD_SYSTEMS.get(sys_uri)
        if label:
            std[label] = {'occurrences': occ, 'distinct_codes': a['codes_by_system'].get(sys_uri, 0)}
    std_total_systems = len(std)

    # CQM code presence
    cqm = {name: a['all_codes'].get(code, 0) for name, code in CQM_CODES.items()}

    # ages (reference year 2016 as in the paper window)
    ages = []
    for b in a['birthdates']:
        m = re.match(r'(\d{4})', b)
        if m:
            ages.append(2016 - int(m.group(1)))
    age_50_75 = sum(1 for x in ages if 50 <= x <= 75)
    age_18_85 = sum(1 for x in ages if 18 <= x <= 85)

    return {
        'standard_code_systems': std,
        'n_standard_systems': std_total_systems,
        'total_coded_entries': a['total_codings'],
        'distinct_codes_total': len(a['all_codes']),
        'cqm_target_code_counts': cqm,
        'patients': a['resource_types'].get('Patient', 0),
        'conditions': a['resource_types'].get('Condition', 0),
        'observations': a['resource_types'].get('Observation', 0),
        'procedures': a['resource_types'].get('Procedure', 0),
        'encounters': a['resource_types'].get('Encounter', 0),
        'deceased_patients': a['deceased'],
        'patients_age_50_75': age_50_75,
        'patients_age_18_85': age_18_85,
    }


def measure_feasibility(s):
    """For each CQM: can the dataset express the required coded data elements?
    'expressible' = the required standard code systems / resource types are used."""
    sys = s['standard_code_systems']
    has_snomed = 'SNOMED CT' in sys
    has_loinc = 'LOINC' in sys
    proc = s['procedures'] > 0
    cond = s['conditions'] > 0
    obs = s['observations'] > 0
    return {
        'Colorectal Cancer Screening': {
            'requires': 'Procedure + SNOMED screening codes; Patient age 50-75',
            'expressible': bool(has_snomed and proc),
            'qualifying_pop_in_sample': s['patients_age_50_75'],
        },
        'COPD 30-Day Mortality': {
            'requires': 'Condition (COPD SNOMED) + Encounter + Patient deceased date',
            'expressible': bool(has_snomed and cond and s['encounters'] > 0),
            'copd_codes_in_sample': s['cqm_target_code_counts']['COPD bronchitis (SNOMED 185086009)']
                                    + s['cqm_target_code_counts']['COPD emphysema (SNOMED 84733001)'],
        },
        'Hip/Knee Replacement Complications': {
            'requires': 'Procedure (arthroplasty SNOMED) + complication Conditions + dates',
            'expressible': bool(has_snomed and proc),
            'arthroplasty_codes_in_sample': s['cqm_target_code_counts']['knee replacement (SNOMED 609588000)']
                                            + s['cqm_target_code_counts']['hip replacement (SNOMED 52734007)'],
        },
        'Controlling High Blood Pressure': {
            'requires': 'Condition (hypertension SNOMED 38341003) + BP Observation (LOINC 8480-6/8462-4)',
            'expressible': bool(has_snomed and has_loinc and cond and obs),
            'bp_observations_in_sample': s['cqm_target_code_counts']['systolic BP (LOINC 8480-6)'],
            'hypertension_in_sample': s['cqm_target_code_counts']['hypertension (SNOMED 38341003)'],
        },
    }


def main():
    out = {}
    for label, path in DATASETS.items():
        print(f"== {label} ({path.stat().st_size/1e6:.1f} MB) ==")
        a = analyze(path)
        s = summarize(a)
        s['cqm_feasibility'] = measure_feasibility(s)
        out[label] = s
        print(f"   standard code systems: {s['n_standard_systems']}, "
              f"coded entries: {s['total_coded_entries']}, distinct codes: {s['distinct_codes_total']}")

    p = BASE / '2-fhir' / 'cqm_comparison.json'
    p.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {p}")


if __name__ == '__main__':
    main()
