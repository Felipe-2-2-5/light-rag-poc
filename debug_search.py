#!/usr/bin/env python3
"""Debug script to check vector search"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sentence_transformers import SentenceTransformer
from vector_store import FaissStore
from dotenv import load_dotenv
import os

load_dotenv()

# Load models
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
print(f"Loading embedding model: {EMBEDDING_MODEL}")
model = SentenceTransformer(EMBEDDING_MODEL)
dim = model.get_sentence_embedding_dimension()
print(f"Embedding dimension: {dim}")

# Load vector store
print(f"\nLoading vector store...")
store = FaissStore(dim=dim)
print(f"Index contains {store.index.ntotal} vectors")
print(f"Metadata contains {len(store.meta)} entries")

# Test queries
queries = [
    "How does it work?",
    "What is LightRAG?",
    "graph retrieval",
    "knowledge graph",
]

for query in queries:
    print(f"\n{'='*80}")
    print(f"Query: '{query}'")
    print(f"{'='*80}")
    
    # Embed
    query_vec = model.encode([query])[0]
    
    # Search
    results = store.search(query_vec, k=5)
    
    print(f"\nTop 5 results:")
    for i, (idx, dist, meta) in enumerate(results, 1):
        similarity = 1.0 / (1.0 + dist)
        chunk_id = meta.get("chunk_id", "N/A") if meta else "N/A"
        text_preview = meta.get("text", "")[:100] if meta else ""
        
        print(f"\n{i}. Chunk: {chunk_id}")
        print(f"   Distance: {dist:.4f}, Similarity: {similarity:.4f}")
        print(f"   Text: {text_preview}...")
