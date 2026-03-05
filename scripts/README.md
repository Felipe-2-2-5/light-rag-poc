# Scripts

Utility and debug scripts for development and maintenance.

## Usage

All scripts should be run from the **project root**:

```bash
source ~/.lightRAG_env/bin/activate

# Debug embedding similarity
python scripts/debug_embeddings.py

# Debug FAISS vector search
python scripts/debug_search.py

# Fix embedding metadata after ingestion
python scripts/fix_embedding_metadata.py

# Fix storage citations (add file paths / page numbers)
python scripts/fix_storage_citations.py
```

## Script Descriptions

| Script | Purpose |
|---|---|
| `debug_embeddings.py` | Debug Gemini embedding similarity for Vietnamese queries |
| `debug_search.py` | Inspect FAISS vector search results |
| `fix_embedding_metadata.py` | Patch metadata in existing FAISS index after re-ingestion |
| `fix_storage_citations.py` | Enrich LightRAG storage files with file paths and page estimates |
