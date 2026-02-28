#!/usr/bin/env python3
"""
Parser Comparison Script

Compare classic text extraction vs RAG-Anything multimodal parsing
to help evaluate which approach works better for your documents.

Usage:
    python compare_parsers.py data/LIGHTRAG.pdf
    python compare_parsers.py data/*.pdf
"""

import sys
import os
import argparse
from pathlib import Path

# Add lightrag directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "lightrag"))

from lightrag_ingest import read_document


def analyze_parsing_result(text: str, parser_name: str):
    """Analyze and print statistics about parsed content"""
    
    print(f"\n{'='*60}")
    print(f"{parser_name} Results")
    print(f"{'='*60}")
    
    # Basic statistics
    char_count = len(text)
    word_count = len(text.split())
    line_count = len(text.split('\n'))
    
    print(f"\n📊 Statistics:")
    print(f"  Characters: {char_count:,}")
    print(f"  Words: {word_count:,}")
    print(f"  Lines: {line_count:,}")
    
    # Detect special content markers
    has_tables = '[TABLES]' in text
    has_images = '[IMAGES/DIAGRAMS]' in text
    has_formulas = '[FORMULAS]' in text
    
    if has_tables or has_images or has_formulas:
        print(f"\n📋 Special Content Detected:")
        if has_tables:
            table_section = text.split('[TABLES]')[1].split('[')[0]
            table_count = table_section.count('Table ')
            print(f"  ✓ Tables: {table_count}")
        if has_images:
            image_section = text.split('[IMAGES/DIAGRAMS]')[1].split('[')[0]
            image_count = image_section.count('Figure ')
            print(f"  ✓ Images/Diagrams: {image_count}")
        if has_formulas:
            formula_section = text.split('[FORMULAS]')[1].split('[')[0] if '[' in text.split('[FORMULAS]')[1] else text.split('[FORMULAS]')[1]
            formula_count = formula_section.count('Formula ')
            print(f"  ✓ Formulas: {formula_count}")
    
    # Preview
    print(f"\n📄 Content Preview (first 500 chars):")
    print("-" * 60)
    print(text[:500])
    print("-" * 60)


def compare_parsers(filepath: str):
    """Compare both parsing approaches for a single file"""
    
    print("\n" + "="*80)
    print("PARSER COMPARISON")
    print("="*80)
    print(f"\nFile: {filepath}")
    
    # Parse with classic method
    print("\n\n🔵 Testing CLASSIC Parser (Unstructured.io)...")
    try:
        classic_text = read_document(filepath, use_ade_fallback=True, use_rag_anything=False)
        analyze_parsing_result(classic_text, "Classic Parser (Text Only)")
    except Exception as e:
        print(f"\n❌ Classic parser failed: {e}")
        classic_text = None
    
    # Parse with RAG-Anything
    print("\n\n🟢 Testing RAG-ANYTHING Parser (Multimodal)...")
    try:
        multimodal_text = read_document(filepath, use_ade_fallback=False, use_rag_anything=True)
        analyze_parsing_result(multimodal_text, "RAG-Anything (Multimodal)")
    except Exception as e:
        print(f"\n❌ RAG-Anything parser failed: {e}")
        print("   Install with: pip install raganything")
        multimodal_text = None
    
    # Comparison summary
    if classic_text and multimodal_text:
        print("\n" + "="*80)
        print("COMPARISON SUMMARY")
        print("="*80)
        
        classic_size = len(classic_text)
        multimodal_size = len(multimodal_text)
        
        print(f"\nContent Size:")
        print(f"  Classic: {classic_size:,} chars")
        print(f"  RAG-Anything: {multimodal_size:,} chars")
        print(f"  Difference: {abs(multimodal_size - classic_size):,} chars ({((multimodal_size - classic_size) / classic_size * 100):.1f}%)")
        
        # Recommendations
        print(f"\n💡 Recommendation:")
        
        has_structured_content = '[TABLES]' in multimodal_text or '[IMAGES/DIAGRAMS]' in multimodal_text or '[FORMULAS]' in multimodal_text
        
        if has_structured_content:
            print("  ✅ Use RAG-ANYTHING - Document contains tables, images, or formulas")
            print("     that benefit from multimodal parsing")
        else:
            print("  ✅ Either parser works - Document is primarily text")
            print("     Classic parser is faster, RAG-Anything provides more detail")
    
    print("\n" + "="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Compare classic vs RAG-Anything parsing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "files",
        nargs="+",
        help="PDF files to compare"
    )
    
    args = parser.parse_args()
    
    # Process each file
    for filepath in args.files:
        path = Path(filepath)
        if path.exists():
            compare_parsers(str(path))
        else:
            print(f"⚠️  File not found: {filepath}")
    
    print("\n✓ Comparison complete!")
    print("\nNext steps:")
    print("1. For multimodal PDFs, use: python lightrag/lightrag_ingest.py --input FILE --use-rag-anything")
    print("2. For text-heavy docs, use: python lightrag/lightrag_ingest.py --input FILE")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
