# GitHub Copilot Instructions for LightRAG PoC

## Virtual Environment Activation

**CRITICAL**: This project uses a Python virtual environment located at `~/.lightRAG_env/`.

Before running ANY Python commands, scripts, or terminal operations in this workspace, you MUST:

```bash
source ~/.lightRAG_env/bin/activate
```

## When to Activate

Always activate the virtual environment when:
- Running Python scripts (e.g., `python src/ingest.py`, `python src/visualize.py`)
- Installing packages with pip
- Running API servers (`python lightrag_api_server.py`, `python api_server.py`)
- Executing query commands (`python lightrag/lightrag_query.py`)
- Running tests or debug scripts
- Any other Python-related terminal commands

## Example Usage Patterns

```bash
# Before running any script:
source ~/.lightRAG_env/bin/activate
python src/ingest.py --input data/vn_law_sample.txt

# Before starting servers:
source ~/.lightRAG_env/bin/activate
python lightrag_api_server.py

# Before querying:
source ~/.lightRAG_env/bin/activate
python lightrag/lightrag_query.py "What is Article 10?" --mode hybrid
```

## Project Context

This is a LightRAG (Lightweight Retrieval-Augmented Generation) Proof of Concept for Vietnamese legal document analysis that combines:
- Knowledge Graph (Neo4j)
- Vector search (FAISS)
- Document parsing (Unstructured.io + OCR)
- Entity extraction and relation detection

All Python dependencies are isolated in the `~/.lightRAG_env/` virtual environment.
