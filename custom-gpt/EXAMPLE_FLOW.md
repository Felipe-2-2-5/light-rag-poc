# Custom GPT Integration - Example Flow

This document shows example requests and responses to illustrate how your Custom GPT will interact with the retrieval API.

---

## Example 1: Simple Fact Lookup

### User Question (to Custom GPT)
```
What does Article 15 say about compliance requirements?
```

### Custom GPT → API Request
```http
POST https://your-ngrok-url.ngrok-free.app/retrieve
Content-Type: application/json

{
  "query": "What does Article 15 say about compliance requirements?",
  "max_results": 5,
  "include_graph": true
}
```

### API → Custom GPT Response
```json
{
  "query": "What does Article 15 say about compliance requirements?",
  "intent": {
    "primary": "FACT_LOOKUP",
    "confidence": 0.8
  },
  "vector_evidence": [
    {
      "chunk_id": "vn_law_sample.txt_C42",
      "text": "Điều 15 quy định rằng tất cả các tổ chức phải tuân thủ các yêu cầu bảo mật dữ liệu theo quy định của pháp luật hiện hành...",
      "similarity": 0.87,
      "authority": "PRIMARY"
    },
    {
      "chunk_id": "vn_law_sample.txt_C43",
      "text": "Các yêu cầu tuân thủ bao gồm: (1) Bảo vệ thông tin cá nhân, (2) Báo cáo vi phạm trong vòng 72 giờ...",
      "similarity": 0.75,
      "authority": "SECONDARY"
    }
  ],
  "graph_evidence": {
    "nodes": [
      {
        "id": "ARTICLE_Điều_15",
        "label": "Điều 15",
        "type": "Article"
      },
      {
        "id": "LAW_12345",
        "label": "Luật Bảo vệ Dữ liệu",
        "type": "Law"
      }
    ],
    "edges": [
      {
        "source": "ARTICLE_Điều_15",
        "relation": "MENTIONED_WITH",
        "target": "LAW_12345"
      }
    ],
    "traversal_path": "Điều 15 --MENTIONED_WITH--> Luật Bảo vệ Dữ liệu"
  },
  "confidence": "HIGH",
  "confidence_score": 0.85,
  "retrieval_strategy": "VECTOR_PRIMARY",
  "evidence_summary": "Retrieved 2 relevant chunks with 2 entities and 1 relationship"
}
```

### Custom GPT → User Answer
```
**Answer**
Article 15 requires all organizations to comply with data security requirements 
as stipulated by current law. The compliance requirements include: (1) Protection 
of personal information, and (2) Reporting violations within 72 hours.

**Reasoning**
The answer is directly supported by two high-confidence text chunks from the 
legal document (vn_law_sample.txt_C42 and C43). The first chunk establishes 
the general compliance obligation under Article 15, while the second chunk 
enumerates the specific requirements. The knowledge graph confirms that 
Article 15 is connected to the Data Protection Law, providing additional 
contextual authority.

**Evidence Used**
- vn_law_sample.txt_C42 (similarity: 0.87, authority: PRIMARY)
  "Điều 15 quy định rằng tất cả các tổ chức phải tuân thủ..."
  
- vn_law_sample.txt_C43 (similarity: 0.75, authority: SECONDARY)
  "Các yêu cầu tuân thủ bao gồm: (1) Bảo vệ thông tin cá nhân..."

- Graph Context: Article 15 → Mentioned With → Data Protection Law

**Confidence**
HIGH (0.85)
```

---

## Example 2: Relationship Query

### User Question
```
How does Article 15 relate to privacy regulations?
```

### API Response (Abbreviated)
```json
{
  "intent": {
    "primary": "RELATIONSHIP",
    "confidence": 0.8
  },
  "retrieval_strategy": "GRAPH_PRIMARY",
  "graph_evidence": {
    "nodes": [
      {"id": "ARTICLE_Điều_15", "label": "Điều 15", "type": "Article"},
      {"id": "LAW_PRIVACY", "label": "Luật Bảo vệ Quyền riêng tư", "type": "Law"},
      {"id": "ORG_DPA", "label": "Data Protection Authority", "type": "Organization"}
    ],
    "edges": [
      {"source": "ARTICLE_Điều_15", "relation": "IMPLEMENTS", "target": "LAW_PRIVACY"},
      {"source": "LAW_PRIVACY", "relation": "ENFORCED_BY", "target": "ORG_DPA"}
    ],
    "traversal_path": "Điều 15 --IMPLEMENTS--> Privacy Law --ENFORCED_BY--> DPA"
  },
  "confidence": "HIGH"
}
```

### Custom GPT Answer
```
**Answer**
Article 15 implements the Privacy Protection Law (Luật Bảo vệ Quyền riêng tư), 
which is enforced by the Data Protection Authority.

**Reasoning**
The knowledge graph reveals a direct implementation relationship between 
Article 15 and the Privacy Law, with the Data Protection Authority serving 
as the enforcement body. This structural relationship is authoritative for 
understanding legal connections.

**Evidence Used**
- Graph Path: Điều 15 → IMPLEMENTS → Privacy Law → ENFORCED_BY → DPA
- 3 entities, 2 relationships traversed

**Confidence**
HIGH
```

---

## Example 3: Low Confidence / Insufficient Evidence

### User Question
```
What was the economic impact of Article 15 in 2023?
```

### API Response
```json
{
  "intent": {
    "primary": "TEMPORAL",
    "confidence": 0.75
  },
  "vector_evidence": [
    {
      "chunk_id": "vn_law_sample.txt_C89",
      "text": "Điều 15 có hiệu lực từ năm 2020...",
      "similarity": 0.42,
      "authority": "CONTEXTUAL"
    }
  ],
  "graph_evidence": null,
  "confidence": "LOW",
  "confidence_score": 0.35,
  "retrieval_strategy": "VECTOR_PRIMARY",
  "evidence_summary": "Retrieved 1 relevant chunk with low similarity"
}
```

### Custom GPT Answer
```
**Answer**
The provided evidence does not support an answer about the economic impact 
of Article 15 in 2023.

**Reasoning**
While one chunk mentions Article 15 became effective in 2020, there is no 
evidence in the retrieved documents regarding economic impact or 2023-specific 
data. The low similarity score (0.42) and absence of graph context indicate 
the question falls outside the knowledge base coverage.

**Evidence Used**
- vn_law_sample.txt_C89 (similarity: 0.42, authority: CONTEXTUAL)
  "Điều 15 có hiệu lực từ năm 2020..."
  [Not sufficient for answering the question]

**Confidence**
LOW (0.35)
```

---

## Example 4: Testing via curl

### Test Locally
```bash
# Health check
curl http://localhost:8000/health

# Simple query
curl -X POST http://localhost:8000/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Article 15?",
    "max_results": 3,
    "include_graph": true
  }' | jq

# Simplified endpoint
curl -X POST "http://localhost:8000/retrieve/simple?query=test&max_results=2" | jq
```

### Test via ngrok
```bash
# Replace with your actual ngrok URL
NGROK_URL="https://abc123.ngrok-free.app"

# Health check
curl $NGROK_URL/health

# Full retrieval
curl -X POST $NGROK_URL/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "compliance requirements",
    "max_results": 5,
    "include_graph": true
  }' | jq '.evidence_summary'
```

---

## Evidence Contract Validation

The API response **MUST** include:

### ✅ Required Fields
- `query` (string): Original query
- `intent` (object): Intent classification with `primary` and `confidence`
- `vector_evidence` (array): At least one chunk with:
  - `chunk_id` (string)
  - `text` (string)
  - `similarity` (number, 0-1)
  - `authority` (enum: PRIMARY, SECONDARY, CONTEXTUAL, HISTORICAL)
- `confidence` (enum: HIGH, MEDIUM, LOW)
- `confidence_score` (number, 0-1)
- `retrieval_strategy` (enum: VECTOR_PRIMARY, GRAPH_PRIMARY, HYBRID)
- `evidence_summary` (string)

### ✅ Optional Fields
- `graph_evidence` (object, nullable): When graph context is available
  - `nodes` (array)
  - `edges` (array)
  - `traversal_path` (string)

### ❌ Custom GPT Must NOT
- Request additional retrieval
- Make assumptions beyond evidence
- Fill gaps with prior knowledge
- Modify or reinterpret evidence authority

---

## Intent → Strategy Mapping

Following `knowledge_hybrid_index.md`:

| User Intent | API Intent | Retrieval Strategy | Primary Focus |
|-------------|-----------|-------------------|---------------|
| "What is X?" | FACT_LOOKUP | VECTOR_PRIMARY | Text chunks |
| "How does X relate to Y?" | RELATIONSHIP | GRAPH_PRIMARY | Graph traversal |
| "Why was X decided?" | DECISION_RATIONALE | GRAPH_PRIMARY | Graph + context |
| "How do I do X?" | PROCEDURE | VECTOR_PRIMARY | Step-by-step text |
| "Compare X and Y" | COMPARISON | VECTOR_PRIMARY | Multiple chunks |
| "When did X change?" | TEMPORAL | GRAPH_PRIMARY | Temporal edges |
| "Explain X" | EXPLANATION | VECTOR_PRIMARY | Descriptive chunks |
| "Why did X fail?" | ROOT_CAUSE | GRAPH_PRIMARY | Causal chains |

---

## Authority Levels Explained

### PRIMARY
- High similarity (>0.8)
- Strong graph connections (3+ entities)
- Direct answer to query
- **Most trustworthy evidence**

### SECONDARY
- Good similarity (>0.6)
- Some graph context (1+ entities)
- Relevant but not definitive
- **Supporting evidence**

### CONTEXTUAL
- Moderate similarity (>0.4)
- Limited or no graph context
- Background information
- **Supplementary only**

### HISTORICAL
- Low similarity (<0.4)
- Outdated or deprecated
- Legacy information
- **Use with caution**

---

## Performance Expectations

### Latency
- Local API: 50-200ms
- Via ngrok: 200-500ms
- With graph expansion: +100-300ms

### Throughput
- Single query: ~2-5 queries/second
- Batched: Not supported (sequential only)

### Limits
- Max results: 10 chunks
- Max graph depth: 2 hops
- Timeout: 30 seconds

---

## Debugging Tips

### Issue: "System not initialized"
```bash
# Check logs
tail -f api_server.log

# Verify FAISS index
ls -lh outputs/faiss.index

# Test Neo4j connection
python -c "from neo4j import GraphDatabase; \
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'test')); \
driver.verify_connectivity(); print('✅ Neo4j connected')"
```

### Issue: Low confidence scores
- Check if documents are ingested
- Verify embedding model matches
- Adjust similarity thresholds in `api_server.py`
- Review intent classification logic

### Issue: No graph evidence
- Confirm entities extracted: `outputs/entities.json`
- Check Neo4j has relationships: `MATCH ()-[r]->() RETURN count(r)`
- Verify chunk_id format matches

---

## Next Steps

1. ✅ Test API locally: `python test_custom_gpt_api.py`
2. ✅ Start ngrok: `ngrok http 8000`
3. ✅ Update OpenAPI schema with ngrok URL
4. ✅ Import to Custom GPT Actions
5. ✅ Test complete flow in ChatGPT
6. ✅ Monitor confidence scores
7. ✅ Expand knowledge base with more documents

---

**Documentation:**
- [CUSTOM_GPT_INTEGRATION.md](CUSTOM_GPT_INTEGRATION.md) - Full setup guide
- [custom-gpt/customer-gpt.md](custom-gpt/customer-gpt.md) - GPT instructions
- [custom-gpt/knowledge_hybrid_index.md](custom-gpt/knowledge_hybrid_index.md) - Retrieval rules
- [custom-gpt/openapi-schema.yaml](custom-gpt/openapi-schema.yaml) - API schema

**API Endpoints:**
- Local: http://localhost:8000/docs
- ngrok: https://your-url.ngrok-free.app/docs
