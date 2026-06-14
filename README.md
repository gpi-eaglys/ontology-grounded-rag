# Ontology-Grounded RAG

Ontology-Grounded Retrieval-Augmented Generation (_OG-RAG_) is an AI framework that uses a formal ontology (classes, attributes, and relationships) to structure how content is indexed, retrieved, and used to generate answers. Unlike unstructured document search, the explicit semantic model ensures factual accuracy and consistency across complex workflows.


## TL;DR 
* get API keys
```
OPENAI_API_KEY="sk-proj-..."
ANTHROPIC_API_KEY="sk-ant-api03-IXUnt..."
```

* start Neo4J server
```
./01-mandala/scripts/05-start-neo4j.sh
```

* ingest
  * follow setups explained in: [Mandala's README](01-mandala/README.md)
  * ingestion has to be done only once

* query 
  * [text](01-mandala/src/07-query.py)


## Repo Contents
* [Primer on Ontologies](doc/ontologies/README.md)
* [Phase 01: Neo4j + Mandala](01-mandala/README.md) : parses Shippai Mandala into knowledge graph




・製造行
　・失敗、事項　→  何が原因

　・


