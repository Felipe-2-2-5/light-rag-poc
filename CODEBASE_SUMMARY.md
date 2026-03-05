# Codebase Summary — LightRAG PoC

## 1. Project Purpose

This repository is a **Proof of Concept (PoC)** for a hybrid **Knowledge Graph + Vector RAG** (Retrieval-Augmented Generation) system, originally designed for Vietnamese legal document analysis. It exists primarily for learning and comparison: two fully-functional RAG pipelines sit side by side so their internal mechanics, performance, and output quality can be studied directly.

The two systems are:

| System | Description |
|--------|-------------|
| **Traditional GraphRAG** | Hand-built pipeline using FAISS + Neo4j + LangChain |
| **LightRAG** | Official [`lightrag`](https://github.com/HKUDS/LightRAG) library with LLM-powered extraction |

---

## 2. Repository Structure

```
light-rag-poc/
├── src/                        # Traditional GraphRAG implementation
├── lightrag/                   # LightRAG library integration + helpers
├── data/                       # Sample documents (PDFs, TXT)
├── custom-gpt/                 # Custom GPT integration artifacts
├── lightrag_storage/           # LightRAG persisted index (graph + vectors)
├── outputs/                    # Traditional RAG persisted outputs
├── reference/                  # Reference research papers
│
├── compare_rag_systems.py      # Side-by-side comparison runner
├── api_server.py               # FastAPI for Traditional RAG (Custom GPT)
├── lightrag_api_server.py      # FastAPI for LightRAG (Custom GPT)
├── api_example.py              # API usage examples
├── compare_parsers.py          # Document parser benchmark
│
├── test_lightrag_api.py        # Tests: LightRAG API server
├── test_graph_rag.py           # Tests: Traditional GraphRAG
├── test_confidence_scoring.py  # Tests: Confidence scoring
├── test_custom_gpt_api.py      # Tests: Custom GPT API
├── test_parsers.py             # Tests: Document parsers
│
├── debug_embeddings.py         # Debug utility: embedding inspection
├── debug_search.py             # Debug utility: search diagnostics
├── fix_embedding_metadata.py   # Utility: repair FAISS metadata
├── fix_storage_citations.py    # Utility: repair LightRAG citations
│
├── requirements.txt            # Python dependencies
├── docker-compose.yaml         # Neo4j container (port 7687 / 7474)
├── .env.template               # Environment variable reference
├── L11.ipynb                   # Original exploratory notebook
├── analysis.ipynb              # Analysis notebook
└── *.md                        # Architecture and guide documents
```

---

## 3. Source Modules

### 3.1 `src/` — Traditional GraphRAG

| File | Responsibility |
|------|---------------|
| `config.py` | Central configuration loaded from environment variables (Neo4j URI, FAISS paths, embedding model, LLM settings) |
| `ingest.py` | Entry point for document ingestion: parse → chunk → embed → store in FAISS → extract entities/relations with regex → build Neo4j KG |
| `vector_store.py` | Thin FAISS wrapper (HNSW index); `add()` and `search()` operations with JSON metadata sidecar |
| `document_parser.py` | Hybrid multi-format parser: primary Unstructured.io (free, OCR-capable), optional Landing AI ADE API fallback for complex layouts; handles PDF/TXT/images/tables |
| `graph_rag.py` | Core RAG engine: hybrid retrieval combining FAISS vector search + Neo4j graph traversal; builds a LangChain retriever and RAG chain (`RunnableParallel`) |
| `kg_builder.py` | Neo4j Cypher helpers for creating Entity and Chunk nodes and `MENTIONED_IN` / `REL` edges |
| `confidence_scorer.py` | Multi-factor confidence scoring (similarity, graph connectivity, text quality, query-term coverage, semantic coherence, answer presence); exposes `ConfidenceScore` dataclass |
| `visualize.py` | Reads Neo4j graph and renders an interactive HTML visualization using PyVis |

**Key data flow (`ingest.py`):**

```
Input document
    → DocumentParser  (parse to plain text)
    → chunk_text()    (sliding-window word chunks)
    → SentenceTransformer  (all-MiniLM-L6-v2 embeddings)
    → FaissStore.add()     (HNSW vector index)
    → simple_ner_and_relations()  (regex NER: Điều/Luật/Org)
    → build_knowledge_graph()     (Neo4j Cypher)
    → outputs/entities.json + relations.json
```

### 3.2 `lightrag/` — LightRAG Integration

| File | Responsibility |
|------|---------------|
| `lightrag_ingest.py` | Ingests documents with the official LightRAG library; sets up Gemini LLM + embedding functions; handles async ingestion loop for LLM-powered entity/relation extraction |
| `lightrag_query.py` | Query interface supporting four modes: `naive` (vector), `local` (entity graph), `global` (community summary), `hybrid` (local + global fusion); interactive REPL; reference page-number enrichment |
| `query_rag.py` | Traditional GraphRAG query interface: FAISS similarity search + Neo4j context enrichment + LangChain LLM synthesis; interactive REPL and `--search` (no-LLM) mode |
| `lightrag_db_storage.py` | Storage layer: wraps NetworkX graph and multi-level JSON vector stores (`vdb_chunks`, `vdb_entities`, `vdb_relationships`, `kv_store_*`) |

**LightRAG storage layout:**

```
lightrag_storage/
├── graph_chunk_entity_relation.graphml   # Full knowledge graph (NetworkX/GraphML)
├── vdb_chunks.json                       # Chunk-level vector index
├── vdb_entities.json                     # Entity-level vector index
├── vdb_relationships.json                # Relation-level vector index
└── kv_store_*.json                       # Metadata & LLM response caches
```

---

## 4. API Servers

### `api_server.py` — Traditional RAG API
- **Framework**: FastAPI + Uvicorn
- **Endpoints**: `/retrieve` (hybrid FAISS + Neo4j search with confidence score)
- **Purpose**: Exposes the traditional RAG system to the Custom GPT at ChatGPT

### `lightrag_api_server.py` — LightRAG API
- **Framework**: FastAPI + Uvicorn
- **Endpoints**: `/retrieve` (LightRAG query with configurable mode), `/health`
- **Purpose**: Exposes LightRAG to the Custom GPT; supports all four query modes

Both servers follow the same JSON evidence contract defined in `custom-gpt/customer-gpt.md` and `custom-gpt/knowledge_hybrid_index.md`.

Start commands:

```bash
source ~/.lightRAG_env/bin/activate
bash start_lightrag_api.sh       # LightRAG API  (default port 8000)
bash start_custom_gpt_api.sh     # Traditional RAG API
```

---

## 5. Configuration

### `src/config.py` — Key Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `CHUNK_SIZE` | `200` (words) | Text chunk size |
| `CHUNK_OVERLAP` | `50` (words) | Sliding-window overlap |
| `LLM_PROVIDER` | `gemini` | `"gemini"` or `"openai"` |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `FAISS_INDEX_PATH` | `outputs/faiss.index` | FAISS index file |

All variables can be overridden via `.env` (see `.env.template`).

### `docker-compose.yaml` — Neo4j

```bash
docker-compose up -d    # starts Neo4j on ports 7687 (bolt) and 7474 (browser)
```

---

## 6. Dependencies (`requirements.txt`)

| Category | Key Packages |
|----------|-------------|
| **Graph DB** | `neo4j==5.11.0` |
| **Vector DB** | `faiss-cpu==1.7.4` |
| **Embeddings** | `sentence-transformers==2.2.2`, `transformers==4.35.0` |
| **RAG Framework** | `langchain>=0.3.0`, `langchain-google-genai`, `langchain-openai` |
| **LLMs** | `google-generativeai>=0.3.0`, `openai>=1.0.0` |
| **Parsing** | `unstructured[pdf]==0.11.8`, `pytesseract==0.3.10`, `pdfminer.six` |
| **API** | `fastapi>=0.104.0`, `uvicorn>=0.24.0`, `pydantic>=2.0.0` |
| **Visualization** | `pyvis==0.3.1` |
| **Utilities** | `python-dotenv==1.0.0`, `tqdm==4.66.1`, `numpy==1.25.0` |

---

## 7. Tests

| Test File | What It Covers |
|-----------|---------------|
| `test_graph_rag.py` | Traditional GraphRAG: ingestion, FAISS search, Neo4j graph building, hybrid retrieval |
| `test_confidence_scoring.py` | `ConfidenceScorer` scoring logic, threshold behavior, no-answer detection |
| `test_lightrag_api.py` | LightRAG FastAPI server: health check, `/retrieve` endpoint responses |
| `test_custom_gpt_api.py` | Traditional RAG FastAPI server: endpoint contracts for Custom GPT |
| `test_parsers.py` | `DocumentParser`: PDF, TXT, and OCR parsing paths |

Run all tests:

```bash
source ~/.lightRAG_env/bin/activate
python -m pytest test_*.py -v
```

---

## 8. Comparison Tool

`compare_rag_systems.py` runs both systems against the same query and prints a side-by-side summary:

```bash
python compare_rag_systems.py -q "What is LightRAG?"
```

Sample output:

```
Traditional RAG:   query time 11.83s  |  2018 chars
LightRAG (hybrid): query time 5.15s   |  3054 chars

🚀 LightRAG was 56.5% faster
📝 LightRAG provided 1036 more characters of context
```

---

## 9. Documentation Files

| File | Content |
|------|---------|
| `README.md` | Main overview, architecture diagrams, usage instructions, comparison guide |
| `lightrag/LIGHTRAG_INTEGRATION.md` | Detailed LightRAG architecture, query mode explanation |
| `lightrag/NEO4J_INTEGRATION.md` | Neo4j schema, Cypher query examples |
| `1_ARCHITECTURE_KG_BUILD_NO_LR.md` | Knowledge graph construction without LightRAG |
| `1_1_ARCHITECTURE_DOCUMENT_EXTRACTION.md` | Document extraction architecture |
| `1_2_PARSER_SETUP.md` | Document parser setup guide |
| `2_1_RAG_COMPARISON_GUIDE.md` | Detailed RAG comparison with example queries |
| `2_BUILD_COMPLETE_LANG_CHAIN.md` | LangChain build guide |
| `3_CUSTOM_GPT_INTEGRATION.md` | ChatGPT Custom GPT setup instructions |
| `4_CITATION_EXAMPLES.md` | Citation and reference examples |
| `5_LIGHTRAG_API_MIGRATION.md` | Migration guide to LightRAG API |
| `6_RAG_ANYTHING_MIGRATION.md` | RAGAnything migration notes |
| `INTEGRATED_PIPELINE.md` | End-to-end pipeline documentation |
| `NLP501_FinalProject_Guidelines.extraction.md` | Academic project requirements |

---

## 10. System Comparison Summary

| Dimension | Traditional GraphRAG | LightRAG |
|-----------|---------------------|----------|
| **Entity extraction** | Regex heuristics (Điều/Luật/Org patterns) | LLM-powered (Gemini) |
| **Document parsing** | Unstructured.io + ADE fallback | Unstructured.io + OCR + multimodal |
| **Graph storage** | Neo4j (bolt protocol, live DB) | NetworkX + GraphML file |
| **Vector storage** | FAISS HNSW index + JSON sidecar | Multi-level JSON vector stores |
| **Query modes** | Single (hybrid FAISS + graph) | 4 modes: naive / local / global / hybrid |
| **LLM synthesis** | LangChain chain (Gemini or OpenAI) | LightRAG built-in (Gemini or OpenAI) |
| **Speed** | Baseline | ~56% faster |
| **Context coverage** | Good | ~50% more comprehensive |
| **Best use case** | Learning RAG internals | Production / research |
