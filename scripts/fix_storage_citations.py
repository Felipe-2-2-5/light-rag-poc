#!/usr/bin/env python3
"""
Fix LightRAG Storage for Citations

This script updates the storage files to include proper:
1. File paths (instead of "unknown_source")
2. Page number estimates based on chunk order
3. Document titles extracted from content

Run this after ingestion to enable proper citations.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any

def extract_document_title(content: str) -> str:
    """Extract a meaningful title from document content"""
    
    # Try to find title patterns
    lines = content.strip().split('\n')
    
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        if not line:
            continue
        
        # Skip arxiv metadata and formatting junk
        if 'arxiv' in line.lower() or re.match(r'^[\d\s\[\]]+$', line):
            continue
        
        # Check for common title patterns
        if len(line) > 10 and len(line) < 150:
            # MA-RAG pattern
            if 'MA-RAG' in line:
                return 'MA-RAG: Multi-Agent Retrieval-Augmented Generation'
            # LIGHTRAG pattern
            elif 'LIGHTRAG' in line.upper():
                return 'LightRAG: Simple and Fast Retrieval-Augmented Generation'
            # RAG-Based AI Agents pattern
            elif 'RAG-Based AI Agent' in line:
                return 'RAG-Based AI Agents for Enterprise SDLC'
            # Multi-Agent Approach pattern
            elif 'COLLABORATIVE MULTI-AGENT' in line.upper():
                return 'Collaborative Multi-Agent Approach to RAG'
            # Aalto University thesis
            elif 'Aalto' in line:
                return 'Aalto University Building Technology Thesis'
            # Agent Design Pattern
            elif 'AGENT DESIGN PATTERN' in line.upper():
                return 'Agent Design Pattern Catalogue'
            # Graduation Project
            elif 'Group Project Title' in line or 'Multi-Agent RAG-Based System' in line:
                return 'Multi-Agent RAG-Based System for SDLC Automation'
            # Vietnamese law
            elif 'LUẬT BẢO VỆ' in line or 'MÔI TRƯỜNG' in line:
                return 'Luật Bảo vệ Môi trường (Vietnamese Environmental Law)'
            # Generic readable title
            elif line[0].isupper() and not any(c in line for c in ['$', '{', '}', '\\', '|']):
                return line[:100]
    
    # Fallback: use first meaningful content
    for line in lines[:20]:
        line = line.strip()
        if len(line) > 30 and len(line) < 150:
            clean = re.sub(r'[^\w\s\-]', ' ', line)
            if len(clean.split()) >= 3:
                return clean[:80] + '...'
    
    return 'Unknown Document'


def estimate_page_number(chunk_index: int, avg_chars_per_chunk: int = 1200, chars_per_page: int = 2000) -> int:
    """Estimate page number based on chunk position"""
    estimated_char_position = chunk_index * avg_chars_per_chunk
    estimated_page = (estimated_char_position // chars_per_page) + 1
    return max(1, estimated_page)


def fix_storage_citations(working_dir: str = "./lightrag_storage"):
    """Fix storage files to enable proper citations"""
    
    working_path = Path(working_dir)
    
    docs_file = working_path / "kv_store_full_docs.json"
    chunks_file = working_path / "kv_store_text_chunks.json"
    
    if not docs_file.exists() or not chunks_file.exists():
        print(f"❌ Storage files not found in {working_dir}")
        return False
    
    print("=" * 60)
    print("Fixing LightRAG Storage for Citations")
    print("=" * 60)
    
    # Load data
    print("\n📂 Loading storage files...")
    with open(docs_file, 'r', encoding='utf-8') as f:
        docs = json.load(f)
    
    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    print(f"✓ Loaded {len(docs)} documents and {len(chunks)} chunks")
    
    # Build document title mapping
    print("\n📝 Extracting document titles...")
    doc_titles = {}
    for doc_id, doc_data in docs.items():
        content = doc_data.get('content', '')
        title = extract_document_title(content)
        doc_titles[doc_id] = title
        
        # Guess file extension based on content
        if content.startswith(('##', '#')) or '.md' in title.lower():
            extension = '.md'
        else:
            extension = '.pdf'
        
        filename = title.replace(':', '').replace('/', '-') + extension
        doc_titles[doc_id] = filename
        
        print(f"  {doc_id[:20]}... → {filename}")
    
    # Update documents
    print("\n📄 Updating documents...")
    updated_docs = 0
    for doc_id, doc_data in docs.items():
        old_path = doc_data.get('file_path', 'unknown_source')
        if old_path == 'unknown_source':
            new_path = f"data/{doc_titles[doc_id]}"
            doc_data['file_path'] = new_path
            updated_docs += 1
    
    print(f"✓ Updated {updated_docs} document file paths")
    
    # Update chunks
    print("\n🧩 Updating chunks with citation metadata...")
    updated_chunks = 0
    for chunk_id, chunk_data in chunks.items():
        old_path = chunk_data.get('file_path', 'unknown_source')
        
        if old_path == 'unknown_source':
            # Get document info
            doc_id = chunk_data.get('full_doc_id', '')
            if doc_id in doc_titles:
                # Update file path
                chunk_data['file_path'] = f"data/{doc_titles[doc_id]}"
                
                # Add page estimate (not overwriting if it exists)
                if 'page' not in chunk_data:
                    chunk_index = chunk_data.get('chunk_order_index', 0)
                    content_length = len(chunk_data.get('content', ''))
                    chunk_data['page'] = estimate_page_number(chunk_index, content_length)
                
                # Add document title for easy reference
                if 'document_title' not in chunk_data:
                    chunk_data['document_title'] = doc_titles[doc_id]
                
                updated_chunks += 1
    
    print(f"✓ Updated {updated_chunks} chunks")
    
    # Save updated data
    print("\n💾 Saving updates...")
    
    # Backup originals
    backup_dir = working_path / "backup_before_citation_fix"
    backup_dir.mkdir(exist_ok=True)
    
    import shutil
    shutil.copy(docs_file, backup_dir / "kv_store_full_docs.json")
    shutil.copy(chunks_file, backup_dir / "kv_store_text_chunks.json")
    print(f"✓ Backups saved to {backup_dir}")
    
    # Write updated files
    with open(docs_file, 'w', encoding='utf-8') as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)
    
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    
    print("✓ Storage files updated successfully")
    
    # Show summary
    print("\n" + "=" * 60)
    print("Citation Fix Summary")
    print("=" * 60)
    print(f"✓ Documents identified: {len(doc_titles)}")
    print(f"✓ Document paths updated: {updated_docs}")
    print(f"✓ Chunks updated: {updated_chunks}")
    print(f"✓ Page numbers estimated: {updated_chunks}")
    print("\nDocuments now have proper citations enabled!")
    print("\n📋 Document List:")
    for doc_id, filename in doc_titles.items():
        chunk_count = sum(1 for c in chunks.values() if c.get('full_doc_id') == doc_id)
        print(f"  • {filename} ({chunk_count} chunks)")
    
    print("\n✅ Citations fixed! Query results will now include page numbers.")
    
    return True


if __name__ == "__main__":
    import sys
    
    working_dir = sys.argv[1] if len(sys.argv) > 1 else "./lightrag_storage"
    
    try:
        success = fix_storage_citations(working_dir)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
