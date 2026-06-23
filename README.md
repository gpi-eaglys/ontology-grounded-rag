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


## TODO

### Migrate Neo4j from Enterprise to Community

Currently using `neo4j:enterprise` with `NEO4J_ACCEPT_LICENSE_AGREEMENT=eval` (30-day eval limit).
Migration to two Community containers is prepared but not yet run.

**Steps:**

1. **Run the migration script** — dumps `mandara01` and `mandara02` from the running enterprise
   container and loads them into `neo4j-exp01` and `neo4j-exp02`:
   ```bash
   ./scripts/migrate-neo4j.sh
   ```

2. **Update `DATABASE` in all scripts** — Community only has one database named `neo4j`:
   - `01-mandara-rag/src/*.py`: change `DATABASE = "mandara01"` → `DATABASE = "neo4j"`
   - `02-mandara-with-ontology/src/*.py`: change `DATABASE = "mandara02"` → `DATABASE = "neo4j"`

3. **Stop the enterprise container:**
   ```bash
   docker stop neo4j
   ```

4. **Verify the new containers are healthy:**
   ```bash
   docker compose ps
   curl http://localhost:7401   # neo4j-exp01 browser
   curl http://localhost:7402   # neo4j-exp02 browser
   ```

5. **Update `start-neo4j.sh`** (or retire it) — replace with `docker compose up -d`.

## Experiment 03 — Implicit Knowledge / Causal Chain Extraction

### Goal

Extract **implicit causal chains** hidden in corporate documents (emails, Excel, Word).

A document may state *"the pump overheated"* without explicitly saying *"pump temperature
parameter exceeded its constraint, which caused the failure."* The goal is to surface that
hidden causal chain using LLMs grounded in a product/process ontology.

### Ontology (defined by management)

```
Product      → has-part          → Part
Part         → has-param         → Parameter
Parameter    → has-value         → Value
Parameter    → affects           → Parameter
ParamValue   → constrained-by    → Constraint
Failure      → caused-by         → ParameterSetting
```

### Approach

1. **Ingest** — parse `.docx` and `.xlsx` (keyword-context format) into text
2. **Extract** — use LLM to find instances of the ontology relations above
3. **Build causal chains** — link `ParameterSetting → Constraint violation → Failure`
4. **Store** in Neo4j (neo4j-exp03, bolt port 7603, browser port 7403)
5. **Present** — demonstrate to corporate how AI surfaces implicit knowledge

### Input documents

- Excel: two-column format (keyword | context)
- Word: free-text documents
- Source: Google Drive (download locally before ingestion)

## Repo Contents
* [Primer on Ontologies](doc/ontologies/README.md)
* [Phase 01: Neo4j + Mandala](01-mandala/README.md) : parses Shippai Mandala into knowledge graph




・製造行
　・失敗、事項　→  何が原因

　・


