# Candidate Ontologies for Exp03 — Causal Chain Extraction

## Context

Exp03 needs a formal ontology to ground the extraction of implicit causal chains
from corporate documents. The boss's target structure is:

```
Product      → has-part          → Part
Part         → has-param         → Parameter
Parameter    → has-value         → Value
Parameter    → affects           → Parameter
ParamValue   → constrained-by    → Constraint
Failure      → caused-by         → ParameterSetting
```

The following three ontologies are candidates.

---

## 1. Industrial Ontologies Foundry (IOF)

**URLs:**
- GitHub: https://github.com/iofoundry/ontology
- Spec & documentation: https://spec.industrialontologies.org/

**What it is:**
A suite of OWL ontologies for manufacturing and industrial domains, developed by an
international consortium. Covers the full product lifecycle: parts, processes, resources,
and maintenance.

**Relevant classes:**
- `iof:Product`, `iof:Part`, `iof:PhysicalComponent`
- `iof:Process`, `iof:ProcessParameter`
- `iof:MaintenanceProcess`, `iof:Failure`, `iof:FailureMode`
- `iof:Requirement`, `iof:Constraint`

**Relevant properties:**
- `iof:hasPart` — Product → Part
- `iof:hasParameter` — Part → Parameter
- `iof:causedBy` — Failure → cause

**Pros:**
- Directly targets manufacturing and failure analysis
- Actively maintained, used in industry (Siemens, Boeing, etc.)
- Modular — you can import only the core or maintenance sub-ontology

**Cons:**
- Large and complex; steep learning curve
- Some modules still under development

**Format:** OWL/Turtle

---

## 2. SSN/SOSA (W3C Standard)

**URLs:**
- W3C spec: https://www.w3.org/TR/vocab-ssn/
- SSN namespace: http://www.w3.org/ns/ssn/
- SOSA namespace: http://www.w3.org/ns/sosa/

**What it is:**
W3C standard ontology for Semantic Sensor Networks (SSN) and its lightweight core SOSA
(Sensor, Observation, Sample, Actuator). Originally for IoT/sensors but broadly applicable
to any system with observable properties and values.

**Relevant classes:**
- `sosa:FeatureOfInterest` → maps to Part/Product
- `sosa:ObservableProperty` → maps to Parameter
- `sosa:Observation` / `sosa:Result` → maps to measured Value
- `ssn:Property`, `ssn:Stimulus`

**Relevant properties:**
- `ssn:hasProperty` — Part → Parameter
- `sosa:hasResult` — Observation → Value
- `sosa:observes` — links observation to property

**Pros:**
- W3C standard — widely supported, stable, well-documented
- Lightweight SOSA core is easy to get started with
- Covers the `Parameter → has-value → Value` part of the boss's ontology very cleanly

**Cons:**
- Does not natively cover failure causality (`Failure → caused-by`)
- Needs extension for the constraint and failure parts
- Primarily designed for sensor data, not manufacturing documents

**Format:** OWL/Turtle, RDF/XML

---

## 3. FMEA Ontology

**URLs:**
- Protégé ontology library (search "FMEA"): https://protege.stanford.edu/
- LOD cloud / ontology search: https://lov.linkeddata.es/dataset/lov/
- Key paper: Matsokis & Kiritsis (2010) — "An ontology-based approach for FMEA"
  (search on Google Scholar — multiple GitHub implementations exist based on this paper)

**What it is:**
Failure Mode and Effects Analysis (FMEA) ontologies model the causal structure of failures
in engineering systems. Several versions exist from academic research.

**Relevant classes:**
- `fmea:Component` → Part
- `fmea:FailureMode`
- `fmea:Cause` → ParameterSetting out of constraint
- `fmea:Effect` → downstream Failure
- `fmea:Severity`, `fmea:Occurrence`, `fmea:Detection`

**Relevant properties:**
- `fmea:hasCause` — FailureMode → Cause
- `fmea:hasEffect` — FailureMode → Effect
- `fmea:causedBy` — Failure → ParameterSetting

**Pros:**
- Purpose-built for exactly this problem: causal chains from parameter settings to failures
- Directly models the boss's `Failure → caused-by → ParameterSetting` relation
- Familiar to engineers who know FMEA methodology

**Cons:**
- No single authoritative version — multiple competing academic ontologies
- Less tooling support than IOF or SSN
- Does not cover the `Product → has-part → Parameter` hierarchy well

**Format:** OWL/XML (varies by implementation)

---

## Recommendation

**Use IOF core + SOSA as the base, extended with FMEA-style causal relations.**

| Need | Source |
|---|---|
| `Product → has-part → Part` | IOF core |
| `Part → has-param → Parameter` | IOF + SOSA `ssn:hasProperty` |
| `Parameter → has-value → Value` | SOSA `sosa:hasResult` |
| `Parameter → affects → Parameter` | custom extension |
| `ParamValue → constrained-by → Constraint` | IOF `iof:Requirement` |
| `Failure → caused-by → ParameterSetting` | FMEA pattern |

**Rationale:**
- IOF gives the product/part/process backbone — no need to invent it
- SOSA covers the parameter/observation/value layer cleanly (W3C standard = credible for corporate presentation)
- FMEA pattern covers the causal chain — the core goal of exp03
- Avoids adopting any single ontology wholesale, which would bring hundreds of unused classes

**Practical first step:**
Define a small custom OWL file with ~10 classes and ~8 properties, importing only the
relevant IOF and SOSA terms by URI. This keeps it simple enough to explain to corporate
while being formally grounded.
