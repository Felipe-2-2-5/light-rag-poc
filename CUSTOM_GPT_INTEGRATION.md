# Custom GPT Integration Guide

## Overview

This guide explains how to integrate your local LightRAG retrieval system with the **Internal Knowledge Navigator** custom GPT at ChatGPT.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query (ChatGPT)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│            Custom GPT (Reasoning Layer)                     │
│  - Uses customer-gpt.md instructions                        │
│  - Constrained to provided evidence only                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ API Call via Actions
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    Internet (HTTPS)                          │
│                  ngrok tunnel or public server               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│          Local API Server (api_server.py)                   │
│                                                              │
│  ┌─────────────────────┬─────────────────┐                 │
│  │   Vector Search     │   Graph Search  │                 │
│  │      (FAISS)        │     (Neo4j)     │                 │
│  └─────────────────────┴─────────────────┘                 │
│                                                              │
│  Returns: Structured Evidence Response                      │
│  - Vector chunks with similarity scores                     │
│  - Graph entities & relationships                           │
│  - Intent classification                                    │
│  - Confidence scores                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

✅ **System Requirements:**
- Python 3.8+
- Neo4j running (via Docker or local)
- FAISS index and metadata files populated
- Internet connection for ngrok tunnel

✅ **Files Required:**
- `api_server.py` - FastAPI server
- `custom-gpt/openapi-schema.yaml` - API schema
- `custom-gpt/customer-gpt.md` - GPT instructions
- `custom-gpt/knowledge_hybrid_index.md` - Retrieval rules

---

## Step 1: Install Dependencies

```bash
# Install FastAPI and server dependencies
pip install fastapi uvicorn[standard] pydantic python-dotenv

# Install ngrok for exposing local server
# Option A: Direct download
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
  sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && \
  echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
  sudo tee /etc/apt/sources.list.d/ngrok.list && \
  sudo apt update && sudo apt install ngrok

# Option B: Download binary manually
# Visit: https://ngrok.com/download
```

Update `requirements.txt`:
```bash
cat >> requirements.txt << 'EOF'

# API Server
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
EOF
```

---

## Step 2: Configure Environment

Ensure your `.env` file has the necessary configuration:

```bash
# .env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=test

FAISS_INDEX_PATH=outputs/faiss.index
META_PATH=outputs/meta.json
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Optional: API server port
API_PORT=8000
```

---

## Step 3: Start Your Local Services

### 3.1 Start Neo4j

```bash
docker-compose up -d
```

### 3.2 Verify Data is Loaded

```bash
# Check FAISS index exists
ls -lh outputs/faiss.index outputs/meta.json

# Check Neo4j has data
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'test'))
with driver.session() as session:
    result = session.run('MATCH (n) RETURN count(n) as count')
    print(f'Neo4j nodes: {result.single()[\"count\"]}')
driver.close()
"
```

If no data exists, run ingestion first:
```bash
python src/ingest.py data/vn_law_sample.txt
```

---

## Step 4: Start API Server

```bash
# Run the API server
python api_server.py
```

You should see:
```
╔══════════════════════════════════════════════════════════╗
║   Internal Knowledge Navigator API Server               ║
║   Custom GPT Integration                                 ║
╚══════════════════════════════════════════════════════════╝

🌐 API URL: http://localhost:8000
📚 Docs: http://localhost:8000/docs
🔍 Health: http://localhost:8000/health

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
🔄 Initializing retrieval system...
📦 Loading embedding model: sentence-transformers/all-MiniLM-L6-v2
📂 Loading FAISS index from: outputs/faiss.index
🔗 Connecting to Neo4j at: bolt://localhost:7687
✅ System initialized successfully!
```

### 4.1 Test Locally

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test retrieval
curl -X POST http://localhost:8000/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Article 15?",
    "max_results": 3,
    "include_graph": true
  }'
```

Visit interactive docs: http://localhost:8000/docs

---

## Step 5: Expose Server to Internet (ngrok)

ChatGPT needs HTTPS access to call your API. Use ngrok to create a secure tunnel.

### 5.1 Sign Up for ngrok (Free)

1. Visit: https://ngrok.com/
2. Sign up for free account
3. Get your authtoken from dashboard

### 5.2 Configure ngrok

```bash
# Add your authtoken (one-time setup)
ngrok config add-authtoken YOUR_AUTHTOKEN_HERE
```

### 5.3 Start ngrok Tunnel

**In a new terminal** (keep api_server.py running):

```bash
ngrok http 8000
```

You'll see output like:
```
Session Status                online
Account                       yourname@email.com
Version                       3.x.x
Region                        United States (us)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123.ngrok-free.app -> http://localhost:8000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**Important:** Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`)

### 5.4 Test ngrok URL

```bash
# Test health through ngrok
curl https://YOUR-NGROK-URL.ngrok-free.app/health

# Test retrieval through ngrok
curl -X POST https://YOUR-NGROK-URL.ngrok-free.app/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Article 15?",
    "max_results": 3
  }'
```

---

## Step 6: Configure Custom GPT Actions

Now configure your custom GPT to call the API.

### 6.1 Access Custom GPT Settings

1. Go to: https://chatgpt.com/g/g-6984a713ab50819191ca60cd27f9037f-internal-knowledge-navigator
2. Click **"Configure"** or **"Edit GPT"**
3. Go to **"Actions"** section

### 6.2 Import OpenAPI Schema

1. Click **"Create new action"** or **"Add action"**
2. In the schema editor, paste the contents of `custom-gpt/openapi-schema.yaml`
3. **Replace the server URL** in the schema:

```yaml
servers:
  - url: https://YOUR-NGROK-URL.ngrok-free.app
    description: Development server via ngrok
```

Replace `YOUR-NGROK-URL.ngrok-free.app` with your actual ngrok URL.

### 6.3 Test the Action

In the Actions interface:
1. Click **"Test"** next to the `retrieveEvidence` action
2. Provide test input:
```json
{
  "query": "What is Article 15?",
  "max_results": 3,
  "include_graph": true
}
```
3. Click **"Run"**
4. Verify you get a successful response with evidence

### 6.4 Save Configuration

1. Review the action settings
2. Set **"Authentication"** to **"None"** (for development)
3. Click **"Save"** to save the GPT configuration

---

## Step 7: Update GPT Instructions (Optional)

If you haven't already, update the custom GPT instructions:

1. In **"Configure"** tab, find **"Instructions"** section
2. Paste the content from `custom-gpt/customer-gpt.md`
3. Ensure it includes:
   - Role as reasoning layer (not retriever)
   - Use only provided evidence
   - Output contract format
   - Failure handling rules

---

## Step 8: Test End-to-End Integration

### Test in Custom GPT Chat

1. Go to your custom GPT: https://chatgpt.com/g/g-6984a713ab50819191ca60cd27f9037f-internal-knowledge-navigator
2. Ask a question that should trigger retrieval:
   - "What does Article 15 say?"
   - "How do entities relate to compliance?"
   - "Explain the requirements in the law"

### Expected Flow

1. **User asks question** → Custom GPT receives it
2. **GPT calls `/retrieve` action** → Your API server processes it
3. **Evidence returned** → GPT receives structured evidence
4. **GPT synthesizes answer** → Using ONLY the provided evidence
5. **User sees answer** → With reasoning, evidence used, and confidence

### Verify Response Format

The GPT should return answers following the contract in `customer-gpt.md`:

```
**Answer**
[Direct response]

**Reasoning**
[Step-by-step explanation using evidence]

**Evidence Used**
- vn_law_sample.txt_C42 (similarity: 0.87, authority: PRIMARY)
- vn_law_sample.txt_C43 (similarity: 0.75, authority: SECONDARY)

**Confidence**
HIGH
```

---

## Troubleshooting

### ❌ "System not initialized" Error

**Cause:** FAISS index or Neo4j not loaded

**Solution:**
```bash
# Check files exist
ls -lh outputs/faiss.index outputs/meta.json

# Re-run ingestion if needed
python src/ingest.py data/vn_law_sample.txt

# Restart API server
python api_server.py
```

### ❌ ngrok "Failed to complete tunnel connection"

**Cause:** Free ngrok URLs expire after ~8 hours or on restart

**Solution:**
```bash
# Stop and restart ngrok
ngrok http 8000

# Update the URL in custom GPT Actions schema
# Re-test the action
```

### ❌ Custom GPT doesn't call the action

**Cause:** Intent not clear or action not triggered

**Solution:**
1. Be explicit in your question: "Retrieve information about Article 15"
2. Check action logs in GPT configuration
3. Verify ngrok tunnel is active: `curl https://YOUR-URL/health`

### ❌ CORS Errors in Browser

**Cause:** ChatGPT origin not allowed

**Solution:** The API server already includes CORS middleware for ChatGPT domains. Verify in `api_server.py`:
```python
allow_origins=["https://chatgpt.com", "https://chat.openai.com"],
```

### ❌ Neo4j Connection Refused

**Cause:** Neo4j not running

**Solution:**
```bash
docker-compose up -d
docker ps  # Verify neo4j container is running
```

---

## Production Deployment (Optional)

For permanent deployment (not just testing), consider:

### Option 1: Cloud VM + Domain

1. Deploy to cloud VM (AWS EC2, Google Cloud, DigitalOcean)
2. Install dependencies and run API server
3. Use reverse proxy (nginx) with SSL certificate
4. Update OpenAPI schema with your domain URL

### Option 2: Serverless (AWS Lambda, Google Cloud Functions)

1. Package API server as serverless function
2. Configure API Gateway
3. Set up environment variables
4. Update OpenAPI schema with API Gateway URL

### Option 3: ngrok Pro

1. Upgrade to ngrok Pro plan
2. Get a permanent reserved domain
3. Keep ngrok tunnel running as a service
4. More stable than free tier

---

## Maintenance

### Keep ngrok Running

**Option A: Screen/tmux**
```bash
screen -S ngrok
ngrok http 8000
# Ctrl+A, D to detach
```

**Option B: Systemd Service**
Create `/etc/systemd/system/ngrok.service`:
```ini
[Unit]
Description=ngrok tunnel
After=network.target

[Service]
Type=simple
User=youruser
ExecStart=/usr/local/bin/ngrok http 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Update Evidence When Data Changes

```bash
# Re-ingest documents
python src/ingest.py data/new_document.txt

# Restart API server to reload FAISS index
# (or implement hot-reload in api_server.py)
```

### Monitor API Logs

```bash
# API server logs show each request
# Watch for:
# - Query patterns
# - Confidence scores
# - Error rates

tail -f api_server.log  # If logging to file
```

---

## Security Considerations

### Current Setup (Development)

⚠️ **No authentication** - API is open to anyone with the URL
⚠️ **No rate limiting** - Can be abused
⚠️ **ngrok URL is public** - Anyone can discover and use it

### Recommended for Production

1. **Add API Key Authentication**
   ```python
   # In api_server.py
   from fastapi.security import APIKeyHeader
   
   api_key_header = APIKeyHeader(name="X-API-Key")
   
   @app.post("/retrieve")
   async def retrieve_evidence(
       request: QueryRequest,
       api_key: str = Depends(api_key_header)
   ):
       if api_key != os.getenv("API_KEY"):
           raise HTTPException(401, "Invalid API key")
       # ... rest of function
   ```

2. **Add Rate Limiting**
   ```bash
   pip install slowapi
   ```

3. **Use HTTPS with Valid Certificate**
   - Use a real domain with Let's Encrypt
   - Configure nginx reverse proxy

4. **Restrict CORS Origins**
   - Only allow specific ChatGPT domains
   - Already configured in `api_server.py`

---

## Testing Checklist

- [ ] Neo4j container running
- [ ] FAISS index loaded successfully
- [ ] API server starts without errors
- [ ] `/health` endpoint returns healthy status
- [ ] `/retrieve` endpoint returns evidence locally
- [ ] ngrok tunnel active and accessible
- [ ] OpenAPI schema imported to Custom GPT
- [ ] Server URL updated in schema
- [ ] Action test passes in GPT configuration
- [ ] Custom GPT instructions updated
- [ ] End-to-end test: Question → Retrieval → Answer
- [ ] Response follows evidence contract format

---

## Quick Start Commands

```bash
# Terminal 1: Start Neo4j
docker-compose up -d

# Terminal 2: Start API Server
python api_server.py

# Terminal 3: Start ngrok
ngrok http 8000

# Test
curl https://YOUR-NGROK-URL/health
```

---

## Next Steps

1. ✅ **Test with real queries** - Try various question types
2. ✅ **Monitor confidence scores** - See which domains work well
3. ✅ **Expand knowledge base** - Add more documents
4. ✅ **Tune retrieval parameters** - Adjust similarity thresholds
5. ✅ **Implement domain profiles** - Add domain-specific configs (see earlier discussion)
6. ✅ **Add authentication** - Secure the API for production

---

## Support

**API Documentation:** http://localhost:8000/docs (when server running)

**ngrok Dashboard:** http://127.0.0.1:4040 (when ngrok running)

**Custom GPT:** https://chatgpt.com/g/g-6984a713ab50819191ca60cd27f9037f-internal-knowledge-navigator

**Logs:**
- API Server: Check terminal output or `uvicorn.log`
- ngrok: Check ngrok terminal output
- Custom GPT: Check Actions logs in GPT configuration

---

**Last Updated:** February 5, 2026
