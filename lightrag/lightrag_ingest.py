#!/usr/bin/env python3
"""
LightRAG Ingestion Script

Ingests documents using the official LightRAG library with proper
entity extraction, graph construction, and multi-level indexing.

Usage:
    python lightrag_ingest.py --input data/LIGHTRAG.pdf
    python lightrag_ingest.py --input data/vn_law_sample.txt --working-dir ./lightrag_storage
"""

import os
import sys
import argparse
import asyncio
import nest_asyncio
from pathlib import Path
from dotenv import load_dotenv

# Enable nested event loops (needed for Jupyter/interactive environments)
nest_asyncio.apply()

# Load environment variables
load_dotenv()

from lightrag import LightRAG, QueryParam
from lightrag.llm.gemini import gemini_model_complete, gemini_embed
from lightrag.utils import wrap_embedding_func_with_attrs
import numpy as np
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')


def setup_llm_functions():
    """Setup LLM and embedding functions based on environment configuration"""
    
    llm_provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if llm_provider == "gemini":
        GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
        if not GEMINI_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY not set in .env file. "
                "Get your key from: https://aistudio.google.com/app/apikey"
            )
        
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        
        async def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
            return await gemini_model_complete(
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                api_key=GEMINI_API_KEY,
                model_name=gemini_model,
                **kwargs,
            )
        
        @wrap_embedding_func_with_attrs(
            embedding_dim=768,
            max_token_size=2048,
        )
        async def embedding_func(texts: list[str]) -> np.ndarray:
            return await gemini_embed.func(
                texts, 
                api_key=GEMINI_API_KEY, 
                model="models/text-embedding-004"
            )
        
        return llm_model_func, embedding_func, gemini_model
    
    elif llm_provider == "openai":
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in .env file")
        
        openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        from lightrag.llm.openai import openai_complete_if_cache, openai_embedding
        
        async def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
            return await openai_complete_if_cache(
                openai_model,
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                api_key=OPENAI_API_KEY,
                **kwargs,
            )
        
        @wrap_embedding_func_with_attrs(
            embedding_dim=1536,
            max_token_size=8192,
        )
        async def embedding_func(texts: list[str]) -> np.ndarray:
            return await openai_embedding(
                texts,
                model="text-embedding-3-small",
                api_key=OPENAI_API_KEY,
            )
        
        return llm_model_func, embedding_func, openai_model
    
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider}. Use 'gemini' or 'openai'")


async def initialize_rag(working_dir: str):
    """Initialize LightRAG with proper configuration"""
    
    print("=" * 80)
    print("LightRAG Initialization")
    print("=" * 80)
    
    llm_model_func, embedding_func, model_name = setup_llm_functions()
    
    print(f"\n✓ LLM Model: {model_name}")
    print(f"✓ Working Directory: {working_dir}")
    
    rag = LightRAG(
        working_dir=working_dir,
        llm_model_func=llm_model_func,
        embedding_func=embedding_func,
        llm_model_name=model_name,
        # Chunking configuration - larger chunks for better context
        chunk_token_size=1200,  # Increased from default 200 tokens
        chunk_overlap_token_size=100,  # Overlap between chunks
    )
    
    # Initialize storage backends
    print("\n⏳ Initializing storage backends...")
    await rag.initialize_storages()
    print("✓ Storage initialized")
    
    return rag


def read_document(filepath: str, use_ade_fallback: bool = True) -> str:
    """
    Read document using optimized unstructured.io parser with ADE fallback
    
    This uses the custom DocumentParser that:
    - Tries free Unstructured.io parser first (high quality)
    - Falls back to ADE API for complex documents
    - Handles PDFs, images, office docs, and text files
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    # Add src to path to import DocumentParser (go up to project root, then into src)
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    
    try:
        from document_parser import DocumentParser
        
        # Get ADE API key from environment (optional)
        ade_api_key = os.getenv("ADE_API_KEY")
        
        # Initialize parser with ADE fallback if key is available
        parser = DocumentParser(
            ade_api_key=ade_api_key,
            use_ade_fallback=use_ade_fallback and ade_api_key is not None
        )
        
        print(f"\n📄 Parsing document with optimized parser...")
        text, metadata = parser.parse_document(str(filepath))
        
        # Print parsing info
        if metadata:
            parser_name = metadata.get('parser', 'unknown')
            print(f"✓ Parsed with: {parser_name}")
            if 'num_elements' in metadata:
                print(f"  Elements extracted: {metadata['num_elements']}")
            if 'has_tables' in metadata:
                print(f"  Contains tables: {metadata['has_tables']}")
        
        print(f"✓ Extracted {len(text):,} characters")
        
        return text
        
    except ImportError as e:
        print(f"\n⚠️  DocumentParser not available: {e}")
        print("Falling back to simple text extraction...")
        
        # Simple fallback for text files
        if filepath.suffix.lower() in ['.txt', '.md', '.rst']:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            raise ValueError(
                f"Cannot parse {filepath.suffix} files without DocumentParser. "
                "Install dependencies: pip install 'unstructured[pdf]' pillow"
            )


async def ingest_document(rag: LightRAG, filepath: str, use_ade_fallback: bool = True):
    """Ingest a document into LightRAG using optimized parser"""
    
    print("\n" + "=" * 80)
    print("Document Ingestion with Optimized Parser")
    print("=" * 80)
    
    print(f"\nInput: {filepath}")
    
    # Parse document with optimized parser (Unstructured.io + ADE fallback)
    text = read_document(filepath, use_ade_fallback=use_ade_fallback)
    
    print(f"\n📊 Document Statistics:")
    print(f"  Total characters: {len(text):,}")
    print(f"  Total words: {len(text.split()):,}")
    print(f"  Preview: {text[:200]}...")
    
    print("\n⏳ LightRAG Processing...")
    print("  - Chunking document")
    print("  - Extracting entities and relationships with LLM")
    print("  - Building knowledge graph")
    print("  - Creating vector embeddings")
    print("  - Building multi-level indexes (local + global)")
    
    # Insert document (LightRAG handles entity extraction and graph construction)
    await rag.ainsert(text)
    
    print("\n✓ Document ingestion complete!")
    print("  Knowledge graph built with entities, relationships, and embeddings")
    
    return len(text)


def print_statistics(working_dir: str):
    """Print storage statistics"""
    
    print("\n" + "=" * 80)
    print("Storage Statistics")
    print("=" * 80)
    
    working_path = Path(working_dir)
    
    if not working_path.exists():
        print("No storage data found.")
        return
    
    stats = {}
    
    # Check for storage files
    for file in working_path.glob("**/*"):
        if file.is_file():
            size = file.stat().st_size
            stats[file.name] = size
    
    if stats:
        total_size = sum(stats.values())
        print(f"\nTotal storage size: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
        print("\nFiles:")
        for name, size in sorted(stats.items()):
            print(f"  - {name}: {size:,} bytes")
    else:
        print("\nNo files found in storage directory")


def save_to_neo4j(working_dir: str) -> bool:
    """
    Save LightRAG data to Neo4j database for searching
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Import the database storage module (go up to project root, then into src)
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from lightrag_db_storage import save_lightrag_to_database
        
        # Get Neo4j credentials from environment
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "test")
        
        print("\n" + "=" * 80)
        print("Saving to Neo4j Database")
        print("=" * 80)
        print(f"\n⏳ Connecting to Neo4j at {neo4j_uri}...")
        
        # Save to Neo4j with clear_existing=True for fresh data
        save_lightrag_to_database(
            working_dir=working_dir,
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
            clear_existing=True
        )
        
        return True
        
    except ImportError as e:
        print(f"\n⚠️  Database storage module not available: {e}")
        print("Skipping Neo4j storage (data is still saved to files)")
        return False
    except Exception as e:
        print(f"\n⚠️  Failed to save to Neo4j: {e}")
        print("Data is still available in storage files")
        return False


async def main():
    """Main ingestion pipeline"""
    
    parser = argparse.ArgumentParser(
        description="Ingest documents into LightRAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Input document file (PDF, TXT, MD)"
    )
    
    parser.add_argument(
        "--working-dir",
        "-w",
        default="./lightrag_storage",
        help="Working directory for LightRAG storage (default: ./lightrag_storage)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-ingestion even if storage exists"
    )
    
    parser.add_argument(
        "--no-ade-fallback",
        action="store_true",
        help="Disable ADE API fallback (use only free parsers)"
    )
    
    parser.add_argument(
        "--save-to-neo4j",
        action="store_true",
        default=True,
        help="Save ingestion output to Neo4j database (default: True)"
    )
    
    parser.add_argument(
        "--skip-neo4j",
        action="store_true",
        help="Skip saving to Neo4j database"
    )
    
    args = parser.parse_args()
    
    # Create working directory
    working_dir = Path(args.working_dir)
    
    if working_dir.exists() and not args.force:
        print(f"\n⚠️  Storage directory already exists: {working_dir}")
        print("Use --force to re-ingest (will overwrite existing data)")
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            return 1
    
    working_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Initialize LightRAG
        rag = await initialize_rag(str(working_dir))
        
        # Ingest document with optimized parser
        use_ade = not args.no_ade_fallback
        char_count = await ingest_document(rag, args.input, use_ade_fallback=use_ade)
        
        # Print statistics
        print_statistics(str(working_dir))
        
        # Save to Neo4j database if enabled
        neo4j_saved = False
        if not args.skip_neo4j:
            neo4j_saved = save_to_neo4j(str(working_dir))
        
        print("\n" + "=" * 80)
        print("Next Steps")
        print("=" * 80)
        print("\n1. Query the system:")
        print(f"   python lightrag_query.py \"Your question here\"")
        print("\n2. Interactive mode:")
        print(f"   python lightrag_query.py --interactive")
        print("\n3. Test different modes:")
        print(f"   python lightrag_query.py \"Your question\" --mode hybrid")
        
        if neo4j_saved:
            print("\n4. Search Neo4j graph database:")
            print(f"   Open Neo4j Browser at http://localhost:7474")
            print(f"   Query: MATCH (e:LightRAGEntity) RETURN e LIMIT 25")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
