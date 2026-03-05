#!/usr/bin/env python3
"""
Debug embedding similarity for Vietnamese query
"""

import os
import json
import asyncio
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from lightrag.llm.gemini import gemini_embed
from lightrag.utils import wrap_embedding_func_with_attrs


@wrap_embedding_func_with_attrs(
    embedding_dim=768,
    max_token_size=2048,
)
async def embedding_func(texts: list[str]) -> np.ndarray:
    GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
    gemini_embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")
    return await gemini_embed.func(
        texts, 
        api_key=GEMINI_API_KEY, 
        model=gemini_embedding_model,
        embedding_dim=768
    )


def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


async def main():
    # Load the vector database
    print("Loading entity vectors...")
    with open('lightrag_storage/vdb_entities.json', 'r') as f:
        vdb_entities = json.load(f)
    
    print(f"Total entities: {len(vdb_entities['data'])}")
    print(f"Embedding dimension: {vdb_entities['embedding_dim']}")
    
    # Get embeddings for our query
    query = "điều 5"
    print(f"\nQuery: '{query}'")
    print("Getting query embedding...")
    
    query_embedding = await embedding_func([query])
    query_vec = query_embedding[0]
    
    print(f"Query embedding shape: {query_vec.shape}")
    
    # Check similarity with known entities
    print("\n" + "="*80)
    print("Similarity scores with stored entities:")
    print("="*80)
    
    # Calculate similarities
    similarities = []
    for entity in vdb_entities['data'][:50]:  # Check first 50
        entity_name = entity['entity_name']
        
        # Decode the compressed vector
        import base64
        import struct
        import zlib
        vec_b64 = entity['vector']
        vec_compressed = base64.b64decode(vec_b64)
        vec_bytes = zlib.decompress(vec_compressed)
        entity_vec = np.array(struct.unpack(f'{len(vec_bytes)//4}f', vec_bytes))
        
        similarity = cosine_similarity(query_vec, entity_vec)
        similarities.append((entity_name, similarity))
    
    # Sort by similarity
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    # Show top 20
    print("\nTop 20 most similar entities:")
    for i, (name, score) in enumerate(similarities[:20], 1):
        print(f"{i:2d}. {name:50s} | Similarity: {score:.4f}")
    
    print("\n" + "="*80)
    print(f"Threshold in LightRAG: 0.2")
    print(f"Entities above threshold: {sum(1 for _, s in similarities if s >= 0.2)}")
    
    # Also check chunks
    print("\n" + "="*80)
    print("Checking similarity with text chunks:")
    print("="*80)
    
    with open('lightrag_storage/vdb_chunks.json', 'r') as f:
        vdb_chunks = json.load(f)
    
    chunk_similarities = []
    for chunk in vdb_chunks['data']:
        chunk_id = chunk['__id__']
        content_preview = chunk['content'][:100].replace('\n', ' ')
        
        import zlib
        vec_b64 = chunk['vector']
        vec_compressed = base64.b64decode(vec_b64)
        vec_bytes = zlib.decompress(vec_compressed)
        chunk_vec = np.array(struct.unpack(f'{len(vec_bytes)//4}f', vec_bytes))
        
        similarity = cosine_similarity(query_vec, chunk_vec)
        chunk_similarities.append((chunk_id, content_preview, similarity))
    
    chunk_similarities.sort(key=lambda x: x[2], reverse=True)
    
    print("\nTop 10 most similar chunks:")
    for i, (chunk_id, preview, score) in enumerate(chunk_similarities[:10], 1):
        print(f"{i:2d}. Similarity: {score:.4f}")
        print(f"    {preview}...")
        print()
    
    print(f"Chunks above threshold (0.2): {sum(1 for _, _, s in chunk_similarities if s >= 0.2)}")


if __name__ == "__main__":
    asyncio.run(main())
