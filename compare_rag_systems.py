#!/usr/bin/env python3
"""
RAG Systems Comparison Tool

Compares Traditional/Custom Graph RAG vs Official LightRAG
to showcase the enhancement and improvements.

Usage:
    python compare_rag_systems.py
    python compare_rag_systems.py --question "What is LightRAG?"
"""

import sys
import subprocess
import time
import argparse
from pathlib import Path


def print_header(title, char="="):
    """Print a formatted header"""
    print(f"\n{char * 80}")
    print(f"{title:^80}")
    print(f"{char * 80}\n")


def query_traditional(question):
    """Query the traditional/custom Graph RAG system"""
    print_header("🔵 TRADITIONAL/CUSTOM GRAPH RAG", "-")
    print("Implementation: Custom FAISS + Neo4j + LangChain")
    print("Entity Extraction: Regex patterns")
    print("Query Mode: Basic search")
    print("-" * 80)
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            ["python", "lightrag/query_rag.py", question],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            # Filter out the header from output
            output_lines = result.stdout.split('\n')
            # Skip the first few lines (header)
            filtered_output = '\n'.join([
                line for line in output_lines 
                if not line.startswith('='*80) and
                   'TRADITIONAL' not in line and
                   'For the enhanced' not in line
            ]).strip()
            
            print(f"\n{filtered_output}\n")
            print(f"⏱️  Query time: {elapsed:.2f}s")
            return {
                'success': True,
                'time': elapsed,
                'output': filtered_output
            }
        else:
            print(f"❌ Error: {result.stderr}")
            return {'success': False, 'time': elapsed, 'error': result.stderr}
    
    except subprocess.TimeoutExpired:
        print("❌ Timeout after 60 seconds")
        return {'success': False, 'time': 60, 'error': 'Timeout'}
    except Exception as e:
        print(f"❌ Exception: {e}")
        return {'success': False, 'time': 0, 'error': str(e)}


def query_lightrag(question, mode="hybrid"):
    """Query the official LightRAG system"""
    print_header("🟢 OFFICIAL LIGHTRAG", "-")
    print("Implementation: Official LightRAG library")
    print("Entity Extraction: LLM-based (high accuracy)")
    print(f"Query Mode: {mode}")
    print("-" * 80)
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            ["python", "lightrag/lightrag_query.py", question, "--mode", mode],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            print(f"\n{result.stdout}\n")
            print(f"⏱️  Query time: {elapsed:.2f}s")
            return {
                'success': True,
                'time': elapsed,
                'output': result.stdout
            }
        else:
            print(f"❌ Error: {result.stderr}")
            return {'success': False, 'time': elapsed, 'error': result.stderr}
    
    except subprocess.TimeoutExpired:
        print("❌ Timeout after 60 seconds")
        return {'success': False, 'time': 60, 'error': 'Timeout'}
    except Exception as e:
        print(f"❌ Exception: {e}")
        return {'success': False, 'time': 0, 'error': str(e)}


def compare_systems(question, lightrag_mode="hybrid"):
    """Run both systems and compare results"""
    
    print_header("RAG SYSTEMS COMPARISON", "=")
    print(f"Question: {question}")
    
    # Query traditional RAG
    traditional_result = query_traditional(question)
    
    print("\n")
    
    # Query LightRAG
    lightrag_result = query_lightrag(question, lightrag_mode)
    
    # Comparison summary
    print_header("COMPARISON SUMMARY", "=")
    
    if traditional_result['success'] and lightrag_result['success']:
        trad_time = traditional_result['time']
        light_time = lightrag_result['time']
        
        print(f"Traditional RAG:")
        print(f"  ✓ Query time: {trad_time:.2f}s")
        print(f"  ✓ Output length: {len(traditional_result['output'])} chars")
        
        print(f"\nLightRAG ({lightrag_mode} mode):")
        print(f"  ✓ Query time: {light_time:.2f}s")
        print(f"  ✓ Output length: {len(lightrag_result['output'])} chars")
        
        # Performance comparison
        if trad_time > light_time:
            speedup = ((trad_time - light_time) / trad_time) * 100
            print(f"\n🚀 LightRAG was {speedup:.1f}% faster")
        elif light_time > trad_time:
            slower = ((light_time - trad_time) / trad_time) * 100
            print(f"\n⏱️  LightRAG took {slower:.1f}% longer (may have more accurate processing)")
        else:
            print(f"\n⚖️  Both systems had similar response times")
        
        # Output comparison
        output_diff = len(lightrag_result['output']) - len(traditional_result['output'])
        if output_diff > 100:
            print(f"📝 LightRAG provided {output_diff} more characters of context")
        elif output_diff < -100:
            print(f"📝 Traditional RAG provided {abs(output_diff)} more characters")
        else:
            print(f"📝 Both systems provided similar output length")
    
    else:
        if not traditional_result['success']:
            print("❌ Traditional RAG failed")
        if not lightrag_result['success']:
            print("❌ LightRAG failed")
    
    print("\n" + "=" * 80)


def interactive_demo():
    """Run interactive comparison demo"""
    
    print_header("🎯 RAG SYSTEMS INTERACTIVE COMPARISON", "=")
    print("Compare Traditional/Custom Graph RAG vs Official LightRAG")
    print("\nEnter questions to compare both systems side-by-side.")
    print("Type 'quit' or 'exit' to stop.")
    print("=" * 80)
    
    demo_questions = [
        "What is LightRAG?",
        "Explain the multi-agent architecture",
        "What are the main components of the system?",
        "How does knowledge graph extraction work?",
    ]
    
    print("\n💡 Example questions:")
    for i, q in enumerate(demo_questions, 1):
        print(f"  {i}. {q}")
    
    print()
    
    while True:
        try:
            question = input("\n❯ Your question (or 'quit'): ").strip()
            
            if not question:
                continue
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            # Check if it's a number (demo question selector)
            if question.isdigit():
                idx = int(question) - 1
                if 0 <= idx < len(demo_questions):
                    question = demo_questions[idx]
                    print(f"\nUsing demo question: {question}")
                else:
                    print(f"❌ Invalid demo question number. Choose 1-{len(demo_questions)}")
                    continue
            
            # Run comparison
            compare_systems(question)
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            continue


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Compare Traditional RAG vs LightRAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python compare_rag_systems.py
  
  # Single comparison
  python compare_rag_systems.py --question "What is LightRAG?"
  
  # Compare with different LightRAG mode
  python compare_rag_systems.py --question "Your question" --mode mix
        """
    )
    
    parser.add_argument(
        "-q", "--question",
        type=str,
        help="Question to compare (if not provided, runs interactive mode)"
    )
    
    parser.add_argument(
        "-m", "--mode",
        type=str,
        default="hybrid",
        choices=["local", "global", "hybrid", "mix", "naive"],
        help="LightRAG query mode (default: hybrid)"
    )
    
    args = parser.parse_args()
    
    if args.question:
        # Single question mode
        compare_systems(args.question, args.mode)
    else:
        # Interactive mode
        interactive_demo()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
