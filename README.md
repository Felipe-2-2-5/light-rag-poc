# LightRAG PoC - Vietnamese Legal Document Analysis

A complete **Proof of Concept** demonstrating hybrid Knowledge Graph + Vector RAG for Vietnamese legal text analysis, combining the power of graph-based reasoning with semantic search.

## 🎯 Project Overview

This PoC showcases how **LightRAG** (Lightweight Retrieval-Augmented Generation) with Knowledge Graph capabilities can enhance legal document analysis through:

- **Hybrid Retrieval**: Combines Knowledge Graph traversal with FAISS vector similarity search
- **Entity Extraction**: Identifies legal entities (Laws, Articles, Organizations) from Vietnamese text
- **Confidence Scoring**: Multi-factor scoring system with no-answer detection (NLP501 Req #4 & #5)
- **Provenance Tracking**: Maintains links between entities and source document chunks
- **Interactive Visualization**: Graph visualization using pyvis for exploring legal relationships

## 🏗️ Architecture

### Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Graph DB** | Neo4j 4.4 | Knowledge Graph storage & querying |
| **Vector DB** | FAISS (HNSW) | Fast similarity search for document chunks |
| **Embeddings** | sentence-transformers (MiniLM-L6-v2) | Semantic text representation |
| **NER/RE** | Regex-based heuristics | Entity & relation extraction (PoC-level) |
| **Visualization** | pyvis | Interactive HTML graph viewer |

### Data Flow

**Integrated Pipeline (Recommended):**

```
Vietnamese Legal Document (TXT/PDF/Images)
         ↓
    [ingest.py] ← Single command
         ↓
    ┌────────────────┬─────────────────┬─────────────────┐
    ↓                ↓                 ↓                 ↓
Chunks → FAISS   Entities         Relations        Neo4j KG
(embeddings)     (outputs/)       (outputs/)    (live database)
                                                       ↓
                                               [visualize.py]
                                                       ↓
                                                  graph.html
```

**Legacy Pipeline (Manual Steps):**

```
Vietnamese Legal Text (data/vn_law_sample.txt)
         ↓
    [ingest.py --no-kg]
         ↓
    ┌────────────────┬─────────────────┐
    ↓                ↓                 ↓
Chunks → FAISS   Entities → JSON   Relations → JSON
(embeddings)     (outputs/)         (outputs/)
                     ↓
                [kg_builder.py]
                     ↓
                  Neo4j KG
                (Entity-Chunk-Relation graph)
                     ↓
               [visualize.py]
                     ↓
               graph.html
```

## 📦 Project Structure

```
light-rag-poc/
├── docker-compose.yaml      # Neo4j service
├── requirements.txt         # Python dependencies
├── data/
│   └── vn_law_sample.txt   # Sample Vietnamese legal text
├── src/
│   ├── config.py           # Configuration & environment variables
│   ├── ingest.py           # Chunking, embedding, NER/RE
│   ├── kg_builder.py       # Neo4j graph population
│   ├── vector_store.py     # FAISS wrapper with metadata
│   └── visualize.py        # Interactive graph visualization
└── outputs/                # Generated artifacts (auto-created)
    ├── faiss.index
    ├── meta.json
    ├── entities.json
    ├── relations.json
    └── graph.html
```

## 🚀 Setup & Installation

### Prerequisites

- Python 3.8+
- Docker & Docker Compose
- 4GB+ RAM (for Neo4j)

### 1. Start Neo4j

```bash
docker-compose up -d
```

Neo4j will be available at:
- Browser: http://localhost:7474
- Bolt: bolt://localhost:7687
- Credentials: `neo4j` / `test`

### 2. Activate Virtual Environment

**IMPORTANT**: Always activate the virtual environment before running any commands in this project:

```bash
source ~/.lightRAG_env/bin/activate
```

> 💡 **Tip**: Add this to your shell profile or run it at the start of each session to ensure all dependencies are available.

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt

# Or install manually:
pip install 'unstructured[pdf]' pillow pytesseract pdfminer.six matplotlib unstructured-inference

# Install system dependencies for OCR (Ubuntu/Debian)
sudo apt-get install -y tesseract-ocr tesseract-ocr-vie poppler-utils

# macOS
# brew install tesseract poppler
```

**Optional**: Enable Landing AI's ADE for complex document fallback:
```bash
pip install landingai
export ADE_API_KEY="your_landing_ai_api_key"
```

### 4. Run the Integrated Pipeline

#### Quick Start: All-in-One Command

**NEW**: Single command for complete ingestion + knowledge graph building!

```bash
# Run the integrated pipeline (recommended)
python src/ingest.py --input data/vn_law_sample.txt

# This single command:
# ✓ Parses document (text/PDF/images)
# ✓ Generates chunks and embeddings
# ✓ Extracts entities and relations  
# ✓ Builds knowledge graph in Neo4j
# ✓ Saves all outputs
```

**Advanced options:**

```bash
# PDF documents (uses free Unstructured.io parser)
python src/ingest.py --input data/LIGHTRAG.pdf

# With optional ADE fallback for complex documents
python src/ingest.py --input data/LIGHTRAG.pdf --ade-api-key "your_key"

# Skip knowledge graph building (embeddings only)
python src/ingest.py --input data/LIGHTRAG.pdf --no-kg
```

The system uses a **hybrid parsing strategy**:
1. ✅ **Free parsers first** (Unstructured.io + OCR) - 90%+ of documents
2. ✅ **ADE fallback** (optional) - only for complex documents that need it

See [PARSER_SETUP.md](PARSER_SETUP.md) for parser details and [INTEGRATED_PIPELINE.md](INTEGRATED_PIPELINE.md) for complete pipeline documentation.

**What the integrated pipeline does:**
- Splits text into overlapping chunks (200 tokens, 50 overlap)
- Generates embeddings using MiniLM-L6-v2 (FAISS)
- Extracts entities: Articles (Điều), Laws (Luật), Organizations
- Detects co-occurrence relations between entities
- Creates knowledge graph in Neo4j with nodes and relationships
- Saves artifacts to `outputs/` directory

#### Legacy Mode: Separate Steps

If you prefer manual control:

```bash
# Step 1: Ingest only (skip KG)
python src/ingest.py --input data/vn_law_sample.txt --no-kg

# Step 2: Build KG separately
python src/kg_builder.py
```

#### Generate Visualization

```bash
# Step 3: Create interactive graph visualization
python src/visualize.py
```

**What happens:**
- Queries Neo4j for entities and relationships
- Creates nodes in the graph:
  - `Entity` (Law, Article, Organization)
  - `Chunk` (document chunks with text)
- Creates relationships:
  - `REL` between entities (co-occurrence)
  - `MENTIONED_IN` linking entities to chunks

#### Step 3: Visualize the Graph

```bash
python src/visualize.py
```

**Output:** Opens `outputs/graph.html` with interactive graph visualization

## 🔍 Core Capabilities

### 1. Document Chunking & Embedding
- Configurable chunk size with overlap
- Sentence-transformers embeddings (384-dim MiniLM)
- FAISS HNSW index for fast similarity search

### 2. Entity Extraction (Vietnamese Legal Text)
**Supported Entity Types:**
- **Article**: `Điều 1`, `Điều 5`, etc.
- **Law/Decree**: `Luật Bảo vệ Môi trường`, `Nghị định 2022`
- **Organization**: Capitalized sequences (e.g., "Bộ Tài nguyên và Môi trường")

### 3. Relation Extraction
- **Co-occurrence Relations**: Entities mentioned in the same chunk
- **Provenance**: Each entity linked to source chunks via `MENTIONED_IN`

### 4. Confidence Scoring ⭐ NEW!
**Multi-factor scoring system for answer quality (NLP501 Requirements #4 & #5)**

Confidence score based on 6 factors:
- **Similarity** (35%): Vector similarity score
- **Graph Connectivity** (20%): Entity/relation richness
- **Query Coverage** (20%): Query terms in text
- **Text Quality** (10%): Structure and completeness
- **Semantic Coherence** (10%): Question-answer alignment
- **Answer Presence** (5%): No-answer detection

**Example usage:**
```python
from src.graph_rag import GraphRAG

rag = GraphRAG()
# Query with verbose output showing confidence
answer = rag.query("Điều 10 quy định gì?", verbose=True)

# Output shows:
# Chunk 1:
#   Confidence: 0.789 ⭐ HIGH
#   Similarity: 0.823
#   Confidence factors:
#     - Similarity: 0.82
#     - Graph connectivity: 0.75
#     - Query coverage: 0.80
#     - Text quality: 0.95
```

**Confidence levels:**
- 0.80-1.00: **VERY HIGH** ⭐⭐⭐⭐⭐
- 0.70-0.79: **HIGH** ⭐⭐⭐⭐
- 0.50-0.69: **MEDIUM** ⭐⭐⭐
- 0.30-0.49: **LOW** ⭐⭐
- 0.00-0.29: **VERY LOW** (No-answer case) ⭐

See [CONFIDENCE_SCORING.md](CONFIDENCE_SCORING.md) for details.

### 5. Hybrid Retrieval
Current system combines:
- Vector embeddings in FAISS (semantic search)
- Knowledge Graph in Neo4j (structured queries)

**Retrieval strategy:**
1. Vector similarity search for relevant chunks
2. Graph expansion to find related entities
3. Confidence scoring for answer quality
4. Re-ranking by confidence

### 6. Interactive Graph Visualization
- pyvis-generated HTML
- Pan, zoom, drag nodes
- Hover for entity details
- Explore legal document relationships visually

## 📊 Sample Use Cases

### Legal Research Assistant
**Query:** "What are the penalties for environmental violations?"

**Retrieval Strategy:**
1. Vector search in FAISS for semantically similar chunks
2. Graph traversal: `(Nghị định)-[:REL]-(Điều)` to find related articles
3. Combine results with provenance links to source text

### Compliance Checker
**Query:** "Which organizations are responsible for environmental protection?"

**Retrieval Strategy:**
1. Cypher query: `MATCH (org:Entity {type: 'Org'})-[:REL]-(law:Entity {type: 'Law'})`
2. Retrieve chunks mentioning these organizations
3. Present context with graph visualization

### Citation Network Analysis
- Identify most-referenced articles (high degree centrality)
- Discover implicit connections between laws
- Visualize legal document structure

## ⚙️ Configuration

Edit [src/config.py](src/config.py) or use environment variables:

```python
# Neo4j Connection
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "test"

# FAISS Paths
FAISS_INDEX_PATH = "outputs/faiss.index"
META_PATH = "outputs/meta.json"

# Embedding Model
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Chunking Strategy
CHUNK_SIZE = 200        # tokens/words
CHUNK_OVERLAP = 50
```

## 🧪 Example Queries

### Neo4j Browser (http://localhost:7474)

```cypher
// Find all articles
MATCH (e:Entity {type: 'Article'})
RETURN e.name, e.eid LIMIT 10;

// Find laws and their related articles
MATCH (law:Entity {type: 'Law'})-[r:REL]-(article:Entity {type: 'Article'})
RETURN law.name, article.name, type(r);

// Find chunks mentioning a specific article
MATCH (e:Entity)-[:MENTIONED_IN]->(c:Chunk)
WHERE e.name CONTAINS 'Điều 5'
RETURN c.text LIMIT 5;

// Entity co-occurrence network
MATCH (a:Entity)-[r:REL]-(b:Entity)
RETURN a.name, b.name, a.type, b.type LIMIT 20;
```

### Python - FAISS Search

```python
from sentence_transformers import SentenceTransformer
from vector_store import FaissStore
import numpy as np

# Load model and index
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
store = FaissStore(384)  # 384-dim embeddings

# Search
query = "trách nhiệm bảo vệ môi trường"
qvec = model.encode([query])[0]
results = store.search(qvec, k=5)

for idx, score, meta in results:
    print(f"Score: {score:.4f}")
    print(f"Chunk: {meta['chunk_id']}")
    print(f"Text: {meta['text'][:200]}...\n")
```

## 🎯 Future Enhancements

### Short-term (PoC → MVP)
- [ ] REST API for hybrid search queries (FastAPI)
- [ ] Combine KG + vector scores with rank fusion
- [ ] Better Vietnamese NER using transformers (PhoBERT)
- [ ] Query logging and feedback collection

### Medium-term (Production-ready)
- [ ] Multi-document ingestion pipelineh
- [ ] Incremental updates (new laws/amendments)
- [ ] Entity resolution & deduplication
- [ ] Graph-based answer generation (RAG integration)
- [ ] User authentication & query history

### Advanced Features
- [ ] Temporal knowledge graph (track law changes over time)
- [ ] Multi-hop reasoning (chain legal references)
- [ ] Explainable AI (show reasoning path)
- [ ] Integration with LLMs (GPT-4, Claude) for natural language QA

## 📚 Purpose & Applications

### Research & Development
- **GraphRAG**: Demonstrate graph-enhanced RAG architectures
- **Legal AI**: Foundation for legal document analysis systems
- **Knowledge Management**: Enterprise knowledge agent prototypes

### Domain Applications
- **Legal Research Platforms**: Case law analysis, statute interpretation
- **Compliance Systems**: Automated regulation checking
- **Government Services**: Citizen-facing legal information portals
- **Corporate Legal Departments**: Contract analysis, risk assessment

### Educational
- Teaching Knowledge Graph concepts with real-world Vietnamese data
- Demonstrating hybrid retrieval architectures
- Exploring challenges in non-English NLP

## 🐛 Known Limitations (PoC Stage)

1. **NER/RE Quality**: Regex-based extraction is brittle
   - **Fix**: Use trained models (PhoBERT, ViHealthBERT)

2. **Vietnamese Language Handling**: Basic Unicode support
   - **Fix**: Better tokenization (pyvi, underthesea)

3. **Scalability**: Single-file ingestion only
   - **Fix**: Batch processing with progress tracking

4. **No Query Interface**: Manual Neo4j/Python queries
   - **Fix**: Build FastAPI search endpoint

5. **Entity Disambiguation**: Multiple "Điều 1" from different laws not resolved
   - **Fix**: Add document-level context to entity IDs

## 📄 License

MIT License - Feel free to use for research and commercial purposes.

## 🤝 Contributing

This is a proof-of-concept project. Contributions welcome:
- Better Vietnamese NER models
- Hybrid retrieval algorithms
- Additional legal document parsers
- Performance optimizations

## 📞 Contact & Support

For questions about this PoC or collaboration opportunities:
- Create an issue in this repository
- Fork and submit pull requests

---

**Built with ❤️ for Vietnamese Legal AI Research**

*Demonstrating the power of Knowledge Graphs + RAG for domain-specific document analysis*
