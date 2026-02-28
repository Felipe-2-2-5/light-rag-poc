# RAG Comparison Guide - Traditional vs LightRAG

This project now contains **TWO RAG implementations** for comparison and demonstration purposes:

## 🔵 Traditional/Custom Graph RAG (Original)

**What**: Your original custom implementation combining FAISS + Neo4j + LangChain

**Script**: `python lightrag/query_rag.py --interactive`

**Features**:
- Custom entity extraction with regex patterns
- Manual Neo4j graph construction
- LangChain for RAG pipeline
- FAISS vector search
- Good baseline performance

**Storage**:
- Vector: `outputs/faiss.index`
- Graph: Neo4j database (custom schema)
- Entities: `outputs/entities.json`
- Relations: `outputs/relations.json`

---

## 🟢 LightRAG (Official Implementation)

**What**: Official LightRAG library with advanced entity extraction and multi-level indexing

**Script**: `python lightrag/lightrag_query.py --interactive`

**Features**:
- LLM-based entity/relation extraction (higher accuracy)
- Automatic multi-level indexing
- Hybrid query modes (local/global/hybrid/mix)
- RAG-Anything support (multimodal)
- Production-ready

**Storage**:
- All-in-one: `lightrag_storage/`
- Graph: `graph_chunk_entity_relation.graphml`
- Vectors: `vdb_*.json`
- Chunks: `kv_store_*.json`

---

## 📊 Side-by-Side Comparison

### Setup

```bash
# 1. Traditional RAG (uses old data in outputs/)
python lightrag/query_rag.py --interactive

# 2. LightRAG (uses new data in lightrag_storage/)
python lightrag/lightrag_query.py --interactive
```

### Query the Same Question

```bash
QUESTION="What are the main components of multi-agent RAG systems?"

# Traditional RAG
echo "Traditional RAG:"
python lightrag/query_rag.py "$QUESTION"

echo ""
echo "LightRAG:"
python lightrag/lightrag_query.py "$QUESTION" --mode hybrid
```

### Comparison Metrics

| Aspect | Traditional RAG | LightRAG | Winner |
|--------|----------------|----------|---------|
| **Entity Extraction** | Regex patterns | LLM-based | 🟢 LightRAG |
| **Accuracy** | Good | Better | 🟢 LightRAG |
| **Graph Structure** | Manual schema | Auto-generated | 🟢 LightRAG |
| **Query Modes** | Basic search | 5 modes (local/global/hybrid/mix/naive) | 🟢 LightRAG |
| **Setup Complexity** | Manual steps | Integrated | 🟢 LightRAG |
| **Multimodal Support** | ❌ Text only | ✅ Tables/images/formulas | 🟢 LightRAG |
| **Understanding** | Good for learning | Production-ready | 🔵 Both valuable |

---

## 🧪 Demonstration Workflow

### Step 1: Prepare Both Systems

**Traditional RAG (if not already done):**
```bash
# Uses old pipeline
python src/ingest.py --input data/vn_law_sample.txt
python src/kg_builder.py
```

**LightRAG:**
```bash
# Single command, better results
python lightrag/lightrag_ingest.py \
  --input data/LIGHTRAG.pdf \
  --use-rag-anything
```

### Step 2: Run Comparison Script

Create `compare_rag_systems.sh`:

```bash
#!/bin/bash
# Compare Traditional vs LightRAG

QUESTIONS=(
  "What is LightRAG?"
  "Explain the multi-agent architecture"
  "What are the main components?"
)

for Q in "${QUESTIONS[@]}"; do
  echo ""
  echo "========================================="
  echo "Question: $Q"
  echo "========================================="
  
  echo ""
  echo "--- Traditional RAG ---"
  python lightrag/query_rag.py "$Q" 2>/dev/null | head -n 20
  
  echo ""
  echo "--- LightRAG (Hybrid Mode) ---"
  python lightrag/lightrag_query.py "$Q" --mode hybrid 2>/dev/null | head -n 20
  
  echo ""
  echo "--- LightRAG (Mix Mode - KG+Vector) ---"
  python lightrag/lightrag_query.py "$Q" --mode mix 2>/dev/null | head -n 20
  
  echo ""
  read -p "Press Enter for next question..."
done
```

### Step 3: Analyze Results

Compare the outputs focusing on:

1. **Answer Quality**: Which gives more comprehensive answers?
2. **Entity Recognition**: Which identifies more relevant entities?
3. **Relationship Understanding**: Which captures better relationships?
4. **Context Relevance**: Which retrieves more relevant context?

---

## 🎯 Use Cases for Each

### Use Traditional RAG When:
- ✅ Learning how RAG systems work
- ✅ Teaching Graph RAG concepts
- ✅ Simple, controlled demonstrations
- ✅ You need full control over every component

### Use LightRAG When:
- ✅ Production applications
- ✅ Complex academic documents (with RAG-Anything)
- ✅ Need high accuracy
- ✅ Want advanced query modes
- ✅ Processing large document collections

---

## 🔄 Migration Path

If you want to gradually migrate from Traditional to LightRAG:

### Phase 1: Keep Both (Current State)
```bash
# Traditional for baseline
python lightrag/query_rag.py --interactive

# LightRAG for testing
python lightrag/lightrag_query.py --interactive
```

### Phase 2: Parallel Evaluation
```bash
# Same data in both systems
# Compare outputs
# Measure improvements
```

### Phase 3: Full Migration
```bash
# Once satisfied with LightRAG
# Use it as primary
# Keep traditional for reference
```

---

## 📈 Showcase Script

Create `showcase_enhancement.py`:

```python
#!/usr/bin/env python3
"""
Showcase the enhancement from Traditional RAG to LightRAG
"""

import subprocess
import time

def query_both(question):
    """Query both systems and compare"""
    print(f"\n{'='*80}")
    print(f"Question: {question}")
    print(f"{'='*80}\n")
    
    # Traditional RAG
    print("🔵 TRADITIONAL RAG (Custom Implementation)")
    print("-" * 80)
    start = time.time()
    result1 = subprocess.run(
        ["python", "lightrag/query_rag.py", question],
        capture_output=True,
        text=True
    )
    time1 = time.time() - start
    print(result1.stdout[:500])
    print(f"\nTime: {time1:.2f}s")
    
    # LightRAG
    print("\n🟢 LIGHTRAG (Official Implementation)")
    print("-" * 80)
    start = time.time()
    result2 = subprocess.run(
        ["python", "lightrag/lightrag_query.py", question, "--mode", "hybrid"],
        capture_output=True,
        text=True
    )
    time2 = time.time() - start
    print(result2.stdout[:500])
    print(f"\nTime: {time2:.2f}s")
    
    # Summary
    print(f"\n{'='*80}")
    print("COMPARISON SUMMARY:")
    print(f"  Traditional RAG: {time1:.2f}s")
    print(f"  LightRAG: {time2:.2f}s")
    print(f"  Speed: {((time1-time2)/time1*100):+.1f}%")
    print(f"{'='*80}\n")

# Demo questions
questions = [
    "What is LightRAG?",
    "Explain the multi-agent architecture",
    "What evaluation metrics are used?"
]

for q in questions:
    query_both(q)
    input("\nPress Enter to continue...")
```

---

## 💡 Presentation Tips

When showcasing the enhancement:

1. **Start with Traditional**: Show it works well
2. **Highlight Limitations**: Manual entity extraction, single query mode
3. **Introduce LightRAG**: Show same question, better answer
4. **Demonstrate Features**: Multiple query modes, multimodal support
5. **Show Metrics**: Entity count, relationship richness, answer quality

---

## 📚 Documentation

- Traditional RAG: See [2_BUILD_COMPLETE_LANG_CHAIN.md](2_BUILD_COMPLETE_LANG_CHAIN.md)
- LightRAG: See [RAG_ANYTHING_MIGRATION.md](RAG_ANYTHING_MIGRATION.md)
- Scripts: See [SCRIPT_REFERENCE.md](SCRIPT_REFERENCE.md)

---

## ✅ Quick Reference

```bash
# Traditional RAG
python lightrag/query_rag.py --interactive
python lightrag/query_rag.py "Your question"

# LightRAG
python lightrag/lightrag_query.py --interactive
python lightrag/lightrag_query.py "Your question" --mode hybrid

# Compare parsers
python compare_parsers.py data/LIGHTRAG.pdf

# Full migration
./migrate_to_rag_anything.sh
```

**Remember**: Both implementations are valuable - Traditional for understanding, LightRAG for production!
