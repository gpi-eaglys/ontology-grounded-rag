# mandara-with-ontology

Ontology-grounded graph RAG over Japanese industrial failure case reports,
augmented with the Mandala failure taxonomy (失敗まんだら).

## Prerequisites

- Neo4j running locally on `bolt://localhost:7687` with `mandara02` populated
- `OPENAI_API_KEY` in `.env` (used for section embeddings and query embedding)
- `ANTHROPIC_API_KEY` in `.env` — only required when using the default Claude provider

## Pipeline scripts

Run in order:

```
01-extract-mandala.py       extract the Mandala taxonomy
02-insert-ontology-graph.py insert taxonomy nodes into Neo4j
03-insert-graph.py          insert sections, entities, and relations
04-copy-embeddings.py       copy section embeddings into mandara02
05-annotate-ontology.py     classify sections against the Mandala taxonomy
06-export-ontology-annotations.py  persist CLASSIFIED_AS mappings to disk
```

## Querying

### With Claude (default)

```bash
uv run python src/10-query.py "放射能漏れの原因は何ですか？"
uv run python src/10-query.py --top-k 8 "What caused the radiation leak on the Mutsu?"
```

Requires `ANTHROPIC_API_KEY`.

### With LM Studio (local, no API key needed)

**1. Start the LM Studio server and load the model**

CLI (headless):
```bash
lms server start
lms load google/gemma-4-12b
```

GUI: Local Server tab (`<->` icon) → select model → Start Server.

**2. Verify the server is up**

```bash
curl http://localhost:1234/v1/models
```

You should see the loaded model listed in the response.

**3. Run the query**

```bash
uv run python src/10-query.py --provider lmstudio "放射能漏れの原因は何ですか？"
```

The default model is `google/gemma-3-12b-it`. To use a different model pass
`--local-model` with the exact identifier shown in LM Studio:

```bash
uv run python src/10-query.py --provider lmstudio --local-model "google/gemma-4-12b" "..."
```

> **Note:** embeddings always use OpenAI `text-embedding-3-small` regardless of provider,
> so `OPENAI_API_KEY` is always required.
