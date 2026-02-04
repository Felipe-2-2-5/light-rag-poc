# LightRAG Integration - Optimized Pipeline

## Architecture

This implementation combines the best of both worlds:

### 1. **Document Parsing** (Unstructured.io)
- **Primary**: Free Unstructured.io parser with high-res strategy
- **Fallback**: Landing AI ADE API for complex documents
- **Features**:
  - Multi-language support (Vietnamese + English)
  - OCR for scanned documents (Tesseract)
  - Table extraction
  - High-quality text extraction

### 2. **Knowledge Graph & Embeddings** (LightRAG)
- **Entity Extraction**: LLM-powered entity recognition
- **Relationship Extraction**: Automatic relationship detection
- **Multi-Level Indexing**:
  - **Local**: Entity-level embeddings for specific queries
  - **Global**: Document-level embeddings for broad queries
  - **Hybrid**: Combined approach for best results
- **Graph Database**: NetworkX-based graph storage
- **Vector Store**: Nano-VectorDB with cosine similarity

### 3. **LLM & Embeddings** (Google Gemini)
- **LLM**: Gemini 2.5 Flash for entity extraction and generation
- **Embeddings**: text-embedding-004 (768 dimensions)
- **Cache**: LLM response caching for efficiency

## Components

```
Document (PDF/TXT)
    ↓
[DocumentParser - Unstructured.io]
    ├─ High-res strategy
    ├─ OCR with Tesseract
    ├─ Multi-language (vi, en)
    └─ Output: Clean text
    ↓
[LightRAG - Entity & Graph Builder]
    ├─ Chunking (smart splits)
    ├─ Entity extraction (LLM)
    ├─ Relationship detection (LLM)
    ├─ Vector embeddings
    └─ Graph construction
    ↓
[Storage]
    ├─ graph_chunk_entity_relation.graphml (NetworkX)
    ├─ vdb_entities.json (Entity embeddings)
    ├─ vdb_relationships.json (Relation embeddings)
    ├─ vdb_chunks.json (Chunk embeddings)
    └─ kv_store_*.json (Metadata)
    ↓
[Query Modes]
    ├─ naive: Simple vector similarity
    ├─ local: Entity-focused retrieval
    ├─ global: Community-level retrieval
    └─ hybrid: Combined approach (best accuracy)
```

## Usage

### 1. Ingest Documents

```bash
# Activate environment
source ~/.lightRAG_env/bin/activate

# Ingest a document
python lightrag_ingest.py --input data/LIGHTRAG.pdf --working-dir ./lightrag_storage

# Force re-ingestion
python lightrag_ingest.py --input data/document.pdf --working-dir ./storage --force

# Disable ADE fallback (free parsers only)
python lightrag_ingest.py --input data/doc.pdf --no-ade-fallback
```

### 2. Query the System

```bash
# Single query
python lightrag_query.py "What is LightRAG?" --mode hybrid

# Interactive mode
python lightrag_query.py --interactive

# Specify query mode
python lightrag_query.py "Your question" --mode local   # Entity-focused
python lightrag_query.py "Your question" --mode global  # Community-level
python lightrag_query.py "Your question" --mode hybrid  # Best accuracy
```

### 3. Query Modes

- **naive**: Simple vector similarity search (fastest, least context)
- **local**: Entity-focused retrieval (good for specific questions)
- **global**: Community/topic-level retrieval (good for broad questions)
- **hybrid**: Combines local + global (best accuracy, recommended)

## Performance

### Document Parsing
- **LIGHTRAG.pdf**: 67,630 characters, 228 elements extracted
- **Quality**: 100% printable characters
- **Speed**: ~30 seconds for 16-page PDF with OCR

### Knowledge Graph
- **Entities**: Auto-extracted with LLM
- **Relationships**: Auto-detected between entities
- **Storage**: ~368KB for sample document
- **Embeddings**: 768-dimensional vectors (Gemini)

### Query Performance
- **Initialization**: ~2 seconds (load graph + vectors)
- **Query Time**: ~3-5 seconds (embedding + retrieval + generation)
- **Cache**: LLM responses cached for repeated queries

## Configuration

### Environment Variables (.env)

```bash
# LLM Provider
LLM_PROVIDER=gemini              # or "openai"

# Google Gemini
GOOGLE_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.5-flash

# OpenAI (alternative)
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4o-mini

# Optional: ADE API for complex documents
ADE_API_KEY=your-ade-key
```

### Parser Options

The `DocumentParser` tries parsers in this order:
1. **Unstructured.io** (free, high quality)
   - Strategy: `hi_res` for better accuracy
   - Languages: Vietnamese + English
   - OCR: Tesseract-based
   
2. **ADE API** (paid fallback)
   - Used only if free parser fails
   - Requires `ADE_API_KEY`

## Files Structure

```
lightrag_storage/
├── graph_chunk_entity_relation.graphml  # Main knowledge graph
├── vdb_entities.json                    # Entity embeddings
├── vdb_relationships.json               # Relationship embeddings
├── vdb_chunks.json                      # Text chunk embeddings
├── kv_store_full_docs.json              # Original documents
├── kv_store_text_chunks.json            # Text chunks
├── kv_store_full_entities.json          # Entity metadata
├── kv_store_full_relations.json         # Relationship metadata
├── kv_store_entity_chunks.json          # Entity-chunk mappings
├── kv_store_relation_chunks.json        # Relation-chunk mappings
├── kv_store_llm_response_cache.json     # LLM cache
└── kv_store_doc_status.json             # Document status
```

## Advantages over Previous Approach

### Before (Custom Implementation)
- ❌ Manual entity extraction
- ❌ Manual relationship detection
- ❌ Single-level indexing
- ❌ Fixed chunking strategy
- ❌ Manual graph construction
- ❌ Simple vector search only

### After (LightRAG Integration)
- ✅ **LLM-powered entity extraction** (smarter)
- ✅ **Automatic relationship detection**
- ✅ **Multi-level indexing** (local + global + hybrid)
- ✅ **Smart chunking** with overlap
- ✅ **Automatic graph construction**
- ✅ **Advanced retrieval** with graph traversal
- ✅ **Community detection** for global queries
- ✅ **Query optimization** with caching

## Query Examples

```python
# Vietnamese law query
python lightrag_query.py "Điều 1 quy định gì về phạm vi điều chỉnh?" --mode hybrid

# Technical query
python lightrag_query.py "How does LightRAG work?" --mode hybrid

# Broad query (use global mode)
python lightrag_query.py "What are the main themes?" --mode global

# Specific entity query (use local mode)
python lightrag_query.py "Who are the authors?" --mode local
```

## Troubleshooting

### No results / Low accuracy
- Use `--mode hybrid` for best results
- Check if entities were extracted: `ls -lh lightrag_storage/`
- Verify embeddings: check `vdb_*.json` files are not empty

### Parsing errors
- Ensure unstructured is installed: `pip install 'unstructured[pdf]'`
- For scanned PDFs, install OCR: `sudo apt-get install tesseract-ocr`
- Set `ADE_API_KEY` for fallback to paid parser

### Out of memory
- Reduce batch size in LightRAG config
- Process smaller documents
- Use lower resolution for OCR

## Next Steps

1. **Fine-tune chunking**: Adjust chunk size/overlap for your domain
2. **Custom entities**: Add domain-specific entity types
3. **Reranking**: Add rerank model for better precision
4. **Visualization**: Use `graph.html` to visualize knowledge graph
5. **Multi-document**: Ingest multiple documents into same storage
6. **Incremental updates**: Add new documents without full rebuild

## References

- **LightRAG**: https://github.com/HKUDS/LightRAG
- **Unstructured.io**: https://unstructured.io/
- **Google Gemini**: https://ai.google.dev/
