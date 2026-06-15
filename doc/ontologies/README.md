
## Ontology language

| Language | Description |
|----------|-------------|
| **OWL** | `Web Ontology Language`:  de facto standard for rich ontologies; based on description logics|
| **RDFS** | Basic class/property hierarchies only, no logical constraints |
| **SKOS** | Designed for thesauri, taxonomies, and controlled vocabularies |
| **SHACL** | Defines validation rules over RDF data |
| **OBO** | Open Biomedical Ontologies — widely used in biology/medicine |
| **Common Logic** | ISO standard, more expressive than OWL but less tooling support |
| **KIF** | Older AI/logic-based format, largely academic |
| **Lemon/OntoLex** | Specialized for linking ontologies to lexical/linguistic data |


## Ontology formats

| Format | Extension(s) | Description |
|--------|-------------|-------------|
| Turtle | `.ttl` | Compact, human-readable RDF syntax |
| JSON-LD | `.jsonld` | JSON-based linked data format |
| RDF/XML | `.rdf`, `.owl` | XML serialization of RDF |
| OWL/XML | `.owl` | Web Ontology Language in XML encoding |
| N-Triples | `.nt` | Simple line-based RDF format |
| N3 | `.n3` | Notation3, superset of Turtle |

## Example: Turtle (company ontology)

```turtle
@prefix ex:   <http://example.org/company#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

# --- Classes ---

ex:Employee a owl:Class ;
    rdfs:label "Employee" .

ex:Manager a owl:Class ;
    rdfs:subClassOf ex:Employee ;
    rdfs:label "Manager" .

ex:Programmer a owl:Class ;
    rdfs:subClassOf ex:Employee ;
    rdfs:label "Programmer" .

ex:ITSupport a owl:Class ;
    rdfs:subClassOf ex:Employee ;
    rdfs:label "IT Support" .

ex:SalesPerson a owl:Class ;
    rdfs:subClassOf ex:Employee ;
    rdfs:label "Sales Person" .

ex:ProjectManager a owl:Class ;
    rdfs:subClassOf ex:Manager ;
    rdfs:label "Project Manager" .

ex:CEO a owl:Class ;
    rdfs:subClassOf ex:Manager ;
    rdfs:label "CEO" .

ex:Department a owl:Class ;
    rdfs:label "Department" .

ex:Project a owl:Class ;
    rdfs:label "Project" .

# --- Properties ---

ex:reportsTo a owl:ObjectProperty ;
    rdfs:domain ex:Employee ;
    rdfs:range  ex:Manager ;
    rdfs:label  "reports to" .

ex:manages a owl:ObjectProperty ;
    rdfs:domain ex:Manager ;
    rdfs:range  ex:Employee ;
    rdfs:label  "manages" .

ex:worksOn a owl:ObjectProperty ;
    rdfs:domain ex:Employee ;
    rdfs:range  ex:Project ;
    rdfs:label  "works on" .

ex:belongsTo a owl:ObjectProperty ;
    rdfs:domain ex:Employee ;
    rdfs:range  ex:Department ;
    rdfs:label  "belongs to" .

ex:name a owl:DatatypeProperty ;
    rdfs:range xsd:string .
```



# Ontology integration 
## Schema-free KG 
* extract raw triples
* extract entitites and relations the text naturally contains, without constrains
* How
  * spacy  
  * LLM with a generic prompt ("extract subject-relation-object triples")

## Bottom-up ontology 
* extract triples first 
* discover the schema based on the data 
* ontology emerges from the data rather than being imposed on it




