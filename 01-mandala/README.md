# Ontology Grounded Failure Mandala


## Experiment Plan

| Phases   |  Goals          |
|-------------|----------|
| Phase 1     | graph RAG development, no ontology          |
| Phase 2     | graph RAG with ontology         |



### Phase 1: Graph-only RAG 

1. Data 
   * Parse HA*.pdf 
   * split into the six fixed sections per case
2. Entities + Relations
   * Extract entities + relations from each section 
   * use LLM (Japanese-capable, e.g. Claude) → output structured triples
3. Write into  Neo4j
   * Load into Neo4j: FailureCase nodes with section text as properties, entity nodes, typed relationships (CAUSED_BY, LED_TO, INVOLVES, PREVENTED_BY, …)
4. RAG
   * embed section text, store vectors on nodes, answer queries via Cypher + vector similarity (Neo4j has native vector index since 5.x)

5. 
question → entity extraction → Cypher query → subgraph → LLM prompt → answer



### Phase 2: Graph + Ontology

1. Taxonomy 
    * Extract the Mandala taxonomy from inf/mandara.
    * html → LLM one-shot → structured JSON (3 dimensions × 3 levels)
2. Add ontology nodes to Neo4j
   * how? 
   * CauseCategory, ActionCategory, ResultCategory
   * link each FailureCase to the relevant Mandala nodes (tag assignments live in CA*.html)
3. Update RAG
    * route queries through ontology first
    * query → relevant Mandala nodes → filter candidate cases
    * then vector search within that subgraph



# Processing steps


## Crawl contents 
* use script [01-crawl-mandala.sh](scripts/01-crawl-mandala.sh) to download contects 
  * output dir is [<REPO>/build/mandala/crawl](../build/mandala/crawl)
  * note: the `build` dir is in .gitignore 


## Preprocessing 
* langauge detection 


## Document selection for KG generation
* not all files contribute to Knowledge Graph (KG) generation 
* selection 
  * by language (e.g., English only)
  * format -> PDF only 
  * 

## De-duplication 


## Content extraction 
* text needs to be extracted from  .html, .pdf files 












