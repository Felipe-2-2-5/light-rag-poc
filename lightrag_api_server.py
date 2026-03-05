#!/usr/bin/env python3
"""
LightRAG API Server for Custom GPT Integration

Exposes the LightRAG retrieval system as a REST API for the Custom GPT.
Follows the evidence contract defined in custom-gpt/customer-gpt.md
"""

import os
import sys
import asyncio
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import nest_asyncio
import numpy as np

# Enable nested event loops
nest_asyncio.apply()

# Load environment variables
load_dotenv()

from lightrag import LightRAG, QueryParam

# Shared LLM setup – single authoritative implementation
sys.path.insert(0, str(Path(__file__).parent / "src"))
from llm_setup import setup_llm_functions  # noqa: E402

# Import the reference enhancement function
sys.path.insert(0, str(Path(__file__).parent / "lightrag"))
try:
    from lightrag_query import enhance_references_with_pages
except ImportError:
    # If import fails, we'll define a minimal version inline
    def enhance_references_with_pages(answer: str, working_dir: str) -> str:
        """Fallback - return answer as-is if import fails"""
        return answer

# Initialize FastAPI app
app = FastAPI(
    title="Internal Knowledge Navigator API (LightRAG)",
    description="LightRAG-powered retrieval system for Custom GPT integration",
    version="2.0.0"
)

# Enable CORS for ChatGPT
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chatgpt.com", "https://chat.openai.com", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global LightRAG instance
_rag_instance = None


def extract_citations_from_context(context: str, working_dir: str) -> List['Citation']:
    """
    Extract citation information from LightRAG's answer with references.
    Parses the ### References section and extracts document names and page ranges.
    Also looks up page information from storage when not in references.
    """
    import json
    import re
    
    citations = []
    
    try:
        # Load chunk and document storage for page lookup
        chunks_file = Path(working_dir) / "kv_store_text_chunks.json"
        docs_file = Path(working_dir) / "kv_store_full_docs.json"
        
        chunks_data = {}
        docs_data = {}
        
        if chunks_file.exists():
            with open(chunks_file, 'r', encoding='utf-8') as f:
                chunks_data = json.load(f)
        
        if docs_file.exists():
            with open(docs_file, 'r', encoding='utf-8') as f:
                docs_data = json.load(f)
        
        # Parse references from LightRAG's answer format
        # Look for ### References section
        if "### References" in context or "## References" in context:
            # Extract the references section
            ref_match = re.search(r'###?\s*References?\s*\n(.*?)(?:\n###|\n##|$)', context, re.DOTALL | re.IGNORECASE)
            if ref_match:
                references_text = ref_match.group(1)
                
                # Parse individual references
                # Format variations:
                #   - [1] Title 
                #   - [1] path/to/file.pdf 
                #   - [1] file.pdf (page 5)
                #   - [1] file.pdf (pages 1, 3, 5-7)
                #   - [1] file.pdf (pages 1-10)
                ref_pattern = r'-\s*\[(\d+)\]\s*(.+?)(?:\s*\((pages?)\s+([0-9,\s-]+)\))?$'
                
                for match in re.finditer(ref_pattern, references_text, re.MULTILINE):
                    ref_num = match.group(1)
                    doc_info = match.group(2).strip()
                    page_keyword = match.group(3)  # 'page' or 'pages'
                    page_range_text = match.group(4)  # e.g., "5" or "1, 3, 5-7" or "1-10"
                    
                    # Extract document name (could be a path or title)
                    doc_name = doc_info
                    file_path_hint = None
                    
                    if '/' in doc_info or '\\' in doc_info:
                        # It's a path
                        doc_name = Path(doc_info).name
                        file_path_hint = doc_info
                    else:
                        # It's a title - keep first 80 chars
                        doc_name = doc_info[:80]
                    
                    # Determine page info
                    page_num = None
                    location = f"Reference [{ref_num}]"
                    
                    if page_range_text:
                        # Parse page numbers from various formats:
                        # "5" -> page 5
                        # "1, 3, 5" -> pages 1, 3, 5
                        # "1-10" -> pages 1-10
                        # "1, 3, 5-7" -> pages 1, 3, 5-7
                        
                        page_range_text = page_range_text.strip()
                        
                        # Extract first page number for the page field
                        first_page_match = re.search(r'(\d+)', page_range_text)
                        if first_page_match:
                            page_num = int(first_page_match.group(1))
                        
                        # Format location string
                        if ',' in page_range_text or len(page_range_text) > 10:
                            # Multiple pages or complex range
                            location = f"pages {page_range_text}"
                        elif '-' in page_range_text:
                            # Simple range like "1-10"
                            location = f"pages {page_range_text}"
                        else:
                            # Single page
                            location = f"page {page_range_text}"
                    else:
                        # Try to look up page info from storage by matching document name/title
                        for doc_id, doc_data in docs_data.items():
                            doc_file_path = doc_data.get('file_path', '')
                            doc_content = doc_data.get('content', '')
                            
                            # Check if this document matches
                            matches = False
                            if file_path_hint and file_path_hint in doc_file_path:
                                matches = True
                            elif doc_name in doc_content[:200]:  # Check if title appears in doc content
                                matches = True
                            elif doc_file_path != 'unknown_source' and Path(doc_file_path).stem in doc_name:
                                matches = True
                            
                            if matches:
                                # Count chunks for this document to estimate page range
                                doc_chunks = [c for c in chunks_data.values() if c.get('full_doc_id') == doc_id]
                                if doc_chunks:
                                    # Estimate pages: ~2-3 chunks per page
                                    estimated_pages = max(1, len(doc_chunks) // 2)
                                    page_num = 1
                                    location = f"pages 1-{estimated_pages}"
                                break
                    
                    citations.append(Citation(
                        document=doc_name,
                        page=page_num,
                        location=location,
                        chunk_id=f"ref-{ref_num}"
                    ))
        
        # Fallback: If no references section, try to extract from storage
        if not citations and chunks_data:
            # Find chunks that appear in the context
            chunk_ids = []
            for chunk_id, chunk_data in chunks_data.items():
                content_sample = chunk_data.get('content', '')[:150]
                if content_sample and content_sample in context:
                    chunk_ids.append(chunk_id)
            
            # Build citations from found chunks
            seen_docs = set()
            for chunk_id in chunk_ids[:5]:
                chunk_data = chunks_data.get(chunk_id, {})
                if not chunk_data:
                    continue
                
                file_path = chunk_data.get('file_path', 'unknown_source')
                chunk_index = chunk_data.get('chunk_order_index', 0)
                
                # Skip unknown sources
                if file_path == 'unknown_source':
                    continue
                
                doc_name = Path(file_path).name
                
                # Estimate page based on chunk index (rough: 1 page per 2-3 chunks)
                estimated_page = (chunk_index // 2) + 1
                location = f"section {chunk_index + 1}"
                
                doc_key = f"{doc_name}_{estimated_page}"
                if doc_key not in seen_docs:
                    citations.append(Citation(
                        document=doc_name,
                        page=estimated_page,
                        location=location,
                        chunk_id=chunk_id[-12:]
                    ))
                    seen_docs.add(doc_key)
    
    except Exception as e:
        print(f"Warning: Could not extract citations: {e}")
        import traceback
        traceback.print_exc()
    
    return citations


async def initialize_lightrag():
    """Initialize LightRAG system"""
    global _rag_instance
    
    if _rag_instance is not None:
        return _rag_instance
    
    print("⏳ Initializing LightRAG system...")
    
    working_dir = os.getenv("LIGHTRAG_WORKING_DIR", "./lightrag_storage")
    
    # Check if storage exists
    working_path = Path(working_dir)
    if not working_path.exists():
        raise RuntimeError(
            f"LightRAG storage not found at {working_dir}. "
            "Please run ingestion first: python lightrag/lightrag_ingest.py"
        )
    
    llm_model_func, embedding_func, model_name = setup_llm_functions()
    
    _rag_instance = LightRAG(
        working_dir=working_dir,
        llm_model_func=llm_model_func,
        embedding_func=embedding_func,
        llm_model_name=model_name,
    )
    
    await _rag_instance.initialize_storages()
    
    print(f"✓ LightRAG initialized (Model: {model_name})")
    
    return _rag_instance


# Pydantic models for API
class QueryRequest(BaseModel):
    """Query request from Custom GPT"""
    query: str = Field(description="User's question")
    mode: str = Field(
        default="hybrid",
        description="Search mode: naive, local, global, or hybrid"
    )
    only_need_context: bool = Field(
        default=False,
        description="If True, return only context chunks without LLM synthesis"
    )
    max_chunks: int = Field(
        default=5,
        description="Maximum number of evidence chunks to return (context-only mode)"
    )
    max_chunk_size: int = Field(
        default=400,
        description="Maximum characters per chunk (context-only mode)"
    )


class Citation(BaseModel):
    """Citation information for evidence source"""
    document: str = Field(description="Document name")
    page: Optional[int] = Field(default=None, description="Page number (if available)")
    location: Optional[str] = Field(default=None, description="Location description (e.g., 'line 45-52')")
    chunk_id: str = Field(description="Internal chunk identifier")


class EvidenceChunk(BaseModel):
    """Evidence chunk from retrieval"""
    chunk_id: str = Field(description="Chunk identifier")
    text: str = Field(description="Chunk text content")
    relevance: str = Field(description="Relevance level: HIGH, MEDIUM, LOW")
    citation: Optional[Citation] = Field(default=None, description="Source citation information")


class RetrievalResponse(BaseModel):
    """
    Response format following the Custom GPT evidence contract.
    This provides RAW EVIDENCE only - no LLM synthesis.
    """
    query: str = Field(description="Original user query")
    mode: str = Field(description="Search mode used")
    evidence_chunks: List[EvidenceChunk] = Field(
        description="Retrieved evidence chunks"
    )
    evidence_summary: str = Field(
        description="Brief summary of retrieval results"
    )
    confidence: str = Field(
        description="Confidence level: HIGH, MEDIUM, LOW"
    )


class SynthesizedResponse(BaseModel):
    """
    Full response with LLM synthesis (default mode).
    This is what gets returned when only_need_context=False.
    """
    query: str = Field(description="Original user query")
    mode: str = Field(description="Search mode used")
    answer: str = Field(description="LLM-synthesized answer")
    evidence_used: str = Field(
        description="Brief description of evidence used"
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Detailed citations for evidence sources"
    )
    confidence: str = Field(
        description="Answer confidence: HIGH, MEDIUM, LOW"
    )


@app.on_event("startup")
async def startup_event():
    """Initialize LightRAG on startup"""
    try:
        await initialize_lightrag()
    except Exception as e:
        print(f"❌ Failed to initialize LightRAG: {e}")
        import traceback
        traceback.print_exc()


@app.get("/", tags=["Health"])
async def root():
    """API health check"""
    return {
        "status": "operational",
        "service": "Internal Knowledge Navigator API (LightRAG)",
        "version": "2.0.0",
        "backend": "LightRAG"
    }


@app.get("/health", tags=["Health"])
async def health():
    """Detailed health check"""
    return {
        "status": "healthy" if _rag_instance else "initializing",
        "components": {
            "lightrag": _rag_instance is not None,
        },
        "working_dir": os.getenv("LIGHTRAG_WORKING_DIR", "./lightrag_storage")
    }


@app.post("/retrieve", response_model=SynthesizedResponse, tags=["Retrieval"])
async def retrieve_and_answer(request: QueryRequest):
    """
    Primary endpoint: Retrieve evidence and synthesize an answer.
    
    This endpoint:
    1. Uses LightRAG to retrieve relevant context
    2. Uses LLM to synthesize a grounded answer
    3. Returns the answer with evidence metadata
    
    This is the default mode that Custom GPT should use.
    """
    if not _rag_instance:
        raise HTTPException(
            status_code=503,
            detail="LightRAG system not initialized"
        )
    
    try:
        print(f"🔍 Query: {request.query} (mode: {request.mode})")
        
        # Query LightRAG
        param = QueryParam(mode=request.mode)
        answer = await _rag_instance.aquery(request.query, param=param)
        
        # Handle None or empty answer
        if not answer:
            raise HTTPException(status_code=500, detail="Query returned no results")
        
        # Enhance references with page numbers BEFORE extracting citations
        working_dir = os.getenv("LIGHTRAG_WORKING_DIR", "./lightrag_storage")
        answer = enhance_references_with_pages(answer, working_dir)
        
        # Determine confidence based on answer length and content
        answer_lower = answer.lower()
        if len(answer) > 200 and "reference" in answer_lower:
            confidence = "HIGH"
        elif len(answer) > 100:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        # Extract citations from the answer context (now with page numbers)
        citations = extract_citations_from_context(answer, working_dir)
        
        # Format evidence description with citations
        if citations:
            evidence_desc = f"Retrieved and synthesized using {request.mode} search mode. "
            evidence_desc += f"Evidence from {len(citations)} source(s): "
            evidence_desc += ", ".join([
                f"{c.document}" + (f" (page {c.page})" if c.page else "")
                for c in citations[:3]
            ])
            if len(citations) > 3:
                evidence_desc += f" and {len(citations) - 3} more"
        else:
            evidence_desc = f"Retrieved and synthesized using {request.mode} search mode"
        
        return SynthesizedResponse(
            query=request.query,
            mode=request.mode,
            answer=answer,
            evidence_used=evidence_desc,
            citations=citations,
            confidence=confidence
        )
    
    except Exception as e:
        print(f"❌ Query error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/retrieve/context-only", response_model=RetrievalResponse, tags=["Retrieval"])
async def retrieve_context_only(request: QueryRequest):
    """
    Alternative endpoint: Retrieve raw evidence without LLM synthesis.
    
    This returns ONLY the retrieved context chunks, allowing the
    Custom GPT to do its own synthesis using the evidence contract.
    
    Use this if you want maximum control over the final answer.
    """
    if not _rag_instance:
        raise HTTPException(
            status_code=503,
            detail="LightRAG system not initialized"
        )
    
    try:
        print(f"🔍 Context-only query: {request.query} (mode: {request.mode})")
        
        # Query LightRAG with only_need_context=True to get raw context
        param = QueryParam(mode=request.mode, only_need_context=True)
        context = await _rag_instance.aquery(request.query, param=param)
        
        # Parse context into chunks (simplified - context is returned as text)
        # In a real implementation, you'd extract structured chunks from LightRAG
        chunks = []
        working_dir = os.getenv("LIGHTRAG_WORKING_DIR", "./lightrag_storage")
        citations = extract_citations_from_context(context, working_dir)
        
        if context:
            # Split context into logical chunks
            sections = context.split("\n\n")
            max_chunks = min(request.max_chunks, 5)  # Hard limit of 5 chunks
            for idx, section in enumerate(sections[:max_chunks]):
                if section.strip():
                    # Truncate chunk to prevent response size issues
                    chunk_text = section.strip()
                    if len(chunk_text) > request.max_chunk_size:
                        chunk_text = chunk_text[:request.max_chunk_size] + "... [truncated]"
                    
                    relevance = "HIGH" if idx < 2 else "MEDIUM" if idx < 4 else "LOW"
                    
                    # Attach citation if available
                    citation = citations[idx] if idx < len(citations) else None
                    
                    chunks.append(EvidenceChunk(
                        chunk_id=f"chunk_{idx}",
                        text=chunk_text,
                        relevance=relevance,
                        citation=citation
                    ))
        
        # Determine confidence
        if len(chunks) >= 5:
            confidence = "HIGH"
        elif len(chunks) >= 2:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        evidence_summary = f"Retrieved {len(chunks)} evidence chunks using {request.mode} mode"
        
        return RetrievalResponse(
            query=request.query,
            mode=request.mode,
            evidence_chunks=chunks,
            evidence_summary=evidence_summary,
            confidence=confidence
        )
    
    except Exception as e:
        print(f"❌ Query error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/retrieve/simple", tags=["Retrieval"])
async def retrieve_simple(
    query: str = Query(..., description="User's question"),
    mode: str = Query("hybrid", description="Search mode")
):
    """
    Simplified GET endpoint for quick testing.
    Returns just the answer text.
    """
    request = QueryRequest(query=query, mode=mode)
    response = await retrieve_and_answer(request)
    
    return {
        "query": query,
        "answer": response.answer,
        "confidence": response.confidence
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", "8001"))
    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║   Internal Knowledge Navigator API (LightRAG)           ║
    ║   Custom GPT Integration                                 ║
    ╚══════════════════════════════════════════════════════════╝
    
    🌐 API URL: http://localhost:{port}
    📚 Docs: http://localhost:{port}/docs
    🔍 Health: http://localhost:{port}/health
    
    Backend: LightRAG
    Storage: {os.getenv("LIGHTRAG_WORKING_DIR", "./lightrag_storage")}
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=port)
