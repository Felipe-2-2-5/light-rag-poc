# Hybrid Document Parser Architecture

## System Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     INPUT DOCUMENTS                               │
│  PDF | Images | DOCX | PPTX | TXT | Scanned Documents            │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────┐
│              DOCUMENT PARSER (src/document_parser.py)             │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Step 1: File Type Detection                                │  │
│  │ • .txt → Direct read                                       │  │
│  │ • .pdf → Unstructured.io parser                           │  │
│  │ • .jpg/.png → Unstructured.io + OCR                       │  │
│  │ • .docx/.pptx → Unstructured.io                           │  │
│  └────────────────────────────────────────────────────────────┘  │
│                             │                                     │
│                             ↓                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Step 2: Parse with FREE Tools (Primary)                    │  │
│  │                                                             │  │
│  │  Unstructured.io Library:                                  │  │
│  │  • Layout-aware parsing                                    │  │
│  │  • Table detection & extraction                            │  │
│  │  • OCR support (Tesseract)                                 │  │
│  │  • Vietnamese language support                             │  │
│  │  • High-resolution strategy                                │  │
│  │                                                             │  │
│  │  Features:                                                  │  │
│  │  ✓ Text extraction with reading order                      │  │
│  │  ✓ Table structure recognition                             │  │
│  │  ✓ Page break detection                                    │  │
│  │  ✓ Element type identification                             │  │
│  └────────────────────────────────────────────────────────────┘  │
│                             │                                     │
│                             ↓                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Step 3: Quality Check                                       │  │
│  │                                                             │  │
│  │  Criteria:                                                  │  │
│  │  • Text length > 50 characters                             │  │
│  │  • Printable character ratio > 70%                         │  │
│  │  • No major extraction errors                              │  │
│  │                                                             │  │
│  │  Decision:                                                  │  │
│  │  ✅ Quality sufficient → Use free parser result            │  │
│  │  ❌ Quality insufficient → Trigger ADE fallback            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                             │                                     │
│              ┌──────────────┴──────────────┐                      │
│              ↓                             ↓                      │
│  ┌──────────────────────┐    ┌──────────────────────────────┐    │
│  │  ✅ QUALITY GOOD     │    │  ❌ QUALITY POOR / COMPLEX   │    │
│  │                      │    │                              │    │
│  │  Use: FREE parser    │    │  Fallback to: ADE API        │    │
│  │  Cost: $0            │    │  Cost: ~$0.03-0.10 per page  │    │
│  └──────────┬───────────┘    └──────────┬───────────────────┘    │
│             │                           │                         │
│             │                           ↓                         │
│             │         ┌────────────────────────────────────────┐  │
│             │         │ Step 4: ADE API (Optional)             │  │
│             │         │                                        │  │
│             │         │  Landing AI DPT-2 Model:               │  │
│             │         │  • 99.16% DocVQA accuracy              │  │
│             │         │  • Visual grounding (bounding boxes)   │  │
│             │         │  • Advanced layout understanding       │  │
│             │         │  • Confidence scores                   │  │
│             │         │  • Enterprise-grade accuracy           │  │
│             │         └────────────┬───────────────────────────┘  │
│             │                      │                              │
│             └──────────────────────┘                              │
│                             │                                     │
└─────────────────────────────┼─────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                    STRUCTURED OUTPUT                              │
│                                                                   │
│  Text Content:                                                    │
│  • Extracted text with preserved structure                       │
│  • Reading order maintained                                      │
│  • Tables formatted as text/markdown                             │
│                                                                   │
│  Metadata:                                                        │
│  • Parser used (free/ade/text)                                   │
│  • Number of elements extracted                                  │
│  • Element types (Title, Text, Table, etc.)                      │
│  • Quality metrics                                               │
│  • Visual grounding data (if ADE used)                           │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────┐
│              INGEST PIPELINE (src/ingest.py)                      │
│                                                                   │
│  1. Chunk text (with overlap)                                    │
│  2. Generate embeddings (SentenceTransformers)                   │
│  3. Store in FAISS vector store                                  │
│  4. Extract entities (Vietnamese legal NER)                      │
│  5. Build knowledge graph (Neo4j)                                │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────┐
│                    FINAL OUTPUTS                                  │
│                                                                   │
│  outputs/faiss.index     → Vector embeddings                     │
│  outputs/meta.json       → Chunk metadata                        │
│  outputs/entities.json   → Extracted entities                    │
│  outputs/relations.json  → Entity relationships                  │
│  Neo4j Database          → Knowledge graph                       │
└──────────────────────────────────────────────────────────────────┘
```

## Cost Analysis

### Scenario: Processing 1000 Pages per Month

| Strategy | Free Pages | ADE Pages | Monthly Cost | Notes |
|----------|-----------|-----------|--------------|-------|
| **Free Only** | 1000 (100%) | 0 | $0 | May miss complex layouts |
| **ADE Only** | 0 | 1000 (100%) | $30-100 | Highest accuracy, highest cost |
| **Hybrid (90/10)** | 900 (90%) | 100 (10%) | $3-10 | **RECOMMENDED** - Best balance |
| **Hybrid (95/5)** | 950 (95%) | 50 (5%) | $1.5-5 | Good for simple documents |

### Break-Even Analysis

- **Free parser quality**: ~95% accuracy for typical documents
- **ADE quality**: ~99% accuracy for all documents
- **Cost difference**: $0 vs $0.03-0.10 per page
- **Recommendation**: Use hybrid with quality checks

## Parser Comparison

| Feature | Free (Unstructured.io) | ADE (Landing AI) |
|---------|----------------------|------------------|
| **Accuracy** | ⭐⭐⭐⭐ (95%) | ⭐⭐⭐⭐⭐ (99.16%) |
| **Speed** | Fast (30-60s/100pg) | Fast (20-40s/100pg) |
| **Cost** | $0 | $3-10/1000 pages |
| **Layout Understanding** | ✅ Good | ✅ Excellent |
| **Table Extraction** | ✅ Good | ✅ Excellent |
| **Visual Grounding** | ❌ No | ✅ Yes (bounding boxes) |
| **OCR Quality** | ✅ Good | ✅ Excellent |
| **Vietnamese Support** | ✅ Yes | ✅ Yes |
| **API Limits** | None | Rate limited by plan |
| **Offline Usage** | ✅ Yes | ❌ No (API only) |
| **Complex Layouts** | ⚠️ May struggle | ✅ Handles well |

## Decision Tree

```
Start
  │
  ├─→ Simple document type (.txt)?
  │   └─→ Use direct text read (instant, $0)
  │
  ├─→ Standard PDF with text?
  │   └─→ Try Unstructured.io
  │       ├─→ Good quality? → Use result ($0)
  │       └─→ Poor quality? → Fallback to ADE ($)
  │
  ├─→ Scanned/image-based PDF?
  │   └─→ Try Unstructured.io + OCR
  │       ├─→ Good quality? → Use result ($0)
  │       └─→ Poor quality? → Fallback to ADE ($)
  │
  └─→ Complex layout (tables, charts, forms)?
      └─→ Try Unstructured.io
          ├─→ Good quality? → Use result ($0)
          └─→ Poor quality? → Fallback to ADE ($)
```

## Quality Check Algorithm

```python
def is_quality_sufficient(text, metadata):
    """
    Determine if free parser output is good enough
    """
    # Check 1: Minimum text length
    if len(text.strip()) < 50:
        return False  # Too short, likely failed
    
    # Check 2: Character quality
    printable_ratio = sum(c.isprintable() or c.isspace() 
                         for c in text) / len(text)
    if printable_ratio < 0.7:
        return False  # Too many garbled characters
    
    # Check 3: Element detection (if metadata available)
    if metadata and metadata.get('num_elements', 0) == 0:
        return False  # Nothing detected
    
    return True  # Quality is sufficient
```

## Usage Tracking

The system logs every parse operation:

```json
{
  "timestamp": "2026-01-17T10:30:45",
  "file": "LIGHTRAG.pdf",
  "parser_used": "free",
  "text_length": 15234,
  "processing_time": 32.5,
  "quality_score": 0.98,
  "cost": 0.0
}
```

This enables:
- Cost monitoring
- Quality analysis
- Performance optimization
- Usage pattern identification

## Integration Points

```
External APIs:
  ├─→ Landing AI ADE (optional)
  │   • API endpoint: https://api.landing.ai/v1/parse
  │   • Authentication: Bearer token
  │   • Rate limits: Based on plan
  │
Internal Components:
  ├─→ Unstructured.io (local)
  ├─→ Tesseract OCR (local)
  ├─→ FAISS vector store
  ├─→ Neo4j knowledge graph
  └─→ SentenceTransformers embeddings
```

## Deployment Options

1. **Development (Free Only)**
   - No API keys needed
   - All processing local
   - Good for testing

2. **Production (Hybrid)**
   - ADE API key configured
   - Automatic fallback
   - Cost optimized

3. **Enterprise (Flexible)**
   - Multiple parser options
   - Custom quality thresholds
   - Advanced monitoring
