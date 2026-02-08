#!/usr/bin/env python3
"""
LightRAG Query Script

Query documents using the official LightRAG library with multiple search modes:
- naive: Simple vector search
- local: Entity-focused local search
- global: Community-based global search  
- hybrid: Combined local + global search

Usage:
    python lightrag_query.py "What is LightRAG?"
    python lightrag_query.py "How does it work?" --mode hybrid
    python lightrag_query.py --interactive
"""

import os
import sys
import argparse
import asyncio
import nest_asyncio
from pathlib import Path
from dotenv import load_dotenv

# Enable nested event loops
nest_asyncio.apply()

# Load environment variables
load_dotenv()

from lightrag import LightRAG, QueryParam
from lightrag.llm.gemini import gemini_model_complete, gemini_embed
from lightrag.utils import wrap_embedding_func_with_attrs
import numpy as np


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
        gemini_embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "models/embedding-001")
        
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
            # Use .func to bypass gemini_embed's decorator (which has embedding_dim=1536)
            # and apply our own wrapper with embedding_dim=768
            return await gemini_embed.func(
                texts, 
                api_key=GEMINI_API_KEY, 
                model=gemini_embedding_model,
                embedding_dim=768  # Explicitly set to 768 for compatibility
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
    
    print("⏳ Initializing LightRAG system...")
    
    llm_model_func, embedding_func, model_name = setup_llm_functions()
    
    rag = LightRAG(
        working_dir=working_dir,
        llm_model_func=llm_model_func,
        embedding_func=embedding_func,
        llm_model_name=model_name,
    )
    
    await rag.initialize_storages()
    
    print(f"✓ LightRAG initialized (Model: {model_name})")
    
    return rag


def print_separator(char="=", length=80):
    """Print a separator line"""
    print(char * length)


def enhance_references_with_pages(answer: str, working_dir: str) -> str:
    """
    Post-process the answer to add page numbers to references.
    
    Tries to identify which specific chunks were used by matching content,
    then shows the relevant page numbers.
    
    Example:
        Input:  "[1] data/MA-RAG Multi-Agent.pdf"
        Output: "[1] data/MA-RAG Multi-Agent.pdf (pages 1, 3, 5-7)"
    """
    import json
    import re
    from pathlib import Path
    from collections import defaultdict
    
    # Load chunk metadata
    chunks_file = Path(working_dir) / "kv_store_text_chunks.json"
    if not chunks_file.exists():
        return answer
    
    try:
        with open(chunks_file, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        
        # Build a mapping of file_path to pages, with relevance scoring
        # Try to identify which chunks were likely used by matching snippets
        path_to_pages = defaultdict(set)
        
        # Extract some distinctive phrases from the answer (excluding references section)
        answer_body = answer.split('### References')[0] if '### References' in answer else answer
        answer_snippets = set()
        
        # Extract meaningful phrases (10-50 chars) from answer
        words = answer_body.split()
        for i in range(len(words) - 3):
            phrase = ' '.join(words[i:i+4])
            if len(phrase) >= 15 and len(phrase) <= 60:
                answer_snippets.add(phrase.lower())
        
        # Match chunks to answer content
        relevant_chunks = {}
        for chunk_id, chunk_data in chunks.items():
            content = chunk_data.get('content', '').lower()
            file_path = chunk_data.get('file_path', '')
            page = chunk_data.get('page')
            
            if not file_path or not page:
                continue
            
            # Check if this chunk's content appears in the answer
            relevance_score = 0
            for snippet in answer_snippets:
                if snippet in content:
                    relevance_score += 1
            
            if relevance_score > 0:
                relevant_chunks[chunk_id] = {
                    'file_path': file_path,
                    'page': page,
                    'relevance': relevance_score
                }
                path_to_pages[file_path].add(page)
        
        # Find references in the answer
        # Pattern 1: "[1] data/Document.pdf" (full path)
        # Pattern 2: "[1] Document Name" (just name, can be long)
        reference_pattern1 = r'(\[\d+\])\s+(data/[^\n\r]+?\.(?:pdf|md))'
        reference_pattern2 = r'(\[\d+\])\s+([A-Z][^\[\]\n\r]{15,}?)(?=\n|$)'
        
        def enhance_reference(match):
            ref_num = match.group(1)  # e.g., "[1]"
            file_ref = match.group(2).strip()  # e.g., "data/Document.pdf" or "Document Name"
            
            # Try to find matching file_path
            matched_path = None
            pages = []
            
            if file_ref.startswith('data/'):
                # Direct path match
                matched_path = file_ref
                pages = sorted(path_to_pages.get(file_ref, []))
            else:
                # Name-based matching - find file containing this name
                file_ref_clean = file_ref.replace('.pdf', '').replace('.md', '').lower()
                for path in path_to_pages.keys():
                    path_name = Path(path).stem.lower()
                    if file_ref_clean in path_name or path_name in file_ref_clean:
                        matched_path = path
                        pages = sorted(path_to_pages.get(path, []))
                        break
            
            # If still no pages found, try fallback
            if not pages and matched_path:
                all_pages = set()
                for chunk_data in chunks.values():
                    chunk_path = chunk_data.get('file_path', '')
                    if matched_path in chunk_path or chunk_path in matched_path:
                        if chunk_data.get('page'):
                            all_pages.add(chunk_data.get('page'))
                pages = sorted(all_pages)
            
            # Format the reference with pages
            if matched_path and pages:
                doc_name = Path(matched_path).name
                if len(pages) == 1:
                    return f"{ref_num} {doc_name} (page {pages[0]})"
                elif len(pages) <= 5:
                    pages_str = ", ".join(str(p) for p in pages)
                    return f"{ref_num} {doc_name} (pages {pages_str})"
                else:
                    return f"{ref_num} {doc_name} (pages {pages[0]}-{pages[-1]}, {len(pages)} sections)"
            elif matched_path:
                return f"{ref_num} {Path(matched_path).name}"
            else:
                return match.group(0)  # Return original if no match
        
        # Apply both patterns
        enhanced = re.sub(reference_pattern1, enhance_reference, answer, flags=re.MULTILINE)
        enhanced = re.sub(reference_pattern2, enhance_reference, enhanced, flags=re.MULTILINE)
        return enhanced
    
    except Exception as e:
        print(f"⚠️  Could not enhance references: {e}")
        return answer


async def query_rag(rag: LightRAG, question: str, mode: str = "hybrid", verbose: bool = False, enhance_citations: bool = True):
    """Query the RAG system"""
    
    if verbose:
        print("\n" + "=" * 80)
        print(f"Query: {question}")
        print(f"Mode: {mode}")
        print("=" * 80 + "\n")
    
    # Query with specified mode
    param = QueryParam(mode=mode)
    answer = await rag.aquery(question, param=param)
    
    # Enhance references with page numbers if requested
    if enhance_citations:
        answer = enhance_references_with_pages(answer, rag.working_dir)
    
    return answer


async def interactive_mode(rag: LightRAG):
    """Run interactive Q&A session"""
    
    print("\n" + "=" * 80)
    print("LightRAG - Interactive Mode")
    print("=" * 80)
    print("\nCommands:")
    print("  Type your question to get an answer")
    print("  /mode <naive|local|global|hybrid>  - Change search mode")
    print("  /help                              - Show this help")
    print("  /exit or /quit                     - Exit interactive mode")
    print("\n" + "=" * 80 + "\n")
    
    current_mode = "hybrid"
    
    while True:
        try:
            user_input = input(f"\n[{current_mode}] ❯ ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ['/exit', '/quit', 'exit', 'quit']:
                print("\nGoodbye!")
                break
            
            elif user_input.lower() == '/help':
                print("\nAvailable Commands:")
                print("  <question>       - Ask a question")
                print("  /mode <mode>     - Change search mode")
                print("    Modes:")
                print("      • naive    - Simple vector search")
                print("      • local    - Entity-focused local search")
                print("      • global   - Community-based global search")
                print("      • hybrid   - Combined local + global (recommended)")
                print("  /help            - Show this help")
                print("  /exit or /quit   - Exit")
                continue
            
            elif user_input.startswith('/mode '):
                new_mode = user_input[6:].strip().lower()
                if new_mode in ['naive', 'local', 'global', 'hybrid']:
                    current_mode = new_mode
                    print(f"✓ Search mode changed to: {current_mode}")
                else:
                    print("❌ Invalid mode. Use: naive, local, global, or hybrid")
                continue
            
            else:
                # Regular question
                print(f"\nQ: {user_input}")
                print_separator("=")
                
                answer = await query_rag(rag, user_input, mode=current_mode)
                
                print(f"\nA: {answer}")
                print_separator("=")
        
        except KeyboardInterrupt:
            print("\n\nInterrupted. Use /exit to quit.")
            continue
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


async def compare_modes(rag: LightRAG, question: str):
    """Compare results across all search modes"""
    
    print("\n" + "=" * 80)
    print("Mode Comparison")
    print("=" * 80)
    print(f"\nQuestion: {question}")
    print_separator("-")
    
    modes = ['naive', 'local', 'global', 'hybrid']
    
    for mode in modes:
        print(f"\n📊 {mode.upper()} Mode:")
        print_separator("-")
        
        answer = await query_rag(rag, question, mode=mode)
        print(answer)
        print()


async def main():
    """Main query interface"""
    
    parser = argparse.ArgumentParser(
        description="Query the LightRAG system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Search Modes:
  naive   - Simple vector similarity search
  local   - Entity-focused local search (best for specific facts)
  global  - Community-based global search (best for summaries)
  hybrid  - Combined local + global search (recommended, default)

Examples:
  # Ask a question
  python lightrag_query.py "What is LightRAG?"
  
  # Use specific mode
  python lightrag_query.py "How does it work?" --mode local
  
  # Interactive mode
  python lightrag_query.py --interactive
  
  # Compare all modes
  python lightrag_query.py "What are the main features?" --compare
        """
    )
    
    parser.add_argument(
        "query",
        nargs="*",
        help="Question to ask (if not using --interactive or --compare)"
    )
    
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Start interactive Q&A session"
    )
    
    parser.add_argument(
        "-m", "--mode",
        type=str,
        default="hybrid",
        choices=['naive', 'local', 'global', 'hybrid'],
        help="Search mode (default: hybrid)"
    )
    
    parser.add_argument(
        "-w", "--working-dir",
        type=str,
        default="./lightrag_storage",
        help="Working directory for LightRAG storage (default: ./lightrag_storage)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed query information"
    )
    
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare results across all search modes"
    )
    
    args = parser.parse_args()
    
    # Check if storage exists
    working_path = Path(args.working_dir)
    if not working_path.exists():
        print(f"❌ Storage directory not found: {args.working_dir}")
        print("\nPlease run ingestion first:")
        print(f"  python lightrag_ingest.py --input <your-document>")
        return 1
    
    try:
        # Initialize LightRAG
        rag = await initialize_rag(args.working_dir)
        
        # Interactive mode
        if args.interactive:
            await interactive_mode(rag)
        
        # Compare modes
        elif args.compare:
            if not args.query:
                print("❌ Please provide a question for comparison")
                return 1
            question = " ".join(args.query)
            await compare_modes(rag, question)
        
        # Single query
        elif args.query:
            question = " ".join(args.query)
            
            print(f"\nQuestion: {question}")
            print_separator("=")
            
            answer = await query_rag(rag, question, mode=args.mode, verbose=args.verbose)
            
            print(f"\nAnswer:\n{answer}")
            print_separator("=")
            
            if args.verbose:
                print(f"\n(Search mode: {args.mode})")
        
        else:
            parser.print_help()
            return 1
        
        return 0
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
