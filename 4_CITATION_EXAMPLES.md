# Citation System Documentation

## Overview

The LightRAG API now includes detailed **citation information** for all evidence used in responses. This provides transparency about which documents, pages, and sections were referenced when generating answers.

## Citation Structure

Each citation includes:
- **document**: The name of the source document
- **page**: The page number where the information can be found (if available)
- **location**: Description of the specific location (e.g., "section 3", "chunk 5")
- **chunk_id**: Internal identifier for traceability

## API Response Format

### Synthesized Response (Default Mode)

```json
{
  "query": "What is the purpose of the LightRAG API?",
  "mode": "hybrid",
  "answer": "LightRAG is a retrieval-augmented generation system that...",
  "evidence_used": "Retrieved and synthesized using hybrid search mode. Evidence from 3 source(s): Multi-Agent Retrieval-Augmented System.pdf (page 2), LIGHTRAG: SIMPLE AND FAST RETRIEVAL-AUGMENTED GENERATION.pdf (page 1), Graduation Project.md",
  "citations": [
    {
      "document": "Multi-Agent Retrieval-Augmented System.pdf",
      "page": 2,
      "location": "section 1",
      "chunk_id": "bf58fea9"
    },
    {
      "document": "LIGHTRAG: SIMPLE AND FAST RETRIEVAL-AUGMENTED GENERATION.pdf",
      "page": 1,
      "location": "section 0",
      "chunk_id": "536ebb6e"
    },
    {
      "document": "Graduation Project.md",
      "page": 1,
      "location": "section 0",
      "chunk_id": "a50a9326"
    }
  ],
  "confidence": "HIGH"
}
```

### Context-Only Response

When using the `/retrieve/context-only` endpoint, each evidence chunk includes its own citation:

```json
{
  "query": "What is multi-agent RAG?",
  "mode": "hybrid",
  "evidence_chunks": [
    {
      "chunk_id": "chunk_0",
      "text": "A COLLABORATIVE MULTI-AGENT APPROACH TO RETRIEVAL-AUGMENTED GENERATION...",
      "relevance": "HIGH",
      "citation": {
        "document": "Multi-Agent Retrieval-Augmented System.pdf",
        "page": 1,
        "location": "section 0",
        "chunk_id": "f9f4dddca093"
      }
    },
    {
      "chunk_id": "chunk_1",
      "text": "The proposed system introduces a modular design...",
      "relevance": "HIGH",
      "citation": {
        "document": "Multi-Agent Retrieval-Augmented System.pdf",
        "page": 3,
        "location": "section 2",
        "chunk_id": "713c82a786"
      }
    }
  ],
  "evidence_summary": "Retrieved 2 evidence chunks using hybrid mode",
  "confidence": "MEDIUM"
}
```

## How Citations Work

### 1. Document Parsing with Page Tracking

When documents are ingested, the document parser (using Unstructured.io) extracts page information:

```python
# From document_parser.py
elements = partition(
    filename=file_path,
    strategy="hi_res",
    languages=["vie", "eng"],
    include_page_breaks=True  # Tracks page numbers
)

# Page mapping is stored in metadata
metadata = {
    "parser": "unstructured",
    "page_map": [
        {"start": 0, "end": 1200, "page": 1, "element_type": "Title"},
        {"start": 1202, "end": 3400, "page": 1, "element_type": "NarrativeText"},
        {"start": 3402, "end": 5600, "page": 2, "element_type": "NarrativeText"}
    ],
    "total_pages": 15
}
```

### 2. Citation Extraction During Retrieval

When a query is processed, the API:

1. **Retrieves relevant context** from LightRAG
2. **Extracts chunk metadata** from storage
3. **Maps chunks to source documents** and pages
4. **Builds citation objects** with document names, page numbers, and locations

```python
# From lightrag_api_server.py
def extract_citations_from_context(context: str, working_dir: str) -> List[Citation]:
    # Load chunk and document metadata
    # Match context to chunks
    # Build citations with page information
    citations = [
        Citation(
            document="example.pdf",
            page=5,
            location="section 3",
            chunk_id="abc123"
        )
    ]
    return citations
```

### 3. Evidence Formatting

The API formats the evidence description to include citation information:

```
Retrieved and synthesized using hybrid search mode. 
Evidence from 3 source(s): Multi-Agent RAG paper.pdf (page 2), 
LightRAG documentation.md, Research guidelines.pdf (page 5)
```

## Usage Examples

### Example 1: Enterprise RAG for SDLC

**Query:**
```
"What are the benefits of multi-agent systems in software development?"
```

**Response (snippet):**
```json
{
  "answer": "Multi-agent systems in software development provide several benefits including specialized agents for different phases, improved coordination, and better handling of complex workflows...",
  "evidence_used": "Retrieved from 3 sources: RAG-Based AI Agents for Enterprise.pdf (page 5), Multi-Agent Approach.pdf (page 11), SDLC Automation.md",
  "citations": [
    {
      "document": "RAG-Based AI Agents for Enterprise.pdf",
      "page": 5,
      "location": "section 3",
      "chunk_id": "8fd2f858"
    },
    {
      "document": "Multi-Agent Approach.pdf",
      "page": 11,
      "location": "section 8",
      "chunk_id": "f9f4dddc"
    },
    {
      "document": "SDLC Automation.md",
      "page": null,
      "location": "section 1",
      "chunk_id": "06e66678"
    }
  ]
}
```

### Example 2: Research Paper Query

**Query:**
```
"Explain the dual-level retrieval paradigm in LightRAG"
```

**Response Citations:**
```json
{
  "citations": [
    {
      "document": "LIGHTRAG paper.pdf",
      "page": 3,
      "location": "section 2",
      "chunk_id": "0747de85"
    },
    {
      "document": "LIGHTRAG paper.pdf",
      "page": 4,
      "location": "section 2",
      "chunk_id": "69aa0eae"
    }
  ]
}
```

## Benefits

1. **Transparency**: Users can see exactly which sources were used
2. **Verification**: Easy to verify claims by checking source documents
3. **Academic Integrity**: Proper attribution of information
4. **Debugging**: Trace which chunks influenced the response
5. **Trust**: Builds confidence in AI-generated responses

## Best Practices

### For Custom GPT Integration

When integrating with Custom GPT, use the citations to:

1. **Display source references** in your responses:
   ```
   Based on research from "Multi-Agent RAG" (page 5), the system uses...
   ```

2. **Provide links** to source documents when available

3. **Format citations** in a scholarly style:
   ```
   According to the LightRAG documentation (section 3, page 2), 
   dual-level retrieval combines...
   ```

### For Enterprise Deployments

1. **Store full document paths** during ingestion for precise linking
2. **Implement access control** to respect document permissions
3. **Cache citation metadata** for faster responses
4. **Log citation usage** for audit trails
5. **Validate citations** against source documents periodically

## Limitations and Future Enhancements

### Current Limitations

- Page numbers are estimated for documents without explicit page metadata
- Line numbers are not yet tracked (future enhancement)
- Citation format is standardized (not customizable per use case)

### Planned Enhancements

1. **Precise line number tracking** for text documents
2. **Highlighting exact text spans** within source documents  
3. **Confidence scores** for individual citations
4. **Citation clustering** for multi-document synthesis
5. **Custom citation formats** (APA, MLA, Chicago, etc.)
6. **Interactive citations** with preview capabilities

## Testing Your Citations

To test the citation system:

```bash
# Start the API server
python lightrag_api_server.py

# Test with curl
curl -X POST http://localhost:8001/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is LightRAG?",
    "mode": "hybrid"
  }'

# Check the response for citations field
# Verify document names and page numbers
```

## Troubleshooting

### Citations Not Appearing

1. **Check document metadata**: Ensure documents were ingested with page tracking enabled

2. **Verify storage files**: Check that `kv_store_text_chunks.json` contains chunk data. 
   
   **ACTUAL LightRAG Storage Structure:**
   ```json
   {
     "chunk-xxxxx": {
       "tokens": 200,
       "content": "text content...",
       "chunk_order_index": 0,
       "full_doc_id": "doc-xxxxx",
       "file_path": "data/document.pdf",  ← Should NOT be "unknown_source"
       "llm_cache_list": [],
       "create_time": 1234567890,
       "update_time": 1234567890,
       "_id": "chunk-xxxxx"
     }
   }
   ```
   
   **⚠️ Common Issues:**
   - `file_path` is set to "unknown_source" → Documents ingested without proper path
   - No `page` or `section` fields → LightRAG doesn't store page info by default
   - No nested `metadata` object → LightRAG uses flat structure

3. **Review logs**: Look for warnings about citation extraction failures

### Incorrect Page Numbers

- Page numbers are estimated based on chunk position
- For PDFs, ensure they have page metadata (not scanned images without OCR)
- Consider re-ingesting with updated parser settings

### Missing Document Names

- If showing "Unknown Document", check the `file_path` field in chunks
- **Most common cause**: `file_path` is set to "unknown_source" 
- This happens when documents are ingested without proper file tracking

**To fix:**
```bash
source ~/.lightRAG_env/bin/activate

# Check current file_path values
python3 -c "
import json
with open('lightrag_storage/kv_store_text_chunks.json', 'r') as f:
    chunks = json.load(f)
    file_paths = set(c.get('file_path') for c in chunks.values())
    print('File paths found:', file_paths)
"

# If you see 'unknown_source', re-ingest with proper paths
python src/ingest.py --input data/your_document.pdf
```

**Note:** LightRAG uses a flat storage structure. Citation fields are directly on the chunk object, not in a nested `metadata` field:
```json
{
  "file_path": "data/document.pdf",  ← Direct field
  "chunk_order_index": 0,
  "content": "...",
  "full_doc_id": "doc-xxxxx"
}
```

### Verifying Citation Metadata

To check if your storage files have proper citation data:

```bash
# Activate virtual environment first
source ~/.lightRAG_env/bin/activate

# Inspect chunk storage structure
python3 -c "
import json
with open('lightrag_storage/kv_store_text_chunks.json', 'r') as f:
    chunks = json.load(f)
    first_chunk = next(iter(chunks.values()))
    
    print('Chunk fields:', list(first_chunk.keys()))
    print('File path:', first_chunk.get('file_path', 'NOT FOUND'))
    print('Chunk order:', first_chunk.get('chunk_order_index', 'NOT FOUND'))
    
    # Check citation readiness
    if first_chunk.get('file_path') == 'unknown_source':
        print('❌ WARNING: file_path is unknown_source')
        print('   Re-ingest documents with proper path tracking')
    else:
        print('✅ File path is tracked')
    
    if 'page' not in first_chunk:
        print('⚠️  NOTE: No page field (normal for LightRAG)')
        print('   Page info would need custom implementation')
"
```

**What you should see:**
- `file_path`: Should contain actual file path, NOT "unknown_source"
- `chunk_order_index`: Sequential chunk number within document
- `full_doc_id`: Links chunk to source document

**Current Limitation:** LightRAG's native storage doesn't include page numbers. To add page tracking, you need to extend the ingestion pipeline.

If citation fields are missing, re-ingest documents with:
```bash
source ~/.lightRAG_env/bin/activate
python src/ingest.py --input your_document.pdf
```

### Current Implementation Status

**✅ What's Working:**
- Document and chunk tracking via `full_doc_id` and `chunk_order_index`
- File path storage in flat structure (when properly ingested)
- Basic citation extraction from chunk locations
- Document identification via `full_doc_id`

**⚠️ What Needs Implementation:**
- Page number tracking in LightRAG storage (not included by default)
- Section/element type metadata (requires custom extension)
- Nested metadata structure (LightRAG uses flat structure by design)
- Real-time page mapping during document parsing

**Actual Storage Structure Found:**
```json
{
  "chunk-xxxxx": {
    "tokens": 200,
    "content": "chunk text...",
    "chunk_order_index": 0,
    "full_doc_id": "doc-xxxxx",
    "file_path": "unknown_source",  ← Currently set to this
    "llm_cache_list": [],
    "create_time": 1234567890,
    "update_time": 1234567890,
    "_id": "chunk-xxxxx"
  }
}
```

**To Add Page Tracking:**

Option 1: Extend LightRAG ingestion to store page info
```python
# Custom ingestion extension
chunk_with_page = {
    **chunk_data,
    'page': calculated_page_number,
    'section': section_index,
    'element_type': 'NarrativeText'
}
```

Option 2: Maintain a separate page mapping file
```json
{
  "doc-xxxxx": {
    "file_path": "data/document.pdf",
    "page_map": [
      {"chunk_order": 0, "page": 1, "char_start": 0, "char_end": 1200},
      {"chunk_order": 1, "page": 1, "char_start": 1200, "char_end": 2400},
      {"chunk_order": 2, "page": 2, "char_start": 2400, "char_end": 3600}
    ]
  }
}
```

## Support

For issues or questions about the citation system:
- Review the API logs for detailed error messages
- Check the LightRAG storage files for metadata completeness
- Consult the document parser documentation for ingestion options

---

Last Updated: February 2026
