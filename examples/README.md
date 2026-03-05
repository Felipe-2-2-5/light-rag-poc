# Examples

Standalone FastAPI example demonstrating hybrid (vector + graph) retrieval.

## Usage

Run from the **project root**:

```bash
source ~/.lightRAG_env/bin/activate
uvicorn examples.api_example:app --reload
```

Then open the interactive docs at http://localhost:8000/docs.

> **Note**: `api_example.py` is an illustrative skeleton. For production use,
> see `api_server.py` (custom RAG) or `lightrag_api_server.py` (LightRAG).
