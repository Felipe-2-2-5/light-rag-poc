# Integrated Ingestion & Knowledge Graph Pipeline

## Overview

The integrated pipeline combines document ingestion, vector embedding, entity extraction, and knowledge graph building into a single unified workflow. This eliminates the need to run multiple separate scripts and ensures data consistency.

## Architecture

```
Document Input → Parse → Chunk → Embed → Extract Entities → Build KG → Store
                                    ↓                            ↓
                                 FAISS                        Neo4j
```

### Components

1. **Document Parser** - Handles multiple formats (PDF, TXT, images) with hybrid parsing
2. **Text Chunker** - Splits documents into semantic chunks
3. **Vector Store** - FAISS-based similarity search
4. **Entity Extractor** - NER/RE for Vietnamese legal text
5. **Knowledge Graph Builder** - Direct Neo4j integration

## Usage

### Basic Usage

```bash
python src/ingest.py --input path/to/document.pdf
```

This single command performs:
- ✓ Document parsing
- ✓ Text chunking
- ✓ Vector embedding generation
- ✓ Entity and relation extraction
- ✓ Knowledge graph creation in Neo4j
- ✓ Metadata persistence

### Advanced Options

```bash
# Skip knowledge graph building
python src/ingest.py --input document.pdf --no-kg

# Use ADE API for complex documents
python src/ingest.py --input scanned.pdf --ade-api-key YOUR_API_KEY

# Use environment variable for ADE
export ADE_API_KEY=your_key_here
python src/ingest.py --input document.pdf
```

## Outputs

### Files Created

| File | Description |
|------|-------------|
| `outputs/faiss.index` | FAISS vector index |
| `outputs/meta.json` | Chunk metadata (IDs, text) |
| `outputs/entities.json` | Extracted entities with metadata |
| `outputs/relations.json` | Entity relationships |

### Neo4j Database

**Node Types:**
- `Entity`: Extracted entities (Articles, Laws, Organizations)
- `Chunk`: Text chunks from the document

**Relationships:**
- `REL`: Entity-to-entity relations (e.g., MENTIONED_WITH)
- `MENTIONED_IN`: Entity-to-chunk links

**Properties:**
- Entity: `eid`, `name`, `type`, `source_chunk`
- Chunk: `chunk_id`, `text`, `doc_id`
- Relation: `type`, `first_seen`

## Query Examples

### Neo4j Cypher Queries

```cypher
// Find all entities in the graph
MATCH (e:Entity) RETURN e LIMIT 25

// Find entities by type
MATCH (e:Entity {type: 'Article'}) RETURN e

// Find related entities
MATCH (e1:Entity)-[r:REL]->(e2:Entity)
RETURN e1.name, r.type, e2.name

// Find chunks containing specific entities
MATCH (e:Entity {type: 'Law'})-[:MENTIONED_IN]->(c:Chunk)
RETURN e.name, c.text LIMIT 5

// Find co-occurring entities in same chunk
MATCH (e1:Entity)-[:MENTIONED_IN]->(c:Chunk)<-[:MENTIONED_IN]-(e2:Entity)
WHERE e1 <> e2
RETURN e1.name, e2.name, c.chunk_id
```

### Vector Search (Python)

```python
from sentence_transformers import SentenceTransformer
from src.vector_store import FaissStore

# Load model and store
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
store = FaissStore(384)

# Search for similar chunks
query = "điều luật về môi trường"
qvec = model.encode([query])[0]
results = store.search(qvec, k=5)

for idx, score, meta in results:
    print(f"Chunk: {meta['chunk_id']}")
    print(f"Score: {score:.4f}")
    print(f"Text: {meta['text'][:200]}...\n")
```

## Configuration

### Environment Variables

```bash
# Neo4j connection
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="test"

# Embedding model
export EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"

# Chunking parameters
export CHUNK_SIZE="200"
export CHUNK_OVERLAP="50"

# Optional: ADE API for complex documents
export ADE_API_KEY="your_landing_ai_key"
```

### Code Configuration

Edit [src/config.py](src/config.py) to change defaults.

## Error Handling

The integrated pipeline includes robust error handling:

- **Neo4j Connection Failures**: Pipeline continues, KG skipped with warning
- **Parser Failures**: Falls back to alternative parsers
- **Duplicate Entities**: MERGE operations prevent duplicates
- **Invalid Relations**: Individual failures logged, pipeline continues

## Performance

### Benchmarks (Sample Document)

| Step | Time | Output |
|------|------|--------|
| Parse | 1-2s | Text extraction |
| Chunk | <1s | ~50 chunks |
| Embed | 5-10s | 384-dim vectors |
| NER/RE | 2-3s | ~30 entities |
| KG Build | 3-5s | Neo4j graph |
| **Total** | **15-20s** | Complete pipeline |

### Scalability

- **Small docs** (<10 pages): 15-30 seconds
- **Medium docs** (10-100 pages): 1-5 minutes
- **Large docs** (100+ pages): 5-20 minutes

Use `--no-kg` flag for faster processing when KG is not needed.

## Troubleshooting

### Neo4j Connection Error

```bash
# Check Neo4j is running
docker ps | grep neo4j

# Start Neo4j if not running
docker-compose up -d

# Check logs
docker logs light-rag-poc_neo4j_1
```

### Import Errors

```bash
# Ensure all dependencies are installed
pip install -r requirements.txt

# For Neo4j driver specifically
pip install neo4j
```

### No Entities Found

The Vietnamese legal text extractor uses heuristic patterns. If no entities are found:
- Check document language (Vietnamese expected)
- Verify text parsing quality
- Review entity patterns in `simple_ner_and_relations()` function

## Next Steps

- Query the knowledge graph via Neo4j Browser: http://localhost:7474
- Generate visualization: `python src/visualize.py`
- Implement semantic search API: `python api_example.py`
- Extend entity extraction patterns for better coverage
