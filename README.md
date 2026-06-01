# Ontology-Grounded RAG

Ontology-Grounded Retrieval-Augmented Generation (_OG-RAG_) is an AI framework that grounds language model answers in an explicit semantic model. Instead of searching through unstructured documents, it uses a formal ontology (classes, attributes, and relationships) to retrieve exact facts and constraints, dramatically improving factual accuracy in complex workflows.


## Repo Contents
* [Primer on ontologies](doc/ontologies/README.md)
*  [Phase 01: Neo4j for Mandala](01-mandala/README.md)
  * uses  Mandala as content
  * develops a neo4j database on crawled/parsed data
  * derives a ontology
  * builds knowledge graph

