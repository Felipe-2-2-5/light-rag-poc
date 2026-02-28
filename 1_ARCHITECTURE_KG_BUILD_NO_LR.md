# Architecture Documentation

## System Overview

The LightRAG PoC implements a **hybrid retrieval architecture** combining:
- **Semantic Search**: FAISS vector similarity for contextual matching
- **Structured Queries**: Neo4j graph database for entity relationships
- **Provenance Tracking**: Links between entities, chunks, and source documents

## Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Query                            │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  Vector Search  │     │  Graph Search   │
│     (FAISS)     │     │    (Neo4j)      │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │    ┌──────────────┐   │
         └───►│ Rank Fusion  │◄──┘
              └──────┬───────┘
                     │
                     ▼
              ┌─────────────┐
              │   Results   │
              └─────────────┘
```

## Data Pipeline

### Phase 1: Ingestion (ingest.py)

```
Raw Text
   │
   ├─► Chunking (overlapping windows)
   │     └─► Chunk[0..N]
   │
   ├─► Embedding Generation
   │     └─► SentenceTransformer.encode()
   │           └─► Vector[384-dim]
   │
   ├─► FAISS Indexing
   │     └─► HNSW Index
   │           └─► faiss.index + meta.json
   │
   └─► Entity Extraction
         ├─► Regex-based NER
         │     ├─► Articles (Điều N)
         │     ├─► Laws (Luật X)
         │     └─► Organizations
         │
         └─► Relation Extraction
               └─► Co-occurrence heuristics
                     └─► entities.json + relations.json
```

### Phase 2: Knowledge Graph Construction (kg_builder.py)

```
entities.json + relations.json
   │
   ├─► Neo4j Schema Creation
   │     ├─► Node: Entity (eid, name, type, source_chunk)
   │     ├─► Node: Chunk (chunk_id, text, doc_id)
   │     │
   │     └─► Relationships:
   │           ├─► (Entity)-[:REL]->(Entity)
   │           └─► (Entity)-[:MENTIONED_IN]->(Chunk)
   │
   └─► Graph Population
         └─► Cypher MERGE operations
```

### Phase 3: Visualization (visualize.py)

```
Neo4j Graph
   │
   ├─► Cypher Query
   │     └─► MATCH (a)-[r]->(b) RETURN ...
   │
   └─► pyvis Network
         ├─► add_node() for entities
         ├─► add_edge() for relationships
         └─► show() → graph.html
```

## Data Models

### Vector Store (FAISS)

**Index Type**: HNSW (Hierarchical Navigable Small World)
- **Dimension**: 384 (MiniLM-L6-v2)
- **Distance Metric**: L2 (Euclidean)
- **Pros**: Fast approximate nearest neighbor search
- **Cons**: Memory-intensive for large datasets

**Metadata Structure** (meta.json):
```json
{
  "0": {
    "chunk_id": "vn_law_sample.txt_C0",
    "text": "LUẬT BẢO VỆ MÔI TRƯỜNG — Điều 1..."
  },
  "1": { ... }
}
```

### Knowledge Graph (Neo4j)

**Node Labels:**

1. **Entity**
   - Properties: `eid`, `name`, `type`, `source_chunk`
   - Types: Article, Law, Org
   - Example: `(:Entity {eid: "ARTICLE_Điều_5", name: "Điều 5", type: "Article"})`

2. **Chunk**
   - Properties: `chunk_id`, `text`, `doc_id`
   - Example: `(:Chunk {chunk_id: "vn_law_sample.txt_C3", text: "..."})`

**Relationship Types:**

1. **REL** (Entity-Entity)
   - Type: Co-occurrence
   - Properties: `type` (relationship label), `first_seen` (timestamp)
   - Example: `(Law)-[:REL {type: "MENTIONED_WITH"}]->(Article)`

2. **MENTIONED_IN** (Entity-Chunk)
   - Provenance link
   - Example: `(Entity)-[:MENTIONED_IN]->(Chunk)`

**Graph Schema:**
```
(Entity:Article)-[:REL]->(Entity:Law)
       │
       └─[:MENTIONED_IN]->(Chunk)
                             │
                             └─[has_embedding]->(FAISS)
```

## Retrieval Strategies

### 1. Pure Vector Search

**Algorithm:**
1. Encode query: `q_vec = model.encode(query)`
2. Search FAISS: `D, I = index.search(q_vec, k)`
3. Return top-k chunks with metadata

**Strengths:**
- Semantic similarity (handles synonyms, paraphrases)
- Fast (HNSW index)

**Weaknesses:**
- No structured reasoning
- Ignores entity relationships

### 2. Pure Graph Search

**Algorithm:**
1. Entity matching: `MATCH (e:Entity) WHERE e.name CONTAINS query`
2. Traverse graph: Find related entities via REL
3. Retrieve chunks: Follow MENTIONED_IN edges

**Strengths:**
- Precise entity-based retrieval
- Exploits document structure

**Weaknesses:**
- Requires exact entity names
- Brittle to spelling variations

### 3. Hybrid Retrieval (Recommended)

**Algorithm (Rank Fusion):**
```python
# Step 1: Vector search
vec_results = faiss_search(query, k=10)

# Step 2: Graph search
graph_results = neo4j_entity_search(query, k=10)

# Step 3: Merge & re-rank
for chunk_id in (vec_results ∪ graph_results):
    score = α * vector_score + β * graph_score
    # α=0.6, β=0.4 as heuristic

# Step 4: Return top-k
return sorted_by_score(results)[:k]
```

**Rank Fusion Methods:**
- **Reciprocal Rank Fusion (RRF)**: `score = Σ 1/(k + rank_i)`
- **Linear Combination**: `score = α*s_vec + β*s_graph`
- **Graph-enhanced Re-ranking**: Use PageRank or betweenness centrality

## Entity Extraction (NER/RE)

### Current Implementation (Regex Heuristics)

**Vietnamese Legal Patterns:**

1. **Articles**: `Điều\s*\d+` → Điều 1, Điều 5, etc.
2. **Laws**: `(Luật|Nghị định)\s*[^\.,\n]+` → Luật Bảo vệ Môi trường
3. **Organizations**: Capitalized sequences (crude)

**Relation Extraction:**
- **Co-occurrence**: If entities appear in same chunk → REL

### Future Enhancements

**Transformer-based NER:**
- Model: PhoBERT, ViHealthBERT, or custom-trained
- Training Data: Annotated Vietnamese legal corpus
- Output: BIO tags → Entity spans

**Advanced RE:**
- Dependency parsing for legal "cites" relations
- Rule-based: "theo Điều X Luật Y" → (Điều X)-[:CITES]->(Luật Y)
- ML-based: Relation classification models

## Configuration Management

### Environment Variables (config.py)

```python
# Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "test")

# FAISS
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "outputs/faiss.index")
META_PATH = os.getenv("META_PATH", "outputs/meta.json")

# Embeddings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "200"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
```

### Tuning Parameters

| Parameter | Default | Tuning Guide |
|-----------|---------|--------------|
| `CHUNK_SIZE` | 200 | ↑ for longer context, ↓ for precision |
| `CHUNK_OVERLAP` | 50 | ↑ to reduce boundary issues |
| `EMBEDDING_MODEL` | MiniLM-L6-v2 | Try `paraphrase-multilingual-mpnet-base-v2` for Vietnamese |
| `FAISS_INDEX` | HNSW | Consider `IndexIVFFlat` for larger datasets |

## Performance Considerations

### Scalability Limits (PoC)

| Component | Current | Limit | Solution |
|-----------|---------|-------|----------|
| FAISS | In-memory | ~10M vectors (16GB RAM) | Use `IndexIVFPQ` or Milvus |
| Neo4j | Single instance | ~100M nodes | Neo4j clustering |
| Ingestion | Sequential | ~1K docs/hour | Parallel processing |

### Optimization Strategies

**FAISS:**
- Use GPU acceleration (`faiss-gpu`)
- Product Quantization (PQ) for compression
- Shard index for distributed search

**Neo4j:**
- Create indexes: `CREATE INDEX ON :Entity(eid)`
- Use `LIMIT` in queries
- Batch writes with transactions

**Embeddings:**
- Cache embeddings for frequent queries
- Use smaller models (distilled MiniLM)
- Batch encoding for throughput

## Security & Deployment

### Production Checklist

- [ ] Change Neo4j default password
- [ ] Enable Neo4j authentication & encryption
- [ ] Restrict Cypher query endpoint (no user input)
- [ ] Rate limiting on API endpoints
- [ ] Input validation for all queries
- [ ] HTTPS for API access
- [ ] Docker secrets for credentials
- [ ] Regular backups of Neo4j data
- [ ] Monitor query performance

### Docker Deployment

```yaml
# Production docker-compose.yaml
services:
  neo4j:
    image: neo4j:4.4
    environment:
      - NEO4J_AUTH=${NEO4J_USER}/${NEO4J_PASSWORD}
      - NEO4J_dbms_memory_heap_max__size=2G
    volumes:
      - neo4j_data:/data
    restart: unless-stopped
  
  api:
    build: .
    environment:
      - NEO4J_URI=bolt://neo4j:7687
    ports:
      - "8000:8000"
    depends_on:
      - neo4j
```

## Monitoring & Observability

### Key Metrics

**System:**
- FAISS search latency (ms)
- Neo4j query time (ms)
- API response time (p50, p95, p99)

**Data:**
- Total entities/chunks
- Graph density (edges/nodes)
- Query coverage (% queries finding results)

**Quality:**
- Retrieval precision@k
- Entity extraction F1 score
- User feedback (thumbs up/down)

### Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Log search queries
logger.info(f"Search query: {query}, method: {method}, results: {len(results)}")

# Log errors
logger.error(f"Neo4j connection failed: {e}")
```

## Testing Strategy

### Unit Tests
- `test_chunking()`: Verify chunk sizes and overlaps
- `test_embedding()`: Check embedding dimensions
- `test_faiss_search()`: Validate search results
- `test_neo4j_queries()`: Cypher query correctness

### Integration Tests
- End-to-end pipeline: ingest → kg_builder → search
- API endpoint testing
- Docker compose health checks

### Evaluation
- **Retrieval Quality**: NDCG, MAP, MRR
- **Entity Extraction**: Precision, Recall, F1 (gold annotations needed)
- **Graph Quality**: Manual inspection of entity relationships

## References

### Technologies
- [FAISS](https://github.com/facebookresearch/faiss) - Vector similarity search
- [Neo4j](https://neo4j.com/docs/) - Graph database
- [Sentence Transformers](https://www.sbert.net/) - Embeddings
- [pyvis](https://pyvis.readthedocs.io/) - Network visualization

### Research
- GraphRAG: [Microsoft Research](https://www.microsoft.com/en-us/research/blog/graphrag/)
- LightRAG: Lightweight RAG architectures
- Vietnamese NLP: PhoBERT, VnCoreNLP

---

**Version**: 0.1.0 (PoC)  
**Last Updated**: December 2025
