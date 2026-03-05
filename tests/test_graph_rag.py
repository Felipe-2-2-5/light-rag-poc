#!/usr/bin/env python3
"""
Test script for Graph RAG system

Verifies that all components are properly configured and functional.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_imports():
    """Test that all required modules can be imported"""
    print("\n1. Testing imports...")
    print("-" * 60)
    
    try:
        import faiss
        print("✓ faiss-cpu")
    except ImportError as e:
        print(f"✗ faiss-cpu: {e}")
        return False
    
    try:
        import neo4j
        print("✓ neo4j")
    except ImportError as e:
        print(f"✗ neo4j: {e}")
        return False
    
    try:
        from sentence_transformers import SentenceTransformer
        print("✓ sentence-transformers")
    except ImportError as e:
        print(f"✗ sentence-transformers: {e}")
        return False
    
    try:
        import langchain
        print("✓ langchain")
    except ImportError as e:
        print(f"✗ langchain: {e}")
        return False
    
    try:
        from langchain_openai import ChatOpenAI
        print("✓ langchain-openai")
    except ImportError as e:
        print(f"✗ langchain-openai: {e}")
        return False
    
    try:
        import openai
        print("✓ openai")
    except ImportError as e:
        print(f"✗ openai: {e}")
        return False
    
    return True


def test_environment():
    """Test environment variables"""
    print("\n2. Testing environment...")
    print("-" * 60)
    
    required_vars = ["OPENAI_API_KEY"]
    optional_vars = ["NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"]
    
    all_good = True
    
    for var in required_vars:
        if os.getenv(var):
            print(f"✓ {var} is set")
        else:
            print(f"✗ {var} is NOT set (required)")
            all_good = False
    
    for var in optional_vars:
        if os.getenv(var):
            print(f"✓ {var} is set")
        else:
            print(f"⚠ {var} is NOT set (using default)")
    
    return all_good


def test_data_files():
    """Test that required data files exist"""
    print("\n3. Testing data files...")
    print("-" * 60)
    
    required_files = [
        "outputs/faiss.index",
        "outputs/meta.json",
        "outputs/entities.json",
        "outputs/relations.json"
    ]
    
    all_good = True
    
    for filepath in required_files:
        if Path(filepath).exists():
            size = Path(filepath).stat().st_size
            print(f"✓ {filepath} ({size:,} bytes)")
        else:
            print(f"✗ {filepath} NOT FOUND")
            all_good = False
    
    return all_good


def test_neo4j_connection():
    """Test Neo4j connection"""
    print("\n4. Testing Neo4j connection...")
    print("-" * 60)
    
    try:
        from neo4j import GraphDatabase
        from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
        
        driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            if record["test"] == 1:
                print(f"✓ Connected to Neo4j at {NEO4J_URI}")
                
                # Check if graph has data
                result = session.run("MATCH (e:Entity) RETURN count(e) as count")
                entity_count = result.single()["count"]
                
                result = session.run("MATCH (c:Chunk) RETURN count(c) as count")
                chunk_count = result.single()["count"]
                
                print(f"  - {entity_count:,} entities")
                print(f"  - {chunk_count:,} chunks")
                
                driver.close()
                return True
            else:
                print("✗ Unexpected response from Neo4j")
                driver.close()
                return False
    
    except Exception as e:
        print(f"✗ Failed to connect to Neo4j: {e}")
        return False


def test_vector_store():
    """Test FAISS vector store"""
    print("\n5. Testing vector store...")
    print("-" * 60)
    
    try:
        from vector_store import FaissStore
        
        store = FaissStore(dim=384)  # Default dimension for all-MiniLM-L6-v2
        
        if store.index and store.index.ntotal > 0:
            print(f"✓ FAISS index loaded")
            print(f"  - {store.index.ntotal:,} vectors")
            print(f"  - {len(store.meta):,} metadata entries")
            return True
        else:
            print("✗ FAISS index is empty")
            return False
    
    except Exception as e:
        print(f"✗ Failed to load vector store: {e}")
        return False


def test_embedding_model():
    """Test embedding model"""
    print("\n6. Testing embedding model...")
    print("-" * 60)
    
    try:
        from sentence_transformers import SentenceTransformer
        from config import EMBEDDING_MODEL
        
        print(f"  Loading model: {EMBEDDING_MODEL}")
        model = SentenceTransformer(EMBEDDING_MODEL)
        
        # Test encoding
        test_text = "This is a test sentence."
        embedding = model.encode([test_text])[0]
        
        print(f"✓ Embedding model loaded")
        print(f"  - Dimension: {len(embedding)}")
        print(f"  - Sample vector: [{embedding[0]:.4f}, {embedding[1]:.4f}, ...]")
        
        return True
    
    except Exception as e:
        print(f"✗ Failed to load embedding model: {e}")
        return False


def test_graph_rag():
    """Test GraphRAG initialization"""
    print("\n7. Testing GraphRAG system...")
    print("-" * 60)
    
    try:
        from graph_rag import GraphRAG
        
        print("  Initializing GraphRAG (this may take a moment)...")
        rag = GraphRAG(
            top_k=3,
            similarity_threshold=0.3,
            expand_graph=True
        )
        
        print("✓ GraphRAG initialized successfully")
        
        # Test a simple query
        print("\n  Testing simple query...")
        results = rag.search("test query", top_k=1)
        
        if results:
            print(f"✓ Search working ({len(results)} results)")
        else:
            print("⚠ Search returned no results (may need to adjust threshold)")
        
        rag.close()
        return True
    
    except Exception as e:
        print(f"✗ Failed to initialize GraphRAG: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Graph RAG System - Component Test")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Environment", test_environment()))
    results.append(("Data Files", test_data_files()))
    results.append(("Neo4j Connection", test_neo4j_connection()))
    results.append(("Vector Store", test_vector_store()))
    results.append(("Embedding Model", test_embedding_model()))
    results.append(("GraphRAG System", test_graph_rag()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} - {name}")
    
    print("-" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("  1. Try the CLI: python query_rag.py --interactive")
        print("  2. Open notebook: jupyter notebook graph_rag_demo.ipynb")
        print("  3. Read docs: GRAPH_RAG_README.md")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("  - Install missing packages: pip install -r requirements.txt")
        print("  - Set OPENAI_API_KEY in .env file")
        print("  - Start Neo4j: docker-compose up -d")
        print("  - Run data ingestion: python src/ingest.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
