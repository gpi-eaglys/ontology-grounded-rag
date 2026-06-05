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
3. Write graph into  Neo4j
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

## TUning 

### Chunking 

The typical next step is chunk-level embeddings: split each section into ~300-500 token overlapping chunks, embed each chunk, but store a pointer back to the parent section. Retrieval finds the right chunk, but you pass the full section text (+ graph) to Claude.

For now, given your sections are likely short-to-medium and the graph traversal adds precision on top, one-per-section is fine to validate the approach.

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










# Samples 

```
ontology-grounded-rag/01-mandala$ uv run python  src/07-query.py   火事の原因は大体なに？
warning: The `tool.uv.dev-dependencies` field (used in `pyproject.toml`) is deprecated and will be removed in a future release; use `dependency-groups.dev` instead
21:39:17 [INFO] Embedding question...
21:39:17 [INFO] HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
21:39:17 [INFO] Retrieving top-5 sections...
21:39:18 [WARNING] Received notification from DBMS server: <GqlStatusObject gql_status='01N01', status_description='warn: feature deprecated with replacement. db.index.vector.queryNodes is deprecated. It is replaced by SEARCH.', position=<SummaryInputPosition line=1, column=1, offset=0>, raw_classification='DEPRECATION', classification=<NotificationClassification.DEPRECATION: 'DEPRECATION'>, raw_severity='WARNING', severity=<NotificationSeverity.WARNING: 'WARNING'>, diagnostic_record={'_classification': 'DEPRECATION', '_severity': 'WARNING', '_position': {'offset': 0, 'line': 1, 'column': 1}, 'OPERATION': '', 'OPERATION_CODE': '0', 'CURRENT_SCHEMA': '/'}> for query: "CALL db.index.vector.queryNodes('section_embedding', $top_k, $vector) YIELD node AS s, score RETURN s.report_id AS report_id, s.slug AS slug, s.label AS label, score"
21:39:18 [INFO]   HA0000611/yomoyama  score=0.759  entities=10  triples=37
21:39:18 [INFO]   HA0000619/genin  score=0.755  entities=9  triples=37
21:39:18 [INFO]   HA0000605/genin  score=0.749  entities=20  triples=39
21:39:18 [INFO]   HA0000634/taisho  score=0.748  entities=9  triples=25
21:39:18 [INFO]   HA0000611/chishikika  score=0.748  entities=12  triples=19
21:39:18 [INFO] Asking Claude...
21:39:30 [INFO] HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"

Q: 火事の原因は大体なに？

A: 提供されたレポートの文脈から、火災（火事）の原因として以下のものが挙げられています：

## 直接的な原因

- **タバコの不始末**（HA0000605 / 原因）
- **石炭レンジの残り火**（HA0000605 / 原因）
- **車両に燃えやすい材料を使用したこと**（火の回りが早くなる）（HA0000605 / 原因）
- **ガス爆発**（料理用・暖房用ガスやガスボンベの使用）（HA0000634 / 対処）

## 背景・間接的な原因

- **防災対策の不備**：北陸トンネルでは換気・排煙設備がなく、自然換気のみに頼っていた。消防関係者からの防災対策改善の勧告が再三あったにもかかわらず、国鉄（現JR）が何も実施しなかった（HA0000605 / 原因）
- **保安軽視**：経営的な合理化（設備部門の外注化、設備の老朽化、リストラによるベテラン従業員の減少）が保安軽視につながり、大事故・火災・爆発炎上を招いた（HA0000611 / 四方山話・知識化）
- **ガス工事業者の未熟さ**：正式訓練や作業者登録がされておらず、安全性に問題があった（HA0000634 / 対処）

なお、北陸トンネルの火災については「直接の出火原因は不明」とされています（HA0000605 / 原因）。
```

```
ontology-grounded-rag/01-mandala$ uv run python  src/07-query.py   よく壊れるものは何？
warning: The `tool.uv.dev-dependencies` field (used in `pyproject.toml`) is deprecated and will be removed in a future release; use `dependency-groups.dev` instead
22:16:52 [INFO] Embedding question...
22:16:54 [INFO] HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
22:16:54 [INFO] Retrieving top-5 sections...
22:16:55 [WARNING] Received notification from DBMS server: <GqlStatusObject gql_status='01N01', status_description='warn: feature deprecated with replacement. db.index.vector.queryNodes is deprecated. It is replaced by SEARCH.', position=<SummaryInputPosition line=1, column=1, offset=0>, raw_classification='DEPRECATION', classification=<NotificationClassification.DEPRECATION: 'DEPRECATION'>, raw_severity='WARNING', severity=<NotificationSeverity.WARNING: 'WARNING'>, diagnostic_record={'_classification': 'DEPRECATION', '_severity': 'WARNING', '_position': {'offset': 0, 'line': 1, 'column': 1}, 'OPERATION': '', 'OPERATION_CODE': '0', 'CURRENT_SCHEMA': '/'}> for query: "CALL db.index.vector.queryNodes('section_embedding', $top_k, $vector) YIELD node AS s, score RETURN s.report_id AS report_id, s.slug AS slug, s.label AS label, score"
22:16:55 [INFO]   HA0000625/chishikika  score=0.773  entities=18  triples=17
22:16:55 [INFO]   HA0000601/chishikika  score=0.734  entities=14  triples=19
22:16:55 [INFO]   HA0000601/genin  score=0.730  entities=16  triples=20
22:16:55 [INFO]   HA0000601/taisaku  score=0.707  entities=13  triples=14
22:16:55 [INFO]   HA0000639/chishikika  score=0.704  entities=13  triples=31
22:16:55 [INFO] Asking Claude...
22:17:05 [INFO] HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"

Q: よく壊れるものは何？

A: 提供されたコンテキストに基づいて、壊れやすいものとして以下が挙げられています：

## 壊れやすいもの・現象

### 1. **編組（HA0000625）**
力がかかった際に、1本の編組が切れると隣の編組に負荷が集中し、**破壊の伝播**によって次々と全部が壊れてしまいます。

### 2. **タービンロータ（HA0000601）**
- 材料中の**不純物**が造塊時に中心部に凝縮
- **ミクロポロシティ**（小さな空孔）の発生
- 鍛造・熱処理による**脆化**
- 高速回転による大きな接線力が限界を超えた際に**脆性破壊**が発生し、破裂

### 3. **冷却チューブ（HA0000625）**
美浜原子力発電所での冷却チューブが損傷・破損し、水蒸気による死傷者事故が発生した典型例として挙げられています。

### 4. **Oリング（HA0000639）**
低温環境下で弾性を喪失し、スペースシャトルのような**大事故の原因**となりました。

## 共通する教訓

> 「物は使用していれば必ず**劣化**する。保守点検基準の明確化が不可欠である」（HA0000625）

使用中のあらゆる機器・部品は劣化しうるため、適切な保守点検が重要とされています。
```

