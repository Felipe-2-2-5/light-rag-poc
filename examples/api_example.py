"""
Example FastAPI implementation for hybrid search (KG + Vector)
This demonstrates how to combine Neo4j graph queries with FAISS vector search.

To run (from the project root):
    pip install fastapi uvicorn
    uvicorn examples.api_example:app --reload
    
Access docs at: http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase
from typing import List, Optional
import os

from src.vector_store import FaissStore
from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, EMBEDDING_MODEL

app = FastAPI(
    title="Vietnamese Legal RAG API",
    description="Hybrid Knowledge Graph + Vector search for Vietnamese legal documents",
    version="0.1.0"
)

# Initialize models and connections
model = SentenceTransformer(EMBEDDING_MODEL)
vector_store = FaissStore(384)  # 384-dim for MiniLM
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    method: str = "hybrid"  # "vector", "graph", or "hybrid"
    entity_types: Optional[List[str]] = None  # Filter by entity type


class SearchResult(BaseModel):
    chunk_id: str
    text: str
    score: float
    source: str  # "vector" or "graph"
    entities: Optional[List[dict]] = None


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total: int


@app.get("/")
def root():
    return {
        "service": "Vietnamese Legal RAG API",
        "status": "running",
        "endpoints": ["/search", "/entities", "/graph/query", "/health"]
    }


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    """
    Hybrid search combining vector similarity and graph traversal.
    
    Methods:
    - vector: FAISS similarity search only
    - graph: Neo4j entity search only  
    - hybrid: Combine both with rank fusion
    """
    results = []
    
    if request.method in ["vector", "hybrid"]:
        # Vector search
        qvec = model.encode([request.query])[0]
        vector_results = vector_store.search(qvec, k=request.top_k)
        
        for idx, score, meta in vector_results:
            results.append(SearchResult(
                chunk_id=meta.get("chunk_id", f"chunk_{idx}"),
                text=meta.get("text", "")[:500],
                score=float(score),
                source="vector",
                entities=None
            ))
    
    if request.method in ["graph", "hybrid"]:
        # Graph search: Find entities matching query, then retrieve chunks
        with neo4j_driver.session() as session:
            # Simple text matching on entity names (can be improved with fuzzy search)
            cypher = """
            MATCH (e:Entity)-[:MENTIONED_IN]->(c:Chunk)
            WHERE toLower(e.name) CONTAINS toLower($query)
            RETURN DISTINCT c.chunk_id AS chunk_id, c.text AS text, 
                   collect(DISTINCT {name: e.name, type: e.type}) AS entities
            LIMIT $limit
            """
            graph_results = session.run(cypher, parameters={"query": request.query, "limit": request.top_k})
            
            for record in graph_results:
                results.append(SearchResult(
                    chunk_id=record["chunk_id"],
                    text=record["text"][:500] if record["text"] else "",
                    score=1.0,  # Graph results get uniform score (could use PageRank)
                    source="graph",
                    entities=record["entities"]
                ))
    
    # Rank fusion for hybrid results (simple deduplication by chunk_id)
    if request.method == "hybrid":
        seen = {}
        fused = []
        for r in results:
            if r.chunk_id not in seen:
                seen[r.chunk_id] = r
                fused.append(r)
            else:
                # Merge: boost score if found in both sources
                seen[r.chunk_id].score += r.score * 0.5
                if r.entities:
                    seen[r.chunk_id].entities = r.entities
        results = sorted(fused, key=lambda x: x.score, reverse=True)[:request.top_k]
    
    return SearchResponse(
        query=request.query,
        results=results[:request.top_k],
        total=len(results)
    )


@app.get("/entities")
def list_entities(entity_type: Optional[str] = None, limit: int = 50):
    """List all entities in the knowledge graph, optionally filtered by type."""
    with neo4j_driver.session() as session:
        if entity_type:
            cypher = """
            MATCH (e:Entity {type: $entity_type})
            RETURN e.eid AS id, e.name AS name, e.type AS type, e.source_chunk AS chunk
            LIMIT $limit
            """
            results = session.run(cypher, parameters={"entity_type": entity_type, "limit": limit})
        else:
            cypher = """
            MATCH (e:Entity)
            RETURN e.eid AS id, e.name AS name, e.type AS type, e.source_chunk AS chunk
            LIMIT $limit
            """
            results = session.run(cypher, parameters={"limit": limit})
        
        return {"entities": [dict(r) for r in results]}


@app.get("/entities/{entity_id}/context")
def entity_context(entity_id: str):
    """Get the context (chunks and related entities) for a specific entity."""
    with neo4j_driver.session() as session:
        cypher = """
        MATCH (e:Entity {eid: $eid})
        OPTIONAL MATCH (e)-[:MENTIONED_IN]->(c:Chunk)
        OPTIONAL MATCH (e)-[r:REL]-(related:Entity)
        RETURN e.name AS name, e.type AS type,
               collect(DISTINCT c.text) AS chunks,
               collect(DISTINCT {name: related.name, type: related.type, relation: type(r)}) AS related
        """
        result = session.run(cypher, parameters={"eid": entity_id}).single()
        
        if not result:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        return {
            "entity": {"id": entity_id, "name": result["name"], "type": result["type"]},
            "chunks": result["chunks"],
            "related_entities": result["related"]
        }


@app.post("/graph/query")
def custom_cypher(query: str):
    """
    Execute custom Cypher query (admin only in production!).
    Example: MATCH (n:Entity) RETURN n.name, n.type LIMIT 10
    """
    with neo4j_driver.session() as session:
        try:
            results = session.run(query)
            return {"results": [dict(r) for r in results]}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


@app.get("/health")
def health_check():
    """Check if Neo4j and FAISS are accessible."""
    status = {"neo4j": "unknown", "faiss": "unknown"}
    
    try:
        with neo4j_driver.session() as session:
            session.run("RETURN 1")
        status["neo4j"] = "connected"
    except Exception as e:
        status["neo4j"] = f"error: {str(e)}"
    
    try:
        if vector_store.index and vector_store.index.ntotal > 0:
            status["faiss"] = f"ready ({vector_store.index.ntotal} vectors)"
        else:
            status["faiss"] = "empty"
    except Exception as e:
        status["faiss"] = f"error: {str(e)}"
    
    return status


@app.on_event("shutdown")
def shutdown():
    """Close connections on shutdown."""
    neo4j_driver.close()


# Example usage:
"""
# Vector search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "môi trường", "method": "vector", "top_k": 3}'

# Graph search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Điều 5", "method": "graph", "top_k": 3}'

# Hybrid search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "trách nhiệm bảo vệ", "method": "hybrid", "top_k": 5}'

# List entities
curl http://localhost:8000/entities?entity_type=Article&limit=10

# Get entity context
curl http://localhost:8000/entities/ARTICLE_Điều_5/context

# Health check
curl http://localhost:8000/health
"""
