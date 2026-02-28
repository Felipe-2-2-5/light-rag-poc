"""
Graph-based RAG (Retrieval Augmented Generation) System

This module implements a hybrid RAG approach that combines:
1. Vector similarity search (FAISS)
2. Knowledge graph traversal (Neo4j)
3. LLM generation (via LangChain)

Inspired by the ADE RAG pipeline pattern from L11.ipynb
"""

import os
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer



# LangChain imports
try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.documents import Document
    from langchain_core.callbacks import CallbackManagerForRetrieverRun
    from langchain_core.runnables import RunnablePassthrough, RunnableParallel
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    print(f"Warning: LangChain dependencies not installed. Install with: pip install langchain langchain-openai langchain-google-genai")
    print(f"Error details: {e}")
    BaseRetriever = object
    CallbackManagerForRetrieverRun = object
    Document = dict
    ChatPromptTemplate = object
    ChatOpenAI = object
    ChatGoogleGenerativeAI = object
    RunnablePassthrough = object
    RunnableParallel = object
    StrOutputParser = object
    LANGCHAIN_AVAILABLE = False

from dotenv import load_dotenv

# Load environment variables from .env file BEFORE importing config
load_dotenv()

from vector_store import FaissStore
from confidence_scorer import ConfidenceScorer
from config import (
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, EMBEDDING_MODEL,
    LLM_PROVIDER, OPENAI_MODEL, GEMINI_MODEL, GOOGLE_API_KEY
)

@dataclass
class SearchResult:
    """Container for search results with metadata"""
    text: str
    chunk_id: str
    similarity: float
    entities: List[Dict[str, Any]]
    relations: List[Tuple[str, str, str]]
    metadata: Dict[str, Any]
    confidence: float = 0.0  # Overall confidence score (0-1)
    confidence_factors: Dict[str, float] = None  # Breakdown of confidence components
    
    def __post_init__(self):
        if self.confidence_factors is None:
            self.confidence_factors = {}


class GraphRAGRetriever(BaseRetriever):
    """
    Custom LangChain retriever that combines vector search with graph traversal.
    
    This retriever:
    1. Performs vector similarity search to find relevant chunks
    2. Queries the knowledge graph to find entities in those chunks
    3. Expands context by traversing graph relationships
    4. Returns enriched documents with graph context
    """
    
    vector_store: Any
    graph_driver: Any
    embedding_model: Any
    top_k: int = 5
    similarity_threshold: float = 0.3
    expand_graph: bool = True
    confidence_scorer: Any = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def _get_relevant_documents(
        self, query: str, *, run_manager: Optional[CallbackManagerForRetrieverRun] = None
    ) -> List[Document]:
        """Retrieve documents relevant to the query using hybrid search"""
        
        # 1. Embed query
        query_vec = self.embedding_model.encode([query])[0]
        
        # 2. Vector similarity search
        results = self.vector_store.search(query_vec, k=self.top_k)
        
        documents = []
        for idx, dist, meta in results:
            if meta is None:
                continue
                
            # Calculate similarity (1 - normalized distance)
            similarity = 1.0 / (1.0 + dist)
            
            if similarity < self.similarity_threshold:
                continue
            
            chunk_id = meta.get("chunk_id", "")
            text = meta.get("text", "")
            
            # 3. Graph expansion: Find entities and relationships
            graph_context = ""
            if self.expand_graph and chunk_id:
                graph_context = self._get_graph_context(chunk_id)
            
            # Combine text with graph context
            enriched_text = text
            if graph_context:
                enriched_text = f"{text}\n\n[Graph Context]\n{graph_context}"
            
            # Get entity/relation count for confidence calculation
            entity_count = 0
            relation_count = 0
            if chunk_id and graph_context:
                entity_count, relation_count = self._get_entity_relation_counts(chunk_id)
            
            # Calculate confidence score using advanced scorer
            if self.confidence_scorer:
                conf_score = self.confidence_scorer.calculate_confidence(
                    query=query,
                    text=text,
                    similarity_score=similarity,
                    has_entities=entity_count > 0,
                    num_entities=entity_count,
                    has_relations=relation_count > 0,
                    num_relations=relation_count
                )
                confidence = conf_score.overall
                factors = conf_score.to_dict()
            else:
                # Fallback to simple calculation
                confidence, factors = self._calculate_confidence(
                    similarity=similarity,
                    text=text,
                    query=query,
                    has_graph_context=bool(graph_context)
                )
            
            # Create LangChain Document
            doc = Document(
                page_content=enriched_text,
                metadata={
                    "chunk_id": chunk_id,
                    "similarity": similarity,
                    "original_text": text,
                    "has_graph_context": bool(graph_context),
                    "confidence": confidence,
                    "confidence_factors": factors
                }
            )
            documents.append(doc)
        
        return documents
    
    def _calculate_confidence(
        self,
        similarity: float,
        text: str,
        query: str,
        has_graph_context: bool
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate overall confidence score based on multiple factors.
        
        Factors considered:
        1. Similarity score (0-1): Vector similarity between query and chunk
        2. Graph connectivity (0-1): Whether chunk has graph context
        3. Text length factor (0-1): Prefer chunks with substantial content
        4. Query term coverage (0-1): How many query terms appear in text
        
        Returns:
            Tuple of (overall_confidence, factor_breakdown)
        """
        factors = {}
        
        # Factor 1: Similarity score (40% weight)
        factors['similarity'] = similarity
        
        # Factor 2: Graph connectivity (20% weight)
        factors['graph_connectivity'] = 1.0 if has_graph_context else 0.3
        
        # Factor 3: Text length factor (15% weight)
        # Prefer chunks between 100-500 characters
        text_len = len(text)
        if text_len < 50:
            factors['text_length'] = 0.5
        elif text_len < 100:
            factors['text_length'] = 0.7
        elif text_len <= 500:
            factors['text_length'] = 1.0
        else:
            factors['text_length'] = 0.9
        
        # Factor 4: Query term coverage (25% weight)
        query_terms = set(query.lower().split())
        text_lower = text.lower()
        matching_terms = sum(1 for term in query_terms if term in text_lower)
        factors['query_coverage'] = matching_terms / len(query_terms) if query_terms else 0.0
        
        # Calculate weighted confidence
        weights = {
            'similarity': 0.40,
            'graph_connectivity': 0.20,
            'text_length': 0.15,
            'query_coverage': 0.25
        }
        
        overall_confidence = sum(
            factors[key] * weights[key] for key in weights.keys()
        )
        
        # Store individual factors for transparency
        confidence_breakdown = {
            **factors,
            'weights': weights,
            'overall': overall_confidence
        }
        
        return overall_confidence, confidence_breakdown
    
    def _get_entity_relation_counts(self, chunk_id: str) -> Tuple[int, int]:
        """Get count of entities and relations for a chunk"""
        cypher_query = """
        MATCH (c:Chunk {chunk_id: $chunk_id})<-[:MENTIONED_IN]-(e:Entity)
        OPTIONAL MATCH (e)-[r:REL]->(e2:Entity)
        RETURN count(DISTINCT e) as entity_count, count(DISTINCT r) as relation_count
        """
        
        try:
            with self.graph_driver.session() as session:
                result = session.run(cypher_query, chunk_id=chunk_id)
                record = result.single()
                if record:
                    return record["entity_count"], record["relation_count"]
        except Exception:
            pass
        return 0, 0
    
    def _get_graph_context(self, chunk_id: str) -> str:
        """Query Neo4j for entities and relationships related to a chunk"""
        
        cypher_query = """
        // Find entities mentioned in this chunk
        MATCH (c:Chunk {chunk_id: $chunk_id})<-[:MENTIONED_IN]-(e:Entity)
        
        // Get relationships between these entities
        OPTIONAL MATCH (e)-[r:REL]->(e2:Entity)
        WHERE (e2)-[:MENTIONED_IN]->(:Chunk)
        
        RETURN 
            collect(DISTINCT {name: e.name, type: e.type}) as entities,
            collect(DISTINCT {from: e.name, rel: r.type, to: e2.name}) as relations
        LIMIT 1
        """
        
        try:
            with self.graph_driver.session() as session:
                result = session.run(cypher_query, chunk_id=chunk_id)
                record = result.single()
                
                if not record:
                    return ""
                
                entities = record["entities"]
                relations = record["relations"]
                
                # Format graph context
                context_parts = []
                
                if entities:
                    entity_names = [e["name"] for e in entities if e.get("name")]
                    if entity_names:
                        context_parts.append(f"Entities: {', '.join(entity_names[:10])}")
                
                if relations:
                    rel_strs = [
                        f"{r['from']} -{r['rel']}-> {r['to']}" 
                        for r in relations 
                        if r.get("from") and r.get("to") and r.get("rel")
                    ]
                    if rel_strs:
                        context_parts.append(f"Relations: {'; '.join(rel_strs[:5])}")
                
                return "\n".join(context_parts)
                
        except Exception as e:
            print(f"Error querying graph: {e}")
            return ""


class GraphRAG:
    """
    Main Graph RAG system combining vector search, knowledge graph, and LLM generation.
    
    Usage:
        rag = GraphRAG()
        answer = rag.query("What is LightRAG?")
        print(answer)
    """
    
    def __init__(
        self,
        embedding_model: str = EMBEDDING_MODEL,
        llm_provider: str = None,
        llm_model: str = None,
        temperature: float = 0,
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        expand_graph: bool = True
    ):
        """
        Initialize the Graph RAG system.
        
        Args:
            embedding_model: HuggingFace model for embeddings
            llm_provider: LLM provider ("openai" or "gemini"), defaults to LLM_PROVIDER env var
            llm_model: Model name, defaults to provider's default model
            temperature: LLM temperature (0 = deterministic)
            top_k: Number of chunks to retrieve
            similarity_threshold: Minimum similarity score
            expand_graph: Whether to include graph context
        """
        # Load embedding model
        print(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        
        # Load vector store
        print(f"Loading vector store from outputs/")
        self.vector_store = FaissStore(dim=self.embedding_dim)
        
        # Connect to Neo4j
        print(f"Connecting to Neo4j at {NEO4J_URI}")
        self.graph_driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        
        # Initialize LLM based on provider
        llm_provider = llm_provider or LLM_PROVIDER
        print(f"Initializing LLM provider: {llm_provider}")
        
        if llm_provider.lower() == "gemini":
            llm_model = llm_model or GEMINI_MODEL
            if not GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY not set in .env file. Get your key from: https://aistudio.google.com/app/apikey")
            print(f"Using Google Gemini model: {llm_model}")
            self.llm = ChatGoogleGenerativeAI(
                model=llm_model,
                temperature=temperature,
                google_api_key=GOOGLE_API_KEY
            )
        elif llm_provider.lower() == "openai":
            llm_model = llm_model or OPENAI_MODEL
            print(f"Using OpenAI model: {llm_model}")
            self.llm = ChatOpenAI(model=llm_model, temperature=temperature)
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}. Use 'openai' or 'gemini'")
        
        # Initialize confidence scorer
        self.confidence_scorer = ConfidenceScorer()
        
        # Create custom retriever
        self.retriever = GraphRAGRetriever(
            vector_store=self.vector_store,
            graph_driver=self.graph_driver,
            embedding_model=self.embedding_model,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            expand_graph=expand_graph,
            confidence_scorer=self.confidence_scorer
        )
        
        # Create RAG chain
        self.rag_chain = self._create_rag_chain()
        
        print("✓ Graph RAG system initialized")
    
    def _create_rag_chain(self):
        """Create the LangChain RAG pipeline using LCEL"""
        
        system_prompt = (
            "You are a helpful AI assistant that answers questions based on the provided context.\n"
            "Use the retrieved context to answer the user's question accurately.\n"
            "If the context includes graph information (entities and relationships), use it to provide more comprehensive answers.\n"
            "If you don't know the answer based on the context, say so clearly.\n"
            "\n"
            "Context:\n{context}"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])
        
        # Helper function to format retrieved documents
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)
        
        # Create retrieval chain using LCEL
        chain = (
            RunnableParallel(
                {"context": self.retriever | format_docs, "input": RunnablePassthrough()}
            )
            | prompt
            | self.llm
            | StrOutputParser()
        )
        return chain
    
    def query(self, question: str, verbose: bool = False) -> str:
        """
        Query the Graph RAG system with a natural language question.
        
        Args:
            question: User question
            verbose: If True, print detailed retrieval information
            
        Returns:
            Generated answer grounded in retrieved context
        """
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"Query: {question}")
            print(f"{'='*80}\n")
        
        # Get retrieved documents for verbose output
        if verbose:
            docs = self.retriever.invoke(question)
            print("\nRetrieved Context:")
            print("-" * 80)
            for i, doc in enumerate(docs, 1):
                confidence = doc.metadata.get('confidence', 0)
                similarity = doc.metadata.get('similarity', 0)
                print(f"\nChunk {i}:")
                print(f"  Confidence: {confidence:.3f} ⭐" + (" HIGH" if confidence >= 0.7 else " MEDIUM" if confidence >= 0.5 else " LOW"))
                print(f"  Similarity: {similarity:.3f}")
                print(f"  ID: {doc.metadata.get('chunk_id', 'N/A')}")
                
                # Show confidence breakdown
                factors = doc.metadata.get('confidence_factors', {})
                if factors and 'overall' in factors:
                    print(f"  Confidence factors:")
                    print(f"    - Similarity: {factors.get('similarity', 0):.2f}")
                    print(f"    - Graph connectivity: {factors.get('graph_connectivity', 0):.2f}")
                    print(f"    - Text length: {factors.get('text_length', 0):.2f}")
                    print(f"    - Query coverage: {factors.get('query_coverage', 0):.2f}")
                
                print(f"  Text preview: {doc.page_content[:200]}...")
                if doc.metadata.get("has_graph_context"):
                    print("  ✓ Includes graph context")
            
            print("\n" + "="*80)
            print("Generated Answer:")
            print("="*80)
        
        # Invoke the RAG chain
        response = self.rag_chain.invoke(question)
        
        return response
    
    def search(
        self, 
        question: str, 
        top_k: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Perform hybrid search without generation (retrieval only).
        
        Args:
            question: Search query
            top_k: Override default top_k
            threshold: Override default similarity threshold
            
        Returns:
            List of SearchResult objects with enriched metadata
        """
        
        # Embed query
        query_vec = self.embedding_model.encode([question])[0]
        
        # Vector search
        k = top_k if top_k is not None else self.retriever.top_k
        results = self.vector_store.search(query_vec, k=k)
        
        threshold = threshold if threshold is not None else self.retriever.similarity_threshold
        
        search_results = []
        for idx, dist, meta in results:
            if meta is None:
                continue
            
            similarity = 1.0 / (1.0 + dist)
            if similarity < threshold:
                continue
            
            chunk_id = meta.get("chunk_id", "")
            text = meta.get("text", "")
            
            # Get graph information
            entities, relations = self._get_graph_info(chunk_id)
            
            # Calculate confidence score
            has_graph = bool(entities or relations)
            confidence, factors = self.retriever._calculate_confidence(
                similarity=similarity,
                text=text,
                query=question,
                has_graph_context=has_graph
            )
            
            result = SearchResult(
                text=text,
                chunk_id=chunk_id,
                similarity=similarity,
                entities=entities,
                relations=relations,
                metadata=meta,
                confidence=confidence,
                confidence_factors=factors
            )
            search_results.append(result)
        
        return search_results
    
    def _get_graph_info(self, chunk_id: str) -> Tuple[List[Dict], List[Tuple]]:
        """Get detailed graph information for a chunk"""
        
        cypher_query = """
        MATCH (c:Chunk {chunk_id: $chunk_id})<-[:MENTIONED_IN]-(e:Entity)
        OPTIONAL MATCH (e)-[r:REL]->(e2:Entity)
        RETURN 
            collect(DISTINCT {name: e.name, type: e.type, eid: e.eid}) as entities,
            collect(DISTINCT [e.eid, r.type, e2.eid]) as relations
        """
        
        try:
            with self.graph_driver.session() as session:
                result = session.run(cypher_query, chunk_id=chunk_id)
                record = result.single()
                
                if not record:
                    return [], []
                
                entities = [e for e in record["entities"] if e.get("name")]
                relations = [tuple(r) for r in record["relations"] if r[0] and r[1] and r[2]]
                
                return entities, relations
                
        except Exception as e:
            print(f"Error querying graph: {e}")
            return [], []
    
    def get_entity_context(self, entity_name: str, max_hops: int = 2) -> Dict[str, Any]:
        """
        Get the subgraph context around a specific entity.
        
        Args:
            entity_name: Name of the entity to explore
            max_hops: Maximum relationship hops from the entity
            
        Returns:
            Dictionary with entity info, neighbors, and relationships
        """
        
        cypher_query = """
        MATCH (e:Entity)
        WHERE toLower(e.name) CONTAINS toLower($entity_name)
        
        // Get neighbors within max_hops
        CALL {
            WITH e
            MATCH path = (e)-[r:REL*1..%d]-(neighbor:Entity)
            RETURN neighbor, relationships(path) as rels
            LIMIT 50
        }
        
        RETURN 
            e.name as entity_name,
            e.type as entity_type,
            collect(DISTINCT {
                name: neighbor.name, 
                type: neighbor.type,
                relationship: [rel in rels | rel.type][0]
            }) as neighbors
        LIMIT 1
        """ % max_hops
        
        try:
            with self.graph_driver.session() as session:
                result = session.run(cypher_query, entity_name=entity_name)
                record = result.single()
                
                if not record:
                    return {"error": f"Entity '{entity_name}' not found"}
                
                return {
                    "entity": record["entity_name"],
                    "type": record["entity_type"],
                    "neighbors": record["neighbors"][:20]  # Limit for display
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    def close(self):
        """Clean up resources"""
        if hasattr(self, 'graph_driver'):
            self.graph_driver.close()
        print("✓ Graph RAG system closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """Demo usage of the Graph RAG system"""
    
    print("\n" + "="*80)
    print("Graph RAG System Demo")
    print("="*80 + "\n")
    
    # Initialize system
    rag = GraphRAG(
        top_k=5,
        similarity_threshold=0.3,
        expand_graph=True
    )
    
    # Example queries
    questions = [
        "What is LightRAG?",
        "How does the knowledge graph improve retrieval?",
        "What are the main components of the system?"
    ]
    
    for question in questions:
        print(f"\nQ: {question}")
        print("-" * 80)
        answer = rag.query(question, verbose=False)
        print(f"A: {answer}\n")
    
    # Demonstrate search without generation
    print("\n" + "="*80)
    print("Hybrid Search Demo (Retrieval Only)")
    print("="*80 + "\n")
    
    search_results = rag.search("knowledge graph architecture", top_k=3)
    for i, result in enumerate(search_results, 1):
        print(f"\nResult {i}:")
        print(f"  Confidence: {result.confidence:.3f} {'⭐' * int(result.confidence * 5)}")
        print(f"  Similarity: {result.similarity:.3f}")
        print(f"  Chunk ID: {result.chunk_id}")
        print(f"  Text: {result.text[:150]}...")
        print(f"  Entities: {[e['name'] for e in result.entities[:5]]}")
        if result.confidence_factors:
            print(f"  Confidence breakdown:")
            print(f"    Overall: {result.confidence_factors.get('overall', 0):.3f}")
            print(f"    Factors: sim={result.confidence_factors.get('similarity', 0):.2f}, "
                  f"graph={result.confidence_factors.get('graph_connectivity', 0):.2f}, "
                  f"coverage={result.confidence_factors.get('query_coverage', 0):.2f}")
    
    rag.close()


if __name__ == "__main__":
    main()
