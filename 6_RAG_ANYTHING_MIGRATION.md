# RAG-Anything Migration Guide

Your project has been upgraded to support **RAG-Anything multimodal parsing** while maintaining backward compatibility with the classic text extraction approach.

## 📊 Your Use Case

Based on your data folder containing 12 academic PDFs (MA-RAG, DO-RAG, LightRAG, Agent Design Patterns, etc.), you will benefit from RAG-Anything because these documents likely contain:

- ✅ **System architecture diagrams** (multi-agent flows, RAG pipelines)
- ✅ **Comparison tables** (algorithm performance, evaluation metrics)
- ✅ **Mathematical formulas** (loss functions, optimization equations)
- ✅ **Charts and graphs** (experimental results)

---

## 🚀 Quick Start

### 1. Install RAG-Anything

```bash
# Activate your virtual environment first
source ~/.lightRAG_env/bin/activate

# Install RAG-Anything
pip install raganything
```

### 2. Compare Parsers (Recommended First Step)

Test both parsers on one of your PDFs to see the difference:

```bash
python compare_parsers.py data/LIGHTRAG.pdf
```

This will show you:
- Content extraction quality
- Tables/images/formulas detected
- Size comparison
- Recommendations

### 3. Ingest with RAG-Anything

Once satisfied with the comparison, ingest your PDFs:

```bash
# Single file with multimodal parsing
python lightrag/lightrag_ingest.py \
  --input data/LIGHTRAG.pdf \
  --use-rag-anything

# Multiple files
for pdf in data/*.pdf; do
  python lightrag/lightrag_ingest.py \
    --input "$pdf" \
    --use-rag-anything \
    --working-dir "./lightrag_storage"
done
```

---

## 🔄 Migration Options

### Option 1: Fresh Start (Recommended)

1. **Backup existing storage** (if any):
   ```bash
   mv lightrag_storage lightrag_storage_backup_$(date +%Y%m%d)
   ```

2. **Re-ingest with RAG-Anything**:
   ```bash
   python lightrag/lightrag_ingest.py \
     --input data/LIGHTRAG.pdf \
     --use-rag-anything \
     --force
   ```

### Option 2: Side-by-Side Comparison

Keep both versions in separate directories:

```bash
# Classic parser
python lightrag/lightrag_ingest.py \
  --input data/LIGHTRAG.pdf \
  --working-dir ./lightrag_classic

# RAG-Anything parser
python lightrag/lightrag_ingest.py \
  --input data/LIGHTRAG.pdf \
  --use-rag-anything \
  --working-dir ./lightrag_multimodal
```

Then compare query results from both.

### Option 3: Hybrid Approach

Use RAG-Anything for complex PDFs, classic for text files:

```bash
# For PDF files with diagrams/tables
python lightrag/lightrag_ingest.py \
  --input data/MA-RAG.pdf \
  --use-rag-anything

# For simple text/markdown files
python lightrag/lightrag_ingest.py \
  --input data/vn_law_sample.txt
```

---

## 📈 What Changes with RAG-Anything?

### Before (Classic Parser)
```
System Architecture
The proposed MA-RAG system consists of multiple agents.
[Table content flattened to text - structure lost]
Performance: 85% accuracy
```

### After (RAG-Anything)
```
System Architecture
The proposed MA-RAG system consists of multiple agents.

[TABLES]
Table 1:
| Model      | Accuracy | F1-Score | Latency |
|------------|----------|----------|---------|
| MA-RAG     | 85%      | 0.82     | 120ms   |
| DO-RAG     | 83%      | 0.80     | 150ms   |

[IMAGES/DIAGRAMS]
Figure 1: Multi-agent system architecture showing Query Agent, 
Retrieval Agent, and Generation Agent with bidirectional 
communication flows.

[FORMULAS]
Formula 1: Loss = α·L_retrieval + β·L_generation
```

---

## 🧪 Evaluation Checklist

Since you mentioned you haven't evaluated current ingestion results, here's a systematic approach:

### Step 1: Compare Parsers
```bash
# Run comparison on all your PDFs
python compare_parsers.py data/*.pdf > parser_comparison.txt
```

### Step 2: Test Sample Queries

Create a test query script:

```bash
# Test with classic parser storage
python lightrag/lightrag_query.py \
  "Explain the multi-agent architecture in MA-RAG" \
  --working-dir ./lightrag_classic \
  --mode hybrid

# Test with RAG-Anything storage
python lightrag/lightrag_query.py \
  "Explain the multi-agent architecture in MA-RAG" \
  --working-dir ./lightrag_multimodal \
  --mode hybrid
```

### Step 3: Check Knowledge Graph Quality

After ingestion, inspect Neo4j:

```cypher
// Check entity types extracted
MATCH (e:LightRAGEntity)
RETURN DISTINCT e.entity_type, COUNT(*) as count
ORDER BY count DESC

// Check if table/diagram entities were created
MATCH (e:LightRAGEntity)
WHERE e.description CONTAINS "Table" OR e.description CONTAINS "Figure"
RETURN e LIMIT 10

// Check relationship richness
MATCH (e1:LightRAGEntity)-[r:RELATED_TO]->(e2:LightRAGEntity)
RETURN e1.name, r.description, e2.name LIMIT 25
```

### Step 4: Quality Metrics

Compare these aspects:

| Metric | Classic Parser | RAG-Anything | Winner |
|--------|---------------|--------------|---------|
| Entities extracted | ? | ? | ? |
| Relationships found | ? | ? | ? |
| Table data preserved | ❌ | ✅ | RAG-Anything |
| Diagram understanding | ❌ | ✅ | RAG-Anything |
| Formula extraction | ❌ | ✅ | RAG-Anything |
| Query answer quality | ? | ? | ? |
| Processing time | ? | ? | ? |

---

## 🎯 Recommended Workflow for Your Academic PDFs

```bash
#!/bin/bash
# Automated ingestion workflow

# 1. Activate environment
source ~/.lightRAG_env/bin/activate

# 2. Compare parsers (first run only)
echo "Comparing parsers on sample PDF..."
python compare_parsers.py data/LIGHTRAG.pdf

# 3. Backup existing storage
if [ -d "lightrag_storage" ]; then
  echo "Backing up existing storage..."
  mv lightrag_storage lightrag_storage_backup_$(date +%Y%m%d_%H%M%S)
fi

# 4. Ingest all PDFs with RAG-Anything
echo "Ingesting PDFs with multimodal parser..."
for pdf in data/*.pdf; do
  echo "Processing: $pdf"
  python lightrag/lightrag_ingest.py \
    --input "$pdf" \
    --use-rag-anything \
    --working-dir "./lightrag_storage" \
    --force
done

# 5. Test query
echo ""
echo "Testing query..."
python lightrag/lightrag_query.py \
  "What are the key differences between MA-RAG and DO-RAG architectures?" \
  --mode hybrid

echo ""
echo "✓ Migration complete!"
echo "Check Neo4j at http://localhost:7474"
```

Save this as `migrate_to_rag_anything.sh` and run:
```bash
chmod +x migrate_to_rag_anything.sh
./migrate_to_rag_anything.sh
```

---

## 🔍 Troubleshooting

### Dependency Conflicts (Expected)

When installing RAG-Anything, you may see dependency conflict warnings like:
```
pdfplumber requires pdfminer.six==20221105, but you have pdfminer-six 20260107
unstructured-inference requires onnxruntime<1.16, but you have onnxruntime 1.23.2
```

**These are warnings, not errors!** RAG-Anything will work despite these conflicts. The newer versions are needed for multimodal features. If you encounter actual runtime errors:

```bash
# Option 1: Use RAG-Anything exclusively (recommended)
# The newer versions are compatible with your use case

# Option 2: Create separate environments (if conflicts cause issues)
# Classic parser environment
python -m venv ~/.lightRAG_classic_env
source ~/.lightRAG_classic_env/bin/activate
pip install -r requirements.txt  # Without raganything

# RAG-Anything environment  
python -m venv ~/.lightRAG_multimodal_env
source ~/.lightRAG_multimodal_env/bin/activate
pip install raganything
```

### RAG-Anything Installation Issues

```bash
# If pip install raganything fails, try:
pip install raganything --no-cache-dir

# Or install from source:
git clone https://github.com/HKUDS/RAG-Anything.git
cd RAG-Anything
pip install -e .
```

### Import Errors

If you see `ImportError: cannot import name 'DocumentParser' from 'raganything'`:

```bash
# Check installation
pip show raganything

# Reinstall
pip uninstall raganything
pip install raganything
```

### Performance Issues

If RAG-Anything is slow:

1. **Process PDFs in batches**
2. **Use GPU acceleration** (if available)
3. **Reduce concurrent parsing**

---

## 📚 Next Steps

1. ✅ **Run comparison**: `python compare_parsers.py data/LIGHTRAG.pdf`
2. ✅ **Install RAG-Anything**: `pip install raganything`
3. ✅ **Ingest with multimodal**: Use `--use-rag-anything` flag
4. ✅ **Evaluate results**: Compare query quality
5. ✅ **Document findings**: Track what works better

---

## 💡 Pro Tips

1. **Always compare first** - Run `compare_parsers.py` before full migration
2. **Keep backups** - Storage directories are easy to recreate
3. **Test queries** - Quality matters more than extraction completeness
4. **Monitor Neo4j** - Check if entities make sense
5. **Use hybrid mode** - Best results for academic papers

---

## 📞 Support

If you encounter issues:
1. Check the comparison output: `python compare_parsers.py FILE`
2. Review extraction logs in the terminal
3. Inspect Neo4j browser for entity quality
4. Compare with classic parser results

Remember: **RAG-Anything is optional**. If classic parsing works well for your use case, you can continue using it. The goal is better results, not just more features!
