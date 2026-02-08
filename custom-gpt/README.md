# Custom GPT Integration Files

This directory contains all the necessary configuration files for integrating your LightRAG retrieval system with the Internal Knowledge Navigator custom GPT at ChatGPT.

---

## 📁 Files Overview

| File | Purpose |
|------|---------|
| **customer-gpt.md** | Custom GPT system instructions (paste into GPT "Instructions" field) |
| **knowledge_hybrid_index.md** | Retrieval philosophy and rules (reference for understanding how system works) |
| **openapi-schema.yaml** | OpenAPI schema for GPT Actions (import into GPT "Actions" configuration) |
| **EXAMPLE_FLOW.md** | Example requests/responses showing the complete flow |

---

## 🎯 Quick Start

### 1. Start Your API Server
```bash
# From project root
./start_custom_gpt_api.sh
```

Or manually:
```bash
# Terminal 1: Start Neo4j
docker-compose up -d

# Terminal 2: Start API server
python api_server.py

# Terminal 3: Start ngrok
ngrok http 8000
```

### 2. Configure Custom GPT

1. **Go to your Custom GPT:** https://chatgpt.com/g/g-6984a713ab50819191ca60cd27f9037f-internal-knowledge-navigator

2. **Click "Configure" or "Edit GPT"**

3. **Update Instructions:**
   - Copy content from `customer-gpt.md`
   - Paste into "Instructions" field
   - Save

4. **Add Action:**
   - Go to "Actions" section
   - Click "Create new action"
   - Copy content from `openapi-schema.yaml`
   - **Update server URL** with your ngrok URL:
     ```yaml
     servers:
       - url: https://YOUR-NGROK-URL.ngrok-free.app
     ```
   - Test the action
   - Save

### 3. Test Integration

Ask your custom GPT questions like:
- "What does Article 15 say?"
- "How do entities relate to compliance?"
- "Explain the requirements"

The GPT should:
1. Call your `/retrieve` endpoint
2. Receive structured evidence
3. Synthesize an answer using ONLY the evidence
4. Return: Answer, Reasoning, Evidence Used, Confidence

---

## 📋 Integration Checklist

### Prerequisites
- [ ] Python 3.8+ installed
- [ ] Neo4j running (docker-compose up -d)
- [ ] FAISS index populated (outputs/faiss.index exists)
- [ ] Dependencies installed (pip install -r requirements.txt)

### API Setup
- [ ] API server starts without errors
- [ ] Health endpoint returns healthy: `http://localhost:8000/health`
- [ ] Retrieval endpoint works: `http://localhost:8000/retrieve`
- [ ] Test script passes: `python test_custom_gpt_api.py`

### Public Access
- [ ] ngrok installed and configured
- [ ] ngrok tunnel active: `ngrok http 8000`
- [ ] ngrok URL accessible: `curl https://YOUR-URL/health`

### Custom GPT Configuration
- [ ] Instructions updated with `customer-gpt.md`
- [ ] OpenAPI schema imported from `openapi-schema.yaml`
- [ ] Server URL updated in schema with ngrok URL
- [ ] Action test passes in GPT configuration
- [ ] End-to-end test: Question → API → Answer

---

## 🏗️ Architecture

```
User Question
     ↓
Custom GPT (Reasoning Layer)
     ↓ API Call
ngrok Tunnel (HTTPS)
     ↓
API Server (api_server.py)
     ↓
┌────────────┬──────────────┐
│   FAISS    │    Neo4j     │
│  (Vector)  │   (Graph)    │
└────────────┴──────────────┘
     ↓
Structured Evidence Response
     ↓
Custom GPT Synthesis
     ↓
Final Answer to User
```

---

## 📖 Key Concepts

### Intent Classification
Every query is classified into one of 8 intent types:
- FACT_LOOKUP
- DECISION_RATIONALE
- RELATIONSHIP
- PROCEDURE
- COMPARISON
- TEMPORAL
- EXPLANATION
- ROOT_CAUSE

### Retrieval Strategy
Based on intent, system selects:
- **VECTOR_PRIMARY**: Facts, procedures, explanations
- **GRAPH_PRIMARY**: Relationships, decisions, causality
- **HYBRID**: Combined approach

### Authority Levels
Evidence is tagged with authority:
- **PRIMARY**: High confidence, strong connections
- **SECONDARY**: Good similarity, some context
- **CONTEXTUAL**: Background information
- **HISTORICAL**: Low confidence or outdated

### Confidence Scoring
Overall confidence combines:
- Vector similarity (35%)
- Graph connectivity (20%)
- Query coverage (20%)
- Text quality (10%)
- Semantic coherence (10%)
- Answer presence (5%)

---

## 🔧 Configuration Options

### API Server (`api_server.py`)

**Environment Variables:**
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=test
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
API_PORT=8000
```

**Modify Default Behavior:**
```python
# Line ~70: Change default max_results
max_results: int = Field(default=5, ge=1, le=10)

# Line ~190: Adjust intent classification patterns
if any(word in query_lower for word in ['what is', 'define']):

# Line ~280: Tune authority assignment
if similarity > 0.8 and has_graph_context and entity_count >= 3:
    return "PRIMARY"
```

### OpenAPI Schema (`openapi-schema.yaml`)

**Update Server URL:**
```yaml
servers:
  - url: https://your-actual-domain.com  # Production
  - url: https://abc123.ngrok-free.app   # Development
```

**Modify Descriptions:**
Edit the `description` fields to customize how ChatGPT understands each endpoint.

---

## 🚨 Troubleshooting

### API Not Starting
```bash
# Check logs
tail -f api_server.log

# Verify environment
python -c "from src.config import *; print(f'Neo4j: {NEO4J_URI}')"

# Test components individually
python test_custom_gpt_api.py --skip-health
```

### Custom GPT Not Calling API
1. Check action logs in GPT configuration
2. Verify ngrok tunnel is active: `curl https://YOUR-URL/health`
3. Test action manually in GPT Actions interface
4. Check if question triggers intent (be explicit: "Retrieve info about X")

### Low Quality Results
1. Review confidence scores in API response
2. Check if sufficient documents are ingested
3. Verify entity extraction: `cat outputs/entities.json | jq length`
4. Adjust similarity thresholds in `api_server.py`

### ngrok URL Expired
Free ngrok URLs change on restart:
```bash
# Get new URL
curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'

# Update in openapi-schema.yaml
# Re-import to Custom GPT Actions
```

---

## 📊 Performance Tips

### Optimize Vector Search
- Use GPU-enabled FAISS index for large datasets
- Reduce embedding dimensions (trade-off: accuracy vs speed)
- Cache frequent queries

### Optimize Graph Queries
- Add indexes in Neo4j: `CREATE INDEX ON :Entity(eid)`
- Limit traversal depth (default: 2 hops)
- Use connection pooling

### Scale API Server
```bash
# Run with multiple workers
uvicorn api_server:app --workers 4 --host 0.0.0.0 --port 8000
```

---

## 🔐 Security (Production)

### Add Authentication
```python
# In api_server.py
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

@app.post("/retrieve")
async def retrieve_evidence(
    request: QueryRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    if credentials.credentials != os.getenv("API_KEY"):
        raise HTTPException(401, "Unauthorized")
    # ... rest of function
```

Then in Custom GPT Actions:
- Set Authentication: Bearer Token
- Add token value

### Rate Limiting
```bash
pip install slowapi
```

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

@app.post("/retrieve")
@limiter.limit("10/minute")
async def retrieve_evidence(request: Request, ...):
    # ...
```

---

## 📚 Additional Documentation

- **[../CUSTOM_GPT_INTEGRATION.md](../CUSTOM_GPT_INTEGRATION.md)** - Complete setup guide
- **[EXAMPLE_FLOW.md](EXAMPLE_FLOW.md)** - Request/response examples
- **[../README.md](../README.md)** - Project overview
- **API Docs:** http://localhost:8000/docs

---

## 🎉 Success Indicators

You know it's working when:

✅ API health check returns all components healthy  
✅ Test script passes all checks  
✅ ngrok tunnel shows incoming requests  
✅ Custom GPT calls the `/retrieve` action  
✅ GPT responses include "Evidence Used" section  
✅ Confidence levels are HIGH/MEDIUM for good matches  
✅ GPT refuses to answer when confidence is LOW  

---

## 🔄 Workflow Summary

```
1. User asks question in Custom GPT
2. GPT calls /retrieve with query
3. API classifies intent
4. API performs hybrid search (vector + graph)
5. API returns structured evidence
6. GPT synthesizes answer from evidence only
7. User receives answer with reasoning & confidence
```

---

**Custom GPT URL:**  
https://chatgpt.com/g/g-6984a713ab50819191ca60cd27f9037f-internal-knowledge-navigator

**Need Help?**  
See [../CUSTOM_GPT_INTEGRATION.md](../CUSTOM_GPT_INTEGRATION.md) for detailed troubleshooting.

---

*Last Updated: February 5, 2026*
