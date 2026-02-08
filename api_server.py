#!/usr/bin/env python3
"""
FastAPI Server for Custom GPT Integration

This server exposes the hybrid RAG retrieval system as a REST API
that can be called by the custom GPT at ChatGPT.

It follows the evidence contract defined in:
- custom-gpt/customer-gpt.md
- custom-gpt/knowledge_hybrid_index.md
"""

import os
import sys
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

# Load environment
load_dotenv()

# Import local modules
from src.vector_store import FaissStore
from src.confidence_scorer import ConfidenceScorer
from src.config import (
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, 
    EMBEDDING_MODEL, FAISS_INDEX_PATH, META_PATH
)

# Initialize FastAPI app
app = FastAPI(
    title="Internal Knowledge Navigator API",
    description="Hybrid RAG retrieval system for Custom GPT integration",
    version="1.0.0"
)

# Enable CORS for ChatGPT
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chatgpt.com", "https://chat.openai.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
_vector_store = None
_graph_driver = None
_embedding_model = None
_confidence_scorer = None


def initialize_system():
    """Initialize retrieval system components"""
    global _vector_store, _graph_driver, _embedding_model, _confidence_scorer
    
    if _vector_store is None:
        print("🔄 Initializing retrieval system...")
        
        # Load embedding model
        print(f"📦 Loading embedding model: {EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        
        # Load vector store
        print(f"📂 Loading FAISS index from: {FAISS_INDEX_PATH}")
        dim = _embedding_model.get_sentence_embedding_dimension()
        _vector_store = FaissStore(dim)
        _vector_store.load()
        
        # Connect to Neo4j
        print(f"🔗 Connecting to Neo4j at: {NEO4J_URI}")
        _graph_driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        
        # Initialize confidence scorer
        _confidence_scorer = ConfidenceScorer()
        
        print("✅ System initialized successfully!")


# Pydantic models for API
class VectorEvidence(BaseModel):
    """Vector search evidence chunk"""
    chunk_id: str = Field(description="Unique chunk identifier")
    text: str = Field(description="Chunk text content")
    similarity: float = Field(description="Similarity score (0-1)")
    authority: str = Field(description="Authority level: PRIMARY, SECONDARY, CONTEXTUAL")
    

class GraphNode(BaseModel):
    """Knowledge graph node"""
    id: str = Field(description="Entity ID")
    label: str = Field(description="Entity label/name")
    type: str = Field(description="Entity type (Article, Law, Org, etc.)")


class GraphEdge(BaseModel):
    """Knowledge graph edge/relationship"""
    source: str = Field(description="Source entity ID")
    relation: str = Field(description="Relation type")
    target: str = Field(description="Target entity ID")


class GraphEvidence(BaseModel):
    """Knowledge graph evidence"""
    nodes: List[GraphNode] = Field(description="Retrieved graph nodes")
    edges: List[GraphEdge] = Field(description="Retrieved graph edges")
    traversal_path: Optional[str] = Field(description="Human-readable traversal path")


class RetrievalIntent(BaseModel):
    """Query intent classification"""
    primary: str = Field(description="Primary intent type")
    secondary: Optional[str] = Field(default=None, description="Secondary intent type")
    confidence: float = Field(description="Intent classification confidence")


class EvidenceResponse(BaseModel):
    """Structured evidence response for Custom GPT"""
    query: str = Field(description="Original user query")
    intent: RetrievalIntent = Field(description="Classified query intent")
    vector_evidence: List[VectorEvidence] = Field(description="Vector search results")
    graph_evidence: Optional[GraphEvidence] = Field(description="Knowledge graph context")
    confidence: str = Field(description="Overall confidence: HIGH, MEDIUM, LOW")
    confidence_score: float = Field(description="Numeric confidence score (0-1)")
    retrieval_strategy: str = Field(description="Strategy used: VECTOR_PRIMARY, GRAPH_PRIMARY, HYBRID")
    evidence_summary: str = Field(description="Brief summary of evidence retrieved")


class QueryRequest(BaseModel):
    """Query request from Custom GPT"""
    query: str = Field(description="User's question")
    max_results: int = Field(default=5, ge=1, le=10, description="Maximum results to return")
    include_graph: bool = Field(default=True, description="Include graph traversal")


# Intent classification logic
def classify_intent(query: str) -> RetrievalIntent:
    """
    Classify query intent based on knowledge_hybrid_index.md taxonomy
    
    Intent types:
    - FACT_LOOKUP: Concrete facts, definitions
    - DECISION_RATIONALE: Why something was chosen
    - RELATIONSHIP: How entities connect
    - PROCEDURE: Steps, workflows
    - COMPARISON: Trade-offs
    - TEMPORAL: Evolution over time
    - EXPLANATION: Conceptual understanding
    - ROOT_CAUSE: Failure analysis
    """
    query_lower = query.lower()
    
    # Heuristic intent classification
    if any(word in query_lower for word in ['what is', 'define', 'meaning of', 'definition']):
        return RetrievalIntent(primary="FACT_LOOKUP", secondary=None, confidence=0.8)
    
    elif any(word in query_lower for word in ['why', 'reason', 'rationale', 'chose', 'decided']):
        return RetrievalIntent(primary="DECISION_RATIONALE", secondary=None, confidence=0.75)
    
    elif any(word in query_lower for word in ['how does', 'relate', 'connection', 'relationship', 'between']):
        return RetrievalIntent(primary="RELATIONSHIP", secondary=None, confidence=0.8)
    
    elif any(word in query_lower for word in ['how to', 'steps', 'procedure', 'process', 'workflow']):
        return RetrievalIntent(primary="PROCEDURE", secondary=None, confidence=0.75)
    
    elif any(word in query_lower for word in ['compare', 'versus', 'vs', 'difference', 'better']):
        return RetrievalIntent(primary="COMPARISON", secondary=None, confidence=0.8)
    
    elif any(word in query_lower for word in ['when', 'history', 'evolution', 'over time', 'changed']):
        return RetrievalIntent(primary="TEMPORAL", secondary=None, confidence=0.75)
    
    elif any(word in query_lower for word in ['explain', 'how', 'understand', 'concept']):
        return RetrievalIntent(primary="EXPLANATION", secondary=None, confidence=0.7)
    
    elif any(word in query_lower for word in ['cause', 'why failed', 'problem', 'issue', 'error']):
        return RetrievalIntent(primary="ROOT_CAUSE", secondary=None, confidence=0.75)
    
    else:
        # Default to explanation
        return RetrievalIntent(primary="EXPLANATION", secondary=None, confidence=0.5)


def determine_retrieval_strategy(intent: RetrievalIntent) -> str:
    """
    Determine retrieval strategy based on intent
    Following rules from knowledge_hybrid_index.md
    """
    # Graph-primary intents
    if intent.primary in ["RELATIONSHIP", "DECISION_RATIONALE", "TEMPORAL", "ROOT_CAUSE"]:
        return "GRAPH_PRIMARY"
    
    # Vector-primary intents
    elif intent.primary in ["FACT_LOOKUP", "PROCEDURE", "COMPARISON", "EXPLANATION"]:
        return "VECTOR_PRIMARY"
    
    else:
        return "HYBRID"


def assign_authority(similarity: float, has_graph_context: bool, entity_count: int) -> str:
    """
    Assign authority level based on evidence quality
    
    Authority levels:
    - PRIMARY: High confidence, strong graph connections
    - SECONDARY: Good similarity, some graph context
    - CONTEXTUAL: Moderate similarity, background info
    - HISTORICAL: Low similarity or outdated
    """
    if similarity > 0.8 and has_graph_context and entity_count >= 3:
        return "PRIMARY"
    elif similarity > 0.6 and (has_graph_context or entity_count >= 1):
        return "SECONDARY"
    elif similarity > 0.4:
        return "CONTEXTUAL"
    else:
        return "HISTORICAL"


def get_graph_context(chunk_id: str) -> Optional[GraphEvidence]:
    """Retrieve graph context for a chunk"""
    if not _graph_driver:
        return None
    
    cypher_query = """
    MATCH (c:Chunk {chunk_id: $chunk_id})<-[:MENTIONED_IN]-(e:Entity)
    OPTIONAL MATCH (e)-[r:REL]->(e2:Entity)
    RETURN e.eid as eid, e.name as name, e.type as type,
           r.type as rel_type, e2.eid as target_eid, e2.name as target_name
    LIMIT 20
    """
    
    try:
        with _graph_driver.session() as session:
            result = session.run(cypher_query, chunk_id=chunk_id)
            records = list(result)
            
            if not records:
                return None
            
            # Build nodes and edges
            nodes = {}
            edges = []
            
            for record in records:
                # Add source entity
                eid = record["eid"]
                if eid not in nodes:
                    nodes[eid] = GraphNode(
                        id=eid,
                        label=record["name"],
                        type=record["type"]
                    )
                
                # Add target entity and edge if exists
                if record["target_eid"]:
                    target_eid = record["target_eid"]
                    if target_eid not in nodes:
                        nodes[target_eid] = GraphNode(
                            id=target_eid,
                            label=record["target_name"],
                            type="Entity"
                        )
                    
                    edges.append(GraphEdge(
                        source=eid,
                        relation=record["rel_type"] or "MENTIONED_WITH",
                        target=target_eid
                    ))
            
            # Create traversal path
            path = " → ".join([
                f"{nodes[e.source].label} --{e.relation}--> {nodes[e.target].label}"
                for e in edges[:3]  # First 3 edges
            ])
            
            return GraphEvidence(
                nodes=list(nodes.values()),
                edges=edges,
                traversal_path=path if path else None
            )
    
    except Exception as e:
        print(f"⚠️  Graph query error: {e}")
        return None


@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    initialize_system()


@app.get("/", tags=["Health"])
async def root():
    """API health check"""
    return {
        "status": "operational",
        "service": "Internal Knowledge Navigator API",
        "version": "1.0.0"
    }


@app.get("/health", tags=["Health"])
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "components": {
            "vector_store": _vector_store is not None,
            "graph_db": _graph_driver is not None,
            "embedding_model": _embedding_model is not None
        }
    }


@app.post("/retrieve", response_model=EvidenceResponse, tags=["Retrieval"])
async def retrieve_evidence(request: QueryRequest):
    """
    Retrieve evidence for a query using hybrid RAG approach.
    
    This endpoint:
    1. Classifies query intent
    2. Determines retrieval strategy
    3. Performs vector and/or graph search
    4. Assigns confidence and authority
    5. Returns structured evidence
    
    The response format matches the evidence contract expected by the Custom GPT.
    """
    if not all([_vector_store, _graph_driver, _embedding_model]):
        raise HTTPException(status_code=503, detail="System not initialized")
    
    query = request.query
    
    # Step 1: Classify intent
    intent = classify_intent(query)
    
    # Step 2: Determine strategy
    strategy = determine_retrieval_strategy(intent)
    
    # Step 3: Vector search
    print(f"🔍 Query: {query}")
    print(f"🎯 Intent: {intent.primary} (confidence: {intent.confidence})")
    print(f"⚡ Strategy: {strategy}")
    
    query_vec = _embedding_model.encode([query])[0]
    results = _vector_store.search(query_vec, k=request.max_results)
    
    # Step 4: Build evidence
    vector_evidence = []
    graph_contexts = []
    
    for idx, dist, meta in results:
        if meta is None:
            continue
        
        # Calculate similarity
        similarity = 1.0 / (1.0 + dist)
        
        # Skip very low similarity (adjust threshold based on strategy)
        min_threshold = 0.1 if strategy == "GRAPH_PRIMARY" else 0.2
        if similarity < min_threshold:
            continue
        
        chunk_id = meta.get("chunk_id", "")
        text = meta.get("text", "")
        
        # Get graph context if requested
        graph_ctx = None
        entity_count = 0
        if request.include_graph and chunk_id:
            graph_ctx = get_graph_context(chunk_id)
            if graph_ctx:
                graph_contexts.append(graph_ctx)
                entity_count = len(graph_ctx.nodes)
        
        # Assign authority
        authority = assign_authority(
            similarity=similarity,
            has_graph_context=graph_ctx is not None,
            entity_count=entity_count
        )
        
        vector_evidence.append(VectorEvidence(
            chunk_id=chunk_id,
            text=text,
            similarity=round(similarity, 3),
            authority=authority
        ))
    
    # Calculate overall confidence
    if vector_evidence:
        avg_similarity = sum(ve.similarity for ve in vector_evidence) / len(vector_evidence)
        has_graph = len(graph_contexts) > 0
        
        if avg_similarity > 0.7 and has_graph:
            confidence_level = "HIGH"
            confidence_score = 0.85
        elif avg_similarity > 0.5 or has_graph:
            confidence_level = "MEDIUM"
            confidence_score = 0.65
        else:
            confidence_level = "LOW"
            confidence_score = 0.40
    else:
        confidence_level = "LOW"
        confidence_score = 0.20
    
    # Merge graph contexts (take first one for now)
    merged_graph = graph_contexts[0] if graph_contexts else None
    
    # Create evidence summary
    summary = f"Retrieved {len(vector_evidence)} relevant chunks"
    if merged_graph:
        summary += f" with {len(merged_graph.nodes)} entities and {len(merged_graph.edges)} relationships"
    
    return EvidenceResponse(
        query=query,
        intent=intent,
        vector_evidence=vector_evidence,
        graph_evidence=merged_graph,
        confidence=confidence_level,
        confidence_score=round(confidence_score, 2),
        retrieval_strategy=strategy,
        evidence_summary=summary
    )


@app.post("/retrieve/simple", tags=["Retrieval"])
async def retrieve_simple(
    query: str = Query(..., description="Search query"),
    max_results: int = Query(5, ge=1, le=10)
):
    """
    Simplified retrieval endpoint that returns just text chunks.
    Useful for testing or lightweight integrations.
    """
    request = QueryRequest(query=query, max_results=max_results, include_graph=False)
    response = await retrieve_evidence(request)
    
    return {
        "query": query,
        "results": [
            {
                "text": ve.text,
                "similarity": ve.similarity,
                "authority": ve.authority
            }
            for ve in response.vector_evidence
        ],
        "confidence": response.confidence
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", "8000"))
    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║   Internal Knowledge Navigator API Server               ║
    ║   Custom GPT Integration                                 ║
    ╚══════════════════════════════════════════════════════════╝
    
    🌐 API URL: http://localhost:{port}
    📚 Docs: http://localhost:{port}/docs
    🔍 Health: http://localhost:{port}/health
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=port)
