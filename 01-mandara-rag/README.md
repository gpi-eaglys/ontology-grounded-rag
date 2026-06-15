# Ontology Grounded Failure Mandala


## Experiment Plan

| Phases   |  Goals          |
|-------------|----------|
| Phase 1     | graph RAG development, no ontology          |
| Phase 2     | graph RAG with ontology         |


## Data Overview

* crawl data from Mandala is placed under: [build/mandala/crawl](../build/mandala/crawl)
* [site overview](../doc/site-overview.md)


### Report Sections 
* most report have these sections
* numbering may differ 
* not every report has every section 

| Japanese | Slug | Description |
|----------|------|-------------|
| 事象 | jisho | What happened — factual description of the incident |
| 経過 | keika | Timeline/progression of events leading up to and during the incident |
| 原因 | genin | Root cause analysis |
| 対処 | taisho | Immediate response actions taken at the time |
| 対策 | taisaku | Corrective and preventive measures implemented afterward |
| 総括 | sokatsu | Overall summary and conclusions |
| 知識化 | chishikika | Lessons learned and distilled knowledge for future prevention |
| 背景 | haikei | Background context and circumstances surrounding the incident |
| 四方山話 | yomoyama | Side notes and informal observations (yomoyamabanashi) |
| 後日談 | gojitsudan | Follow-up / postscript — what happened after the case closed |


## Research Plan

### Phase 1: Graph-only RAG 

1. Data 
   * Parse HA*.pdf 
   * split into the fixed sections per case
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


## Q: 「火事の原因は大体なに？」
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


## Q: 「人的ミス以外に多くある事故の原因は何？」


### STDOUT
```
Q: 人的ミス以外に多くある事故の原因は何？

A: 提供されたコンテキストに基づいて、人的ミス以外の事故原因を以下にまとめます。

## 機器・システムの問題

- **信頼性に欠ける機器**による原発プラントシステムの運転（HA0000404/総括）
- **コンピュータソフト仕様**の不具合（HA0000293/総括）
- **バックアップシステムの故障**（HA0000404/知識化）
- **自己制御性に欠ける機械**における小さな現象の致命的レベルへの発散（HA0000644/知識化）

## 設計・構造上の問題

- **新規構造の採用**時の安全面での確認不足（HA0000603/知識化）
- **性能向上・効率向上**が安全性の低下につながる場合（HA0000603/知識化）
- **ハイテク機のコンピュータ優先設計**（ゴー・アラウンド・モードや自動着陸時）（HA0000621/総括）

## 環境・条件の変化

- **低温などの条件・環境の変化**（Oリングの弾性喪失など）（HA0000639/知識化）
- **部品摩耗による形状変化**で事故の発生限界（余裕度）が低下（HA0000608/知識化）

## 組織・情報の問題

- **大きなプロジェクトでの組織分断**による情報の途絶（HA0000639/知識化）
- **アウトソーシング**によるレベルの低下（HA0000404/知識化）
- **政治的な都合**で技術の欠陥の真相が隠される（HA0000644/知識化）

## 複合要因

- **複数の因子の複合**によって事故が発生する場合（HA0000608/知識化）
- 1つの故障に誤った判断や**他の故障が重なる**（HA0000404/知識化）

これらの事例から、事故は単一原因ではなく、機器の信頼性、設計仕様、環境変化、組織的問題など多岐にわたる要因が複合して発生することが多いと言えます。
```

### Context

```
=== SYSTEM ===

You are an expert analyst of Japanese industrial failure case reports (ハイトラブル事例).
You are given retrieved sections from multiple reports, each augmented with a knowledge
graph of entities and relations extracted from that section.

Answer the user's question using ONLY the provided context.
If the answer cannot be found in the context, say so clearly.
Cite the report ID and section name when referencing a source.


=== USER ===

Context from failure case reports:

## HA0000404 / 知識化（chishikika）  [similarity: 0.760]

（１） 事故は 1 つの故障に、誤った判断や他の故障が多く重なって生じることが多い。
1 つ 1 つの機器の信頼性を高め、バックアップのシステムが常に正常に作動する体
制を保障することが重要である。
（２） さらに人間の判断の特性に合わせ、わかりやすく、誤判断を起こしにくいシステム
を組むとともに、誤操作や誤判断に対する安全システムを組むことが大切である。
（３） アウトソーシングの危険
アウトソーシングによるレベルの低下を防止する必要がある。

### Entities
  - レベルの低下 (Phenomenon)
  - アウトソーシング (Other)
  - 安全システム (Equipment)
  - 誤操作 (Phenomenon)
  - 誤判断 (Phenomenon)
  - 人間の判断 (Phenomenon)
  - バックアップシステム (Equipment)
  - 機器 (Equipment)
  - 誤った判断 (Phenomenon)
  - 故障 (Phenomenon)
  - 事故 (Phenomenon)

### Relations
  レベルの低下 --[CAUSED_BY]--> アウトソーシング
  安全システム --[PREVENTED_BY]--> 誤操作
  安全システム --[PREVENTED_BY]--> 誤判断
  安全システム --[PREVENTED_BY]--> 誤判断
  誤操作 --[TRIGGERED]--> 事故
  誤判断 --[TRIGGERED]--> 事故
  人間の判断 --[LED_TO]--> 警報を無視する
  人間の判断 --[CAUSED_BY]--> 装置の制御ループの中間に挿入される
  バックアップシステム --[PREVENTED_BY]--> 事故
  故障 --[OCCURRED_AT]--> バックアップ・システム
  故障 --[CAUSED_BY]--> 誤った判断
  事故 --[OCCURRED_AT]--> アポロ宇宙船
  事故 --[TRIGGERED]--> 想定した条件を超えた部分
  事故 --[TRIGGERED]--> 59両の車両の回収
  事故 --[TRIGGERED]--> 原因解明のための調査
  事故 --[TRIGGERED]--> 誤判断
  事故 --[TRIGGERED]--> 誤判断
  事故 --[CAUSED_BY]--> 安全確保措置
  事故 --[CAUSED_BY]--> 二重構造の車輪への変化
  事故 --[CAUSED_BY]--> コンピュータソフト仕様
  事故 --[CAUSED_BY]--> 故障
  事故 --[CAUSED_BY]--> 誤った判断
  事故 --[LED_TO]--> 技術上の対処
  事故 --[LED_TO]--> 被害想定
  事故 --[LED_TO]--> 対策
  事故 --[LED_TO]--> 余裕度
  事故 --[LED_TO]--> 対顧客の対処
  事故 --[LED_TO]--> 人身に関する課題
  事故 --[LED_TO]--> 対社会に関する課題
  事故 --[LED_TO]--> 法律的な課題
  事故 --[LED_TO]--> 防災対策改善
  事故 --[LED_TO]--> 小野谷信号場の使用中止
  事故 --[INVOLVES]--> 兆候
  事故 --[INVOLVES]--> 復帰

---

## HA0000603 / 知識化（chishikika）  [similarity: 0.757]

（１） 小さなミスが大きな被害の起点となる。
（２） 性能向上・効率向上が安全性の低下になる場合がある。
（３） 新規構造を採用する場合、安全面での確認が不可欠である。･･･仮想演習によるチ
ェックが必要である。
（４） 規程・マニュアルによる対応は、ときには大きな間違いも犯す。
（５） 車両に乗るときは、常に万一の場合の脱出経路を確認する用心深さが必要かも知れ
ない。また、万一のときのモラル（パニックにならないという）が事故の被害の大
きさを左右する。

### Entities
  - 事故の被害 (Phenomenon)
  - パニック (Phenomenon)
  - モラル (Phenomenon)
  - 万一の場合 (Phenomenon)
  - 脱出経路 (Location)
  - 車両 (Equipment)
  - 大きな間違い (Phenomenon)
  - 規程・マニュアル (Other)
  - 仮想演習 (Phenomenon)
  - 安全面での確認 (Phenomenon)
  - 新規構造 (Equipment)
  - 安全性の低下 (Phenomenon)
  - 効率向上 (Phenomenon)
  - 性能向上 (Phenomenon)
  - 大きな被害 (Phenomenon)
  - 小さなミス (Phenomenon)

### Relations
  パニック --[LED_TO]--> 機械の運転者
  パニック --[CAUSED_BY]--> 事故の被害
  モラル --[PREVENTED_BY]--> 事故の被害
  脱出経路 --[INVOLVED_IN]--> 万一の場合
  規程・マニュアル --[LED_TO]--> 大きな間違い
  仮想演習 --[PREVENTED_BY]--> 事故
  仮想演習 --[PREVENTED_BY]--> 事故
  仮想演習 --[PREVENTED_BY]--> 安全面での確認
  新規構造 --[TRIGGERED]--> 安全面での確認
  効率向上 --[LED_TO]--> 安全性の低下
  効率向上 --[LED_TO]--> 安全性の低下
  性能向上 --[LED_TO]--> 安全性の低下
  性能向上 --[LED_TO]--> 安全性の低下
  小さなミス --[LED_TO]--> 大きな被害

---

## HA0000293 / 総括（sokatsu）  [similarity: 0.756]

本事例は、ヒューマンインターフェース向上のために作ったコンピュータソフト仕
様が事故の一因となった例である。コンピュータ社会にどっぷり浸かろうとしている
現代社会にとって、コンピュータを過信するのは禁物という大きな警鐘である。
3
失敗知識データベース‑失敗百選

### Entities
  - コンピュータ過信 (Phenomenon)
  - 現代社会 (Other)
  - コンピュータ社会 (Other)
  - 事故 (Phenomenon)
  - ヒューマンインターフェース (Equipment)
  - コンピュータソフト仕様 (Equipment)

### Relations
  コンピュータ過信 --[INVOLVES]--> 現代社会
  事故 --[OCCURRED_AT]--> アポロ宇宙船
  事故 --[TRIGGERED]--> 想定した条件を超えた部分
  事故 --[TRIGGERED]--> 59両の車両の回収
  事故 --[TRIGGERED]--> 原因解明のための調査
  事故 --[TRIGGERED]--> 誤判断
  事故 --[TRIGGERED]--> 誤判断
  事故 --[CAUSED_BY]--> 安全確保措置
  事故 --[CAUSED_BY]--> 二重構造の車輪への変化
  事故 --[CAUSED_BY]--> コンピュータソフト仕様
  事故 --[CAUSED_BY]--> 故障
  事故 --[CAUSED_BY]--> 誤った判断
  事故 --[LED_TO]--> 技術上の対処
  事故 --[LED_TO]--> 被害想定
  事故 --[LED_TO]--> 対策
  事故 --[LED_TO]--> 余裕度
  事故 --[LED_TO]--> 対顧客の対処
  事故 --[LED_TO]--> 人身に関する課題
  事故 --[LED_TO]--> 対社会に関する課題
  事故 --[LED_TO]--> 法律的な課題
  事故 --[LED_TO]--> 防災対策改善
  事故 --[LED_TO]--> 小野谷信号場の使用中止
  事故 --[INVOLVES]--> 兆候
  事故 --[INVOLVES]--> 復帰
  コンピュータソフト仕様 --[CAUSED_BY]--> ヒューマンインターフェース向上

---

## HA0000601 / 総括（sokatsu）  [similarity: 0.752]

この事故は単にロータが破裂しただけでなく、多くの死傷者を伴う重大な事故となった。
そのため、事故に対する対処は技術上のものおよび対顧客のものに限らず、人身に関する
もの、対社会に関するもの、また法律的なもの（刑事事件として業務上過失致死傷に当た
るかどうかということ）など、多くの課題を同時に扱う必要が生じた。
4
失敗知識データベース-失敗百選

### Entities
  - 刑事事件 (Other)
  - 業務上過失致死傷 (Other)
  - 法律的な課題 (Other)
  - 対社会に関する課題 (Other)
  - 人身に関する課題 (Other)
  - 対顧客の対処 (Other)
  - 技術上の対処 (Other)
  - 事故 (Phenomenon)
  - 死傷者 (Other)
  - ロータ (Equipment)

### Relations
  業務上過失致死傷 --[INVOLVES]--> 刑事事件
  法律的な課題 --[INVOLVES]--> 業務上過失致死傷
  事故 --[OCCURRED_AT]--> アポロ宇宙船
  事故 --[TRIGGERED]--> 想定した条件を超えた部分
  事故 --[TRIGGERED]--> 59両の車両の回収
  事故 --[TRIGGERED]--> 原因解明のための調査
  事故 --[TRIGGERED]--> 誤判断
  事故 --[TRIGGERED]--> 誤判断
  事故 --[CAUSED_BY]--> 安全確保措置
  事故 --[CAUSED_BY]--> 二重構造の車輪への変化
  事故 --[CAUSED_BY]--> コンピュータソフト仕様
  事故 --[CAUSED_BY]--> 故障
  事故 --[CAUSED_BY]--> 誤った判断
  事故 --[LED_TO]--> 技術上の対処
  事故 --[LED_TO]--> 被害想定
  事故 --[LED_TO]--> 対策
  事故 --[LED_TO]--> 余裕度
  事故 --[LED_TO]--> 対顧客の対処
  事故 --[LED_TO]--> 人身に関する課題
  事故 --[LED_TO]--> 対社会に関する課題
  事故 --[LED_TO]--> 法律的な課題
  事故 --[LED_TO]--> 防災対策改善
  事故 --[LED_TO]--> 小野谷信号場の使用中止
  事故 --[INVOLVES]--> 兆候
  事故 --[INVOLVES]--> 復帰
  ロータ --[INVOLVES]--> 大形タービン
  ロータ --[CAUSED_BY]--> 破裂

---

## HA0000639 / 知識化（chishikika）  [similarity: 0.752]

（１）大事故もＯリングのような機械要素のひとつの不具合から生じる。
（２） 大きなプロジェクトでは組織が分断され、そこで情報も途切れてしまう。また一度
できあがった組織は、それ自体が生き延びようとして尋常でない判断がなされ、事
故につながる場合が多い。
（３） 過去に成功していても、条件や環境の変化で事故が発生してしまう（今回は低温）。
6
失敗知識データベース‑失敗百選

### Entities
  - 低温 (Phenomenon)
  - 環境 (Other)
  - 条件 (Other)
  - 過去の成功 (Phenomenon)
  - 事故 (Phenomenon)
  - 判断 (Phenomenon)
  - 情報 (Other)
  - 組織 (Organization)
  - 大きなプロジェクト (Organization)
  - 不具合 (Phenomenon)
  - 機械要素 (Equipment)
  - Oリング (Equipment)
  - 大事故 (Phenomenon)

### Relations
  低温 --[TRIGGERED]--> 事故
  低温 --[CAUSED_BY]--> 弾性喪失
  事故 --[OCCURRED_AT]--> アポロ宇宙船
  事故 --[TRIGGERED]--> 想定した条件を超えた部分
  事故 --[TRIGGERED]--> 59両の車両の回収
  事故 --[TRIGGERED]--> 原因解明のための調査
  事故 --[TRIGGERED]--> 誤判断
  事故 --[TRIGGERED]--> 誤判断
  事故 --[CAUSED_BY]--> 安全確保措置
  事故 --[CAUSED_BY]--> 二重構造の車輪への変化
  事故 --[CAUSED_BY]--> コンピュータソフト仕様
  事故 --[CAUSED_BY]--> 故障
  事故 --[CAUSED_BY]--> 誤った判断
  事故 --[LED_TO]--> 技術上の対処
  事故 --[LED_TO]--> 被害想定
  事故 --[LED_TO]--> 対策
  事故 --[LED_TO]--> 余裕度
  事故 --[LED_TO]--> 対顧客の対処
  事故 --[LED_TO]--> 人身に関する課題
  事故 --[LED_TO]--> 対社会に関する課題
  事故 --[LED_TO]--> 法律的な課題
  事故 --[LED_TO]--> 防災対策改善
  事故 --[LED_TO]--> 小野谷信号場の使用中止
  事故 --[INVOLVES]--> 兆候
  事故 --[INVOLVES]--> 復帰
  判断 --[LED_TO]--> 事故
  情報 --[LED_TO]--> 組織分断
  組織 --[TRIGGERED]--> 判断
  Oリング --[CAUSED_BY]--> 不具合
  Oリング --[CAUSED_BY]--> 低温
  大事故 --[CAUSED_BY]--> 不具合

---

## HA0000621 / 総括（sokatsu）  [similarity: 0.751]

本来ハイテク機はミスを冒しやすい人間の弱点をカバーし、人為的ミスを根絶するために開
発されたもの、たとえ人間がミスを冒してもそのミスを帳消しにして安全を確保するのがハ
イテク機の思想である。しかし、この機種のようにゴー・アラウンド・モードや、自動着陸の際、
コンピュータの命令が常に優先されると言う設計そのものに問題はなかったのか。
着陸やり直しという時間的に切迫した重大な意図の変化を確実に、安全に実施させようとする
一連のプログラムが強固に組立てられていることは、この機種の設計上の考え方であると言える
が、航空機は最終的にパイロットの意図と決心により操縦されるものであるから、パイロットと
4
失敗知識データベース-失敗百選
機体が操縦面で正反対の動きをすることはあってはならないことである。パイロットの操縦を
優先させるべきものであった。
ハイテク機の飛行が多くなるにつれて、ハイテク機特有の事故が増加している。これらはすで
に自動化が進んできた 1970 年代から発生しはじめていた。これら事故を教訓として、世界の民
間航空において自動化と安全の問題が大きく論議されている。
自動化のもたらす航空事故の共通点として次のようなものが挙げられているが、今回の事故は
まさしくこれらの指摘どおりの点が大きな要因となっている。
① 状況認識力の低下または喪失
② システム理解の不十分
③ 技量や熟練度の低下
④ 誤信号によるエラー
⑤ 単調、退屈に陥って生ずるエラー
⑥ 危険に対する警戒心の低下
⑦ 仕事のやり甲斐の喪失
⑧ 精神的ワークロードの増加
そして、アドバンスト・テクノロジー機の採用に伴って、パイロットの役割は、かつての「正
確な手順の実施者」から「的確なシステムの管理者」へと大きく変化したともいわれている。
このような役割の変化に対応するために 1970 年代に米国航空宇宙局のエーメス研究所が中心に
なって航空安全におけるヒューマンファクタの研究が精力的に実施され、コックピット・リソー
ス・マネージメント(CRM)訓練が各航空会社によって採用されるようになった。
この訓練は操縦室内のクルーの飛行運用に関する最良の協力態勢を引き出すための人間関係改
善を目途として実施されるもので、その教育成果をシミュレータで実際の場合に適用して確認す
るライン・オリエンテッドフライト・トレーニング訓練もあわせて実施される。
このような訓練は世界の主要な航空会社で実施されており、その成果があがりつつある。
また、急速な技術の進歩と航空機の発達は、今後すべての航空機がハイテク化されることであ
ろうし、このことは航空機だけでなくすべての装置産業や家庭用機器などについても同じ傾向を
とってくるであろう。しかし、いかにハイテク化が進んできても、それは人間のために役立つ
ものでなければならないし、人間が使うものでなければならない。少なくとも人間に危害を与え、
事故を発生させ、人の生命を奪うものであってはならない。中華航空機事故はこのような面から
高度技術システムの発展と人間との関わり合いにおける安全のあり方に示唆を与えるものであ
る。

### Entities
  - 誤信号によるエラー (Phenomenon)
  - 技量や熟練度の低下 (Phenomenon)
  - システム理解の不十分 (Phenomenon)
  - 状況認識力の低下 (Phenomenon)
  - 中華航空機事故 (Phenomenon)
  - ライン・オリエンテッドフライト・トレーニング訓練 (Phenomenon)
  - コックピット・リソース・マネージメント(CRM)訓練 (Phenomenon)
  - ヒューマンファクタ (Phenomenon)
  - 米国航空宇宙局エーメス研究所 (Organization)
  - 自動化 (Phenomenon)
  - ハイテク機特有の事故 (Phenomenon)
  - 人為的ミス (Phenomenon)
  - 自動着陸 (Phenomenon)
  - ゴー・アラウンド・モード (Equipment)
  - コンピュータ (Equipment)
  - パイロット (Person)
  - ハイテク機 (Equipment)

### Relations
  自動化 --[INVOLVES]--> マン・マシン・インターフェイス
  自動化 --[LED_TO]--> ヒューマンエラーの削減
  コンピュータ --[INVOLVES]--> 安全
  パイロット --[INVOLVES]--> B25 爆撃機
  パイロット --[INVOLVES]--> エアバス A300-600R
  パイロット --[INVOLVES]--> システム管理
  パイロット --[PREVENTED_BY]--> コンピュータ
  パイロット --[INVOLVED]--> オートマチックフライトシステム

---

## HA0000608 / 知識化（chishikika）  [similarity: 0.749]

事故は様々の因子の複合で発生する場合がある。事故発生に影響を及ぼしたと考えられ
る各因子について、実現可能性を考慮しながら、総合的に事故に対する余裕度を推定する
ことが必要である。そして再発防止のためには、事故の状況や現象を正確に把握すること
が不可欠である。また、事故の発生限界（余裕度）は、部品摩耗など使用にともなう形状
変化で低下するので、摩耗限界などの管理が欠かせない。

### Entities
  - 再発防止 (Other)
  - 摩耗限界 (Other)
  - 事故の発生限界 (Phenomenon)
  - 形状変化 (Phenomenon)
  - 部品摩耗 (Phenomenon)
  - 事故の現象 (Phenomenon)
  - 事故の状況 (Phenomenon)
  - 余裕度 (Phenomenon)
  - 因子 (Other)
  - 事故 (Phenomenon)

### Relations
  再発防止 --[PREVENTED_BY]--> 事故の現象
  再発防止 --[PREVENTED_BY]--> 事故の状況
  摩耗限界 --[PREVENTED_BY]--> 事故の発生限界
  形状変化 --[LED_TO]--> 事故の発生限界
  部品摩耗 --[CAUSED_BY]--> 形状変化
  因子 --[CAUSED_BY]--> 事故
  事故 --[OCCURRED_AT]--> アポロ宇宙船
  事故 --[TRIGGERED]--> 想定した条件を超えた部分
  事故 --[TRIGGERED]--> 59両の車両の回収
  事故 --[TRIGGERED]--> 原因解明のための調査
  事故 --[TRIGGERED]--> 誤判断
  事故 --[TRIGGERED]--> 誤判断
  事故 --[CAUSED_BY]--> 安全確保措置
  事故 --[CAUSED_BY]--> 二重構造の車輪への変化
  事故 --[CAUSED_BY]--> コンピュータソフト仕様
  事故 --[CAUSED_BY]--> 故障
  事故 --[CAUSED_BY]--> 誤った判断
  事故 --[LED_TO]--> 技術上の対処
  事故 --[LED_TO]--> 被害想定
  事故 --[LED_TO]--> 対策
  事故 --[LED_TO]--> 余裕度
  事故 --[LED_TO]--> 対顧客の対処
  事故 --[LED_TO]--> 人身に関する課題
  事故 --[LED_TO]--> 対社会に関する課題
  事故 --[LED_TO]--> 法律的な課題
  事故 --[LED_TO]--> 防災対策改善
  事故 --[LED_TO]--> 小野谷信号場の使用中止
  事故 --[INVOLVES]--> 兆候
  事故 --[INVOLVES]--> 復帰

---

## HA0000404 / 総括（sokatsu）  [similarity: 0.746]

信頼性に欠ける機器で成り立った原発プラントシステムを、不十分な点検体制のまま、
無理やり運転を続けていた。故障を伝えるシステムも運転員を混乱させ、誤判断を生みや
すいものだったため、運転員は事故に際し、何がおこっているのかさっぱりわからず、誤
判断による操作がさらに事態を悪化させて、最大事故にまで発展した。

### Entities
  - 最大事故 (Phenomenon)
  - 誤判断による操作 (Phenomenon)
  - 事故 (Phenomenon)
  - 誤判断 (Phenomenon)
  - 運転員 (Person)
  - 故障を伝えるシステム (Equipment)
  - 点検体制 (Other)
  - 信頼性に欠ける機器 (Equipment)
  - 原発プラントシステム (Equipment)

### Relations
  誤判断による操作 --[LED_TO]--> 最大事故
  事故 --[OCCURRED_AT]--> アポロ宇宙船
  事故 --[TRIGGERED]--> 想定した条件を超えた部分
  事故 --[TRIGGERED]--> 59両の車両の回収
  事故 --[TRIGGERED]--> 原因解明のための調査
  事故 --[TRIGGERED]--> 誤判断
  事故 --[TRIGGERED]--> 誤判断
  事故 --[CAUSED_BY]--> 安全確保措置
  事故 --[CAUSED_BY]--> 二重構造の車輪への変化
  事故 --[CAUSED_BY]--> コンピュータソフト仕様
  事故 --[CAUSED_BY]--> 故障
  事故 --[CAUSED_BY]--> 誤った判断
  事故 --[LED_TO]--> 技術上の対処
  事故 --[LED_TO]--> 被害想定
  事故 --[LED_TO]--> 対策
  事故 --[LED_TO]--> 余裕度
  事故 --[LED_TO]--> 対顧客の対処
  事故 --[LED_TO]--> 人身に関する課題
  事故 --[LED_TO]--> 対社会に関する課題
  事故 --[LED_TO]--> 法律的な課題
  事故 --[LED_TO]--> 防災対策改善
  事故 --[LED_TO]--> 小野谷信号場の使用中止
  事故 --[INVOLVES]--> 兆候
  事故 --[INVOLVES]--> 復帰
  誤判断 --[TRIGGERED]--> 事故
  運転員 --[INVOLVES]--> 誤判断による操作
  故障を伝えるシステム --[CAUSED_BY]--> 誤判断
  故障を伝えるシステム --[CAUSED_BY]--> 誤判断
  信頼性に欠ける機器 --[INVOLVES]--> 原発プラントシステム

---

## HA0000604 / 対処（taisho）  [similarity: 0.739]

本事故は、事故の直接原因の解明も重要であるが、最初の事故（第一事故）発生後の対
処方法に多く学ぶことがある。
すなわち、乗客が勝手に乗客用の非常用ドアコックを使用し、線路に降りて線路上を歩
いたこと、あるいは上り電車の抑止手配の遅れなど、最初の事故発生後における対処方法
のまずさが、結果的に多くの死傷者を出す大惨事になってしまったことである。

### Entities
  - 抑止手配の遅れ (Phenomenon)
  - 大惨事 (Phenomenon)
  - 死傷者 (Phenomenon)
  - 第一事故 (Phenomenon)
  - 上り電車 (Equipment)
  - 線路 (Location)
  - 乗客用の非常用ドアコック (Equipment)
  - 乗客 (Person)

### Relations
  抑止手配の遅れ --[LED_TO]--> 大惨事
  大惨事 --[CAUSED_BY]--> 不十分な事故時教育
  大惨事 --[PREVENTED_BY]--> 信号扱い所の掛員の列車停止権限の欠如
  大惨事 --[LED_TO]--> 上り電車2000Hの抑止失敗
  上り電車 --[INVOLVED]--> 列車三重衝突事故
  乗客 --[INVOLVES]--> 洞爺丸
  乗客 --[LED_TO]--> 上り急行「立山3号」
  乗客 --[LED_TO]--> 線路に降りて線路上を歩いた
  乗客 --[CAUSED_BY]--> 乗客用の非常用ドアコックを使用
  乗客 --[LED_TO]--> 線路上を歩き始め

---

## HA0000644 / 知識化（chishikika）  [similarity: 0.738]

（１） 自己制御性に欠ける機械は、小さな現象が致命的なレベルまで発散する危険性をも
っている。とくに巨大なシステムにおいては重大な事故につながる。
（２） 操作上の制限がなぜ必要か、それを破るとどんなことが起こるかを設計者は運転者
に十分に説明し、運転員がそれを認識することが必要である。
（３） 政治的な都合で技術の欠陥の真相が隠されてしまうことがある。社会的影響の大き
い技術については、その内容が公開され、社会的批判のもとに、改善・発展をはか
る健全な社会システムが不可欠である。

### Entities
  - 改善・発展 (Phenomenon)
  - 社会的批判 (Phenomenon)
  - 社会的影響の大きい技術 (Substance)
  - 政治的な都合 (Other)
  - 技術の欠陥 (Phenomenon)
  - 操作上の制限 (Other)
  - 運転者 (Person)
  - 設計者 (Person)
  - 事故 (Phenomenon)
  - 巨大なシステム (Equipment)
  - 小さな現象 (Phenomenon)
  - 機械 (Equipment)

### Relations
  社会的批判 --[LED_TO]--> 改善・発展
  社会的影響の大きい技術 --[INVOLVES]--> 公開
  政治的な都合 --[LED_TO]--> 技術の欠陥が隠される
  操作上の制限 --[PREVENTED_BY]--> 事故
  設計者 --[INVOLVES]--> 運転者
  設計者 --[TRIGGERED]--> 危険性の指摘
  事故 --[OCCURRED_AT]--> アポロ宇宙船
  事故 --[TRIGGERED]--> 想定した条件を超えた部分
  事故 --[TRIGGERED]--> 59両の車両の回収
  事故 --[TRIGGERED]--> 原因解明のための調査
  事故 --[TRIGGERED]--> 誤判断
  事故 --[TRIGGERED]--> 誤判断
  事故 --[CAUSED_BY]--> 安全確保措置
  事故 --[CAUSED_BY]--> 二重構造の車輪への変化
  事故 --[CAUSED_BY]--> コンピュータソフト仕様
  事故 --[CAUSED_BY]--> 故障
  事故 --[CAUSED_BY]--> 誤った判断
  事故 --[LED_TO]--> 技術上の対処
  事故 --[LED_TO]--> 被害想定
  事故 --[LED_TO]--> 対策
  事故 --[LED_TO]--> 余裕度
  事故 --[LED_TO]--> 対顧客の対処
  事故 --[LED_TO]--> 人身に関する課題
  事故 --[LED_TO]--> 対社会に関する課題
  事故 --[LED_TO]--> 法律的な課題
  事故 --[LED_TO]--> 防災対策改善
  事故 --[LED_TO]--> 小野谷信号場の使用中止
  事故 --[INVOLVES]--> 兆候
  事故 --[INVOLVES]--> 復帰
  巨大なシステム --[LED_TO]--> 重大な事故
  小さな現象 --[LED_TO]--> 事故
  機械 --[INVOLVES]--> 小さな現象

```