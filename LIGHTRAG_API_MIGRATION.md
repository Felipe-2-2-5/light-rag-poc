# LightRAG API Migration Guide

## Problem Summary

Your Custom GPT was calling the **old API server** (`api_server.py`) which uses FAISS + Neo4j, but the documents about "Internal Knowledge Navigator" were in the **new LightRAG system** (`lightrag_storage/`).

### Result:
- ❌ **Old API** (`api_server.py` on port 8000): "The retrieved evidence does not provide information..."
- ✅ **New LightRAG API** (`lightrag_api_server.py` on port 8001): Full accurate answer with references

## Solution

I created a new FastAPI server (`lightrag_api_server.py`) that uses **LightRAG** instead of the old FAISS+Neo4j system.

## Key Differences

| Feature | Old API (port 8000) | New LightRAG API (port 8001) |
|---------|-------------------|--------------------------|
| **Backend** | FAISS + Neo4j | LightRAG |
| **Storage** | `outputs/` folder | `lightrag_storage/` folder |
| **Documents** | Old ingestion | Current documents (5 docs, 24 chunks) |
| **Search Modes** | Vector + Graph | naive, local, global, hybrid |
| **Synthesis** | Manual | LightRAG built-in |

## Files Created

1. **`lightrag_api_server.py`** - New FastAPI server using LightRAG
2. **`start_lightrag_api.sh`** - Startup script
3. **`test_lightrag_api.py`** - Test suite
4. **`custom-gpt/openapi-schema-lightrag.yaml`** - Updated OpenAPI schema

## Quick Test

The new API is currently running on **port 8001**. Test it:

```bash
# Health check
curl http://localhost:8001/health

# Test query
curl -X POST http://localhost:8001/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Internal Knowledge Navigator platform purpose and rules",
    "mode": "hybrid"
  }'
```

## Update Your Custom GPT

### Step 1: Expose the new API via ngrok

```bash
# If you have ngrok running on port 8000, stop it first
pkill ngrok

# Start ngrok for the new API on port 8001
ngrok http 8001
```

### Step 2: Update the OpenAPI schema

1. Open `custom-gpt/openapi-schema-lightrag.yaml`
2. Update the server URL on line 27:
   ```yaml
   servers:
     - url: https://YOUR-NEW-NGROK-URL.ngrok-free.app
   ```

### Step 3: Import to Custom GPT

1. Go to your Custom GPT in ChatGPT
2. Navigate to **Actions** section
3. Delete the old action (if any)
4. Click **Create new action**
5. Copy and paste the entire contents of `custom-gpt/openapi-schema-lightrag.yaml`
6. Save

### Step 4: Test in Custom GPT

Ask your Custom GPT:
> "What is the Internal Knowledge Navigator platform purpose and rules?"

You should now get the full accurate answer! ✅

## API Endpoints

### Primary Endpoint: `/retrieve` (POST)
Returns a synthesized answer with references.

**Request:**
```json
{
  "query": "Your question here",
  "mode": "hybrid"
}
```

**Response:**
```json
{
  "query": "Your question",
  "mode": "hybrid",
  "answer": "Synthesized answer with [references]...",
  "evidence_used": "Retrieved and synthesized using hybrid search mode",
  "confidence": "HIGH"
}
```

### Alternative: `/retrieve/context-only` (POST)
Returns raw evidence chunks without LLM synthesis - lets Custom GPT do the synthesis.

### Simple: `/retrieve/simple` (GET)
Quick GET endpoint for testing:
```bash
curl "http://localhost:8001/retrieve/simple?query=What+is+LightRAG&mode=hybrid"
```

## Search Modes

- **`naive`**: Simple vector similarity search
- **`local`**: Entity-focused local search (best for specific facts)
- **`global`**: Community-based global search (best for summaries)
- **`hybrid`**: Combined local + global search (✅ **recommended**)

## Startup Commands

### Start the new LightRAG API:
```bash
# Option 1: Direct
python3 lightrag_api_server.py

# Option 2: Using script
./start_lightrag_api.sh

# Option 3: Background
python3 lightrag_api_server.py &
```

### Start ngrok (after API is running):
```bash
ngrok http 8001
```

### Test the API:
```bash
python3 test_lightrag_api.py
```

## Maintenance

### To add new documents:
```bash
# Ingest new document into LightRAG
python lightrag/lightrag_ingest.py --input path/to/document.txt

# Restart API server (kills and restarts)
pkill -f lightrag_api_server
python3 lightrag_api_server.py &
```

### To check what's in LightRAG storage:
```bash
# List documents
cat lightrag_storage/kv_store_doc_status.json | python3 -m json.tool

# Query directly (bypassing API)
python lightrag/lightrag_query.py "Your question here"
```

## Migration Complete! 🎉

Your Custom GPT should now be able to answer questions about:
- Internal Knowledge Navigator platform
- LightRAG system details
- Vietnamese law (sample document)
- Custom GPT integration guides
- Project README

All documents in `lightrag_storage/` are now accessible via the new API.
