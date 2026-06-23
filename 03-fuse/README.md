# Implicit Knowledge Graph

Goal: extract and visualize implicit causal chains hidden in corporate engineering documents.

## Running

Start Neo4j and build the graph:

```bash
docker compose up -d neo4j-exp03
uv run python3 src/01-build-graph.py
```

Open Neo4j Browser at **http://localhost:7403** (user: `neo4j`, password: `password`).

## Exploring the graph

Show everything:

```cypher
MATCH (n) RETURN n
```

You will see 24 nodes and 31 relationships across these types: `Product`, `Part`, `Parameter`, `Value`, `Constraint`, `ParameterSetting`, `Failure`, `Document`.

For the demo the most compelling view is the core failure chain:

```cypher
MATCH path = (d:Document)-[:WARNS_ABOUT|RAISES_CONCERN*0..1]->
             (p:Parameter)-[:AFFECTS*1..3]->
             (sf:Parameter)<-[:HAS_PARAM]-(part:Part)<-[:HAS_PART]-(prod:Product),
      (fail:Failure)-[:CAUSED_BY]->(ps:ParameterSetting)-[:INCLUDES]->(v:Value)
RETURN path, fail, ps, v
LIMIT 50
```

Or just the causal chain without documents:

```cypher
MATCH (prod:Product)-[:HAS_PART]->(part:Part)-[:HAS_PARAM]->(p:Parameter)
-[:AFFECTS*]->(p2:Parameter),
(fail:Failure)-[:CAUSED_BY]->(ps:ParameterSetting)-[:INCLUDES]->(v:Value)
RETURN prod, part, p, p2, fail, ps, v
```

## The story the graph tells

Design review DR-50-03 raised a concern about the tooth root fillet radius being too small.
Technical memo TM-2021-007 warned about it explicitly.
RG-65 still fractured in the field at 47% of its designed life.
QR-2022-114 traced it back to `ρf=0.38m` combined with startup peak torque exceeding the design assumption.
ECR-2026-018 now requests a torque increase (500 → 650 N·m) on RG-50, which has the same unfixed flaw.

## Sample data

Documents are under `assets/3_sample_data/`:

| # | Document type | File |
|---|--------------|------|
| 1 | 設計変更依頼書 (ECR) | ECR-2026-018_設計変更依頼書.docx |
| 2 | 図面 (Drawings) | ASSY-50, EGLギア RG-50, GR-204, GR-205 (PDF) |
| 3 | 設計諸元表 (Spec sheet) | DS-RG50-01_設計諸元表.xlsx |
| 4 | 設計審査議事録 (Design Review) | DR-50-03_設計審査議事録.docx |
| 5 | 不具合対策書 (8D report) | QR-2022-114_不具合対策書.docx |
| 6 | 技術メモ (Veteran notes) | TM-2021-007_技術メモ.docx |
| 7 | 強度計算書・耐久試験報告書 | CALC-RG50-021.xlsx, TR-2022-039.docx |
