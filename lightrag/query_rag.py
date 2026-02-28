#!/usr/bin/env python3
"""
Traditional/Custom Graph RAG CLI - FOR COMPARISON WITH LIGHTRAG

This is the ORIGINAL custom Graph RAG implementation for showcasing
the enhancement when applying official LightRAG.

Use this to compare:
- Traditional RAG: python lightrag/query_rag.py --interactive
- LightRAG (new): python lightrag/lightrag_query.py --interactive

Usage:
    python lightrag/query_rag.py "What is LightRAG?"
    python lightrag/query_rag.py --interactive
    python lightrag/query_rag.py --search "knowledge graph" --top-k 5
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from graph_rag import GraphRAG
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

print("\n" + "=" * 80)
print("🔵 TRADITIONAL/CUSTOM GRAPH RAG (Original Implementation)")
print("=" * 80)
print("This is the custom Graph RAG for comparison purposes.")
print("For the enhanced LightRAG version, use: python lightrag/lightrag_query.py")
print("=" * 80 + "\n")


def print_separator(char="=", length=80):
    """Print a separator line"""
    print(char * length)


def format_result(result, index=1):
    """Format a search result for display"""
    output = []
    output.append(f"\n--- Result {index} ---")
    output.append(f"Similarity: {result.similarity:.3f}")
    output.append(f"Chunk ID: {result.chunk_id}")
    output.append(f"\nText:")
    output.append(result.text[:400] + "..." if len(result.text) > 400 else result.text)
    
    if result.entities:
        entity_names = [e.get('name', 'N/A') for e in result.entities[:8]]
        output.append(f"\nEntities ({len(result.entities)}): {', '.join(entity_names)}")
    
    if result.relations:
        output.append(f"Relations: {len(result.relations)} connections")
    
    return "\n".join(output)


def interactive_mode(rag):
    """Run interactive Q&A session"""
    print("\n" + "="*80)
    print("Graph RAG - Interactive Mode")
    print("="*80)
    print("\nCommands:")
    print("  Type your question to get an answer")
    print("  /search <query>  - Search without generation")
    print("  /entity <name>   - Explore entity context")
    print("  /help            - Show this help")
    print("  /exit or /quit   - Exit interactive mode")
    print("\n" + "="*80 + "\n")
    
    while True:
        try:
            user_input = input("\n❯ ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ['/exit', '/quit', 'exit', 'quit']:
                print("\nGoodbye!")
                break
            
            elif user_input.lower() == '/help':
                print("\nCommands:")
                print("  <question>       - Ask a question and get a generated answer")
                print("  /search <query>  - Search and retrieve chunks without generation")
                print("  /entity <name>   - Explore an entity's context in the graph")
                print("  /help            - Show this help")
                print("  /exit or /quit   - Exit")
                continue
            
            elif user_input.startswith('/search '):
                query = user_input[8:].strip()
                if not query:
                    print("Usage: /search <query>")
                    continue
                
                print(f"\nSearching for: '{query}'")
                print_separator("-")
                
                results = rag.search(query, top_k=5)
                
                if not results:
                    print("No results found.")
                else:
                    for i, result in enumerate(results, 1):
                        print(format_result(result, i))
                        print_separator("-")
            
            elif user_input.startswith('/entity '):
                entity_name = user_input[8:].strip()
                if not entity_name:
                    print("Usage: /entity <name>")
                    continue
                
                print(f"\nExploring entity: '{entity_name}'")
                print_separator("-")
                
                context = rag.get_entity_context(entity_name, max_hops=2)
                
                if "error" in context:
                    print(f"Error: {context['error']}")
                else:
                    print(f"Entity: {context['entity']}")
                    print(f"Type: {context['type']}")
                    print(f"\nConnected Entities ({len(context['neighbors'])}):") 
                    for neighbor in context['neighbors'][:15]:
                        rel = neighbor.get('relationship', 'CONNECTED')
                        print(f"  → {neighbor['name']} ({neighbor['type']}) via {rel}")
            
            else:
                # Regular question
                print(f"\nQ: {user_input}")
                print_separator("=")
                
                answer = rag.query(user_input, verbose=False)
                
                print(f"\nA: {answer}")
                print_separator("=")
        
        except KeyboardInterrupt:
            print("\n\nInterrupted. Use /exit to quit.")
            continue
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Query the Graph RAG system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ask a question
  python query_rag.py "What is LightRAG?"
  
  # Search mode
  python query_rag.py --search "knowledge graph architecture" --top-k 5
  
  # Interactive mode
  python query_rag.py --interactive
  
  # Entity exploration
  python query_rag.py --entity "LightRAG"
  
  # Adjust parameters
  python query_rag.py "How does it work?" --top-k 3 --threshold 0.4
        """
    )
    
    parser.add_argument(
        "query",
        nargs="*",
        help="Question to ask (if not using --search or --entity)"
    )
    
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Start interactive Q&A session"
    )
    
    parser.add_argument(
        "-s", "--search",
        type=str,
        help="Search mode (retrieval only, no generation)"
    )
    
    parser.add_argument(
        "-e", "--entity",
        type=str,
        help="Explore entity context in the knowledge graph"
    )
    
    parser.add_argument(
        "-k", "--top-k",
        type=int,
        default=5,
        help="Number of results to retrieve (default: 5)"
    )
    
    parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=0.02,
        help="Similarity threshold (default: 0.02, range: 0.01-0.05 for L2 distance)"
    )
    
    parser.add_argument(
        "--no-graph",
        action="store_true",
        help="Disable graph expansion (vector search only)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed retrieval information"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM model to use (default: uses config from .env)"
    )
    
    args = parser.parse_args()
    
    # Initialize Graph RAG
    print("\nInitializing Graph RAG system...")
    print_separator("-")
    
    try:
        rag = GraphRAG(
            llm_model=args.model,
            top_k=args.top_k,
            similarity_threshold=args.threshold,
            expand_graph=not args.no_graph
        )
    except Exception as e:
        print(f"\nError initializing Graph RAG: {e}")
        print("\nMake sure:")
        print("  1. Neo4j is running (docker-compose up -d)")
        print("  2. Vector store exists (outputs/faiss.index)")
        print("  3. OpenAI API key is set (OPENAI_API_KEY)")
        return 1
    
    try:
        # Interactive mode
        if args.interactive:
            interactive_mode(rag)
        
        # Entity exploration
        elif args.entity:
            print(f"\nExploring entity: '{args.entity}'")
            print_separator("=")
            
            context = rag.get_entity_context(args.entity, max_hops=2)
            
            if "error" in context:
                print(f"Error: {context['error']}")
            else:
                print(f"\nEntity: {context['entity']}")
                print(f"Type: {context['type']}")
                print(f"\nConnected Entities ({len(context['neighbors'])} total):")
                print_separator("-")
                
                for i, neighbor in enumerate(context['neighbors'][:20], 1):
                    rel = neighbor.get('relationship', 'CONNECTED')
                    print(f"{i:2d}. {neighbor['name']}")
                    print(f"    Type: {neighbor['type']}, Relation: {rel}")
        
        # Search mode
        elif args.search:
            print(f"\nSearch query: '{args.search}'")
            print_separator("=")
            
            results = rag.search(args.search, top_k=args.top_k, threshold=args.threshold)
            
            if not results:
                print("\nNo results found above the similarity threshold.")
            else:
                print(f"\nFound {len(results)} results:\n")
                for i, result in enumerate(results, 1):
                    print(format_result(result, i))
                    print_separator("-")
        
        # Q&A mode
        elif args.query:
            question = " ".join(args.query)
            
            print(f"\nQuestion: {question}")
            print_separator("=")
            
            answer = rag.query(question, verbose=args.verbose)
            
            if not args.verbose:
                print(f"\nAnswer:\n{answer}")
                print_separator("=")
        
        else:
            parser.print_help()
            return 1
    
    finally:
        rag.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
