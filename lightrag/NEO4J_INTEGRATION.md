# LightRAG Neo4j Database Integration

This integration automatically saves LightRAG ingestion outputs to a Neo4j graph database for efficient searching and querying.

## Features

- **Automatic Storage**: Entities, relationships, and chunks are automatically saved to Neo4j during ingestion
- **Graph Search**: Query the knowledge graph using Cypher queries or the provided search interface
- **Fast Lookups**: Indexed entities and relationships for quick retrieval
- **Visual Exploration**: Browse the knowledge graph in Neo4j Browser

## Architecture

```
LightRAG Ingestion → JSON Storage → Neo4j Database
                                   ↓
                            Graph Queries & Search
```

### Data Model

```
(LightRAGEntity) --[LIGHTRAG_RELATION]--> (LightRAGEntity)
        |
   [MENTIONED_IN]
        ↓
  (LightRAGChunk) --[PART_OF]--> (LightRAGDocument)
```

**Nodes:**
- `LightRAGEntity`: Entities extracted from documents
  - Properties: `entity_name`, `entity_type`, `description`, `source_id`
- `LightRAGChunk`: Text chunks from documents
  - Properties: `chunk_id`, `content`, `tokens`, `chunk_order_index`
- `LightRAGDocument`: Source documents
  - Properties: `doc_id`

**Relationships:**
- `LIGHTRAG_RELATION`: Connects related entities
  - Properties: `relation_type`, `description`, `weight`
- `MENTIONED_IN`: Links entities to chunks where they appear
- `PART_OF`: Links chunks to their parent document

## Setup

### 1. Start Neo4j Database

Using Docker (recommended):

```bash
# Start Neo4j with docker-compose
docker-compose up -d

# Or run Neo4j directly
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/test \
  neo4j:latest
```

### 2. Configure Environment

Add Neo4j credentials to your `.env` file:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=test
```

### 3. Install Dependencies

```bash
pip install neo4j==5.11.0 tabulate>=0.9.0
```

## Usage

### Ingest Documents (Auto-saves to Neo4j)

By default, ingestion now saves to Neo4j automatically:

```bash
# Standard ingestion with Neo4j storage
python lightrag_ingest.py --input data/document.pdf

# Skip Neo4j storage (only save to files)
python lightrag_ingest.py --input data/document.pdf --skip-neo4j
```

### Manual Database Save

Save existing LightRAG storage to Neo4j:

```bash
# Using the storage module directly
python src/lightrag_db_storage.py ./lightrag_storage

# Or from Python
from src.lightrag_db_storage import save_lightrag_to_database

save_lightrag_to_database(
    working_dir="./lightrag_storage",
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="test",
    clear_existing=True
)
```

### Search the Database

Use the search interface:

```bash
# Search for entities
python search_neo4j.py --entity "environment"
python search_neo4j.py --entity "Luật Bảo Vệ Môi Trường"

# Find relationships
python search_neo4j.py --relation "Xử Phạt"

# Find connected entities
python search_neo4j.py --connected "Bộ Tài Nguyên Và Môi Trường"

# Get chunks mentioning an entity
python search_neo4j.py --chunks-for "Nghị Định"

# Search by entity type
python search_neo4j.py --type "ORGANIZATION"

# Full-text search
python search_neo4j.py --search "môi trường"

# Show database statistics
python search_neo4j.py --stats
```

### Browse in Neo4j Browser

1. Open http://localhost:7474 in your browser
2. Login with credentials (neo4j/test)
3. Run Cypher queries:

```cypher
// View all entities
MATCH (e:LightRAGEntity) RETURN e LIMIT 25

// View entities and relationships
MATCH (e1:LightRAGEntity)-[r:LIGHTRAG_RELATION]->(e2:LightRAGEntity)
RETURN e1, r, e2 LIMIT 50

// Find entities by type
MATCH (e:LightRAGEntity)
WHERE e.entity_type = 'ORGANIZATION'
RETURN e

// Find all chunks mentioning an entity
MATCH (e:LightRAGEntity {entity_name: 'Luật Bảo Vệ Môi Trường'})
      -[:MENTIONED_IN]->(c:LightRAGChunk)
RETURN e, c

// Find paths between two entities
MATCH path = shortestPath(
  (a:LightRAGEntity {entity_name: 'Bộ Tài Nguyên Và Môi Trường'})
  -[*..5]->
  (b:LightRAGEntity {entity_name: 'Luật Bảo Vệ Môi Trường'})
)
RETURN path
```

## Search Examples

### Example 1: Find Environmental Organizations

```bash
python search_neo4j.py --type "ORGANIZATION" --limit 20
```

### Example 2: Explore Entity Connections

```bash
# Find what's connected to "Bộ Tài Nguyên Và Môi Trường"
python search_neo4j.py --connected "Bộ Tài Nguyên"
```

### Example 3: Get Context for an Entity

```bash
# Get text chunks where "Luật Bảo Vệ Môi Trường" is mentioned
python search_neo4j.py --chunks-for "Luật Bảo Vệ Môi Trường"
```

### Example 4: Full-Text Search

```bash
# Search across all entities, descriptions, and chunks
python search_neo4j.py --search "xử phạt hành chính"
```

## Performance Tips

1. **Indexes**: Indexes are automatically created on:
   - `LightRAGEntity.entity_name`
   - `LightRAGEntity.entity_type`
   - `LightRAGChunk.chunk_id`
   - `LightRAGDocument.doc_id`

2. **Batch Operations**: Large ingestions are processed in batches (100 entities, 100 relations, 50 chunks at a time)

3. **Clear Old Data**: Use `clear_existing=True` to remove old data before re-ingestion

## Integration with Existing Query Tools

The Neo4j database can be used alongside existing query methods:

```bash
# LightRAG native query (uses vector + graph from JSON files)
python lightrag_query.py "What are the environmental regulations?" --mode hybrid

# Neo4j graph query (uses Neo4j database)
python search_neo4j.py --search "environmental regulations"

# Custom RAG with Neo4j (src/graph_rag.py)
python query_rag.py "What are the environmental regulations?"
```

## Troubleshooting

### Connection Failed

```bash
# Check if Neo4j is running
docker ps | grep neo4j

# View Neo4j logs
docker logs neo4j

# Restart Neo4j
docker restart neo4j
```

### Authentication Error

```bash
# Reset Neo4j password
docker exec -it neo4j cypher-shell -u neo4j -p neo4j
# Then run: ALTER CURRENT USER SET PASSWORD FROM 'neo4j' TO 'test';
```

### Database Empty After Ingestion

```bash
# Manually save to Neo4j
python src/lightrag_db_storage.py ./lightrag_storage

# Check statistics
python search_neo4j.py --stats
```

### Clear All Data

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "test"))
with driver.session() as session:
    session.run("MATCH (n) DETACH DELETE n")
driver.close()
```

## API Reference

### LightRAGNeo4jStorage Class

```python
from src.lightrag_db_storage import LightRAGNeo4jStorage

# Initialize
storage = LightRAGNeo4jStorage(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="test"
)

# Save data
storage.save_lightrag_to_neo4j(
    working_dir="./lightrag_storage",
    clear_existing=True
)

# Get statistics
storage.print_neo4j_statistics()

# Close connection
storage.close()
```

### Neo4jSearcher Class

```python
from search_neo4j import Neo4jSearcher

searcher = Neo4jSearcher(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="test"
)

# Search entities
entities = searcher.search_entities("environment", limit=10)

# Find relationships
relations = searcher.find_relationships("Bộ Tài Nguyên", limit=10)

# Find connected entities
connected = searcher.find_connected_entities("Luật Bảo Vệ", limit=10)

# Get chunks
chunks = searcher.find_chunks_for_entity("Nghị Định", limit=5)

# Full-text search
results = searcher.full_text_search("môi trường", limit=20)

searcher.close()
```

## Benefits

1. **Fast Graph Queries**: Traverse entity relationships efficiently
2. **Flexible Searching**: Combine vector search with graph traversal
3. **Visual Exploration**: Use Neo4j Browser to visualize knowledge graph
4. **Production Ready**: Scalable database backend for large document collections
5. **Integration**: Works alongside existing LightRAG query tools

## Next Steps

- Query the graph: `python search_neo4j.py --help`
- Visual exploration: http://localhost:7474
- Integrate with custom RAG: See `src/graph_rag.py` for examples
- Advanced queries: Learn Cypher at https://neo4j.com/docs/cypher-manual/
