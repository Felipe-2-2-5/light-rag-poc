# Tests

Standalone test scripts for the LightRAG PoC components.

## Running Tests

Each test script can be executed from the **project root**:

```bash
# Activate venv first
source ~/.lightRAG_env/bin/activate

# Run individual test scripts
python tests/test_confidence_scoring.py
python tests/test_evaluation_metrics.py
python tests/test_graph_rag.py
python tests/test_parsers.py
python tests/test_lightrag_api.py   # requires lightrag_api_server running
python tests/test_custom_gpt_api.py # requires api_server running
```

## Test Coverage

| Script | Component Tested |
|---|---|
| `test_confidence_scoring.py` | `src/confidence_scorer.py` |
| `test_evaluation_metrics.py` | `src/evaluation_metrics.py` |
| `test_graph_rag.py` | `src/graph_rag.py`, Neo4j, FAISS |
| `test_parsers.py` | `src/document_parser.py` |
| `test_lightrag_api.py` | `lightrag_api_server.py` REST endpoints |
| `test_custom_gpt_api.py` | `api_server.py` REST endpoints |
