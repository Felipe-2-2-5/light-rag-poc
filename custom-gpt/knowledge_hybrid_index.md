# Knowledge Index — Hybrid Light-RAG System

## Purpose
This index defines how the system selects, combines, and constrains retrieval across
vector search, knowledge graph traversal, and symbolic reasoning.

It exists to:
- Maximize factual accuracy
- Minimize retrieval noise
- Preserve explainability
- Enable deterministic retrieval paths before generation

The LLM must follow this index before answering.

---

## Retrieval Philosophy (Hybrid Light-RAG)

This system follows a **3-stage retrieval strategy**:

1. **Intent Classification**
2. **Retriever Selection**
3. **Constrained Synthesis**

The system MUST NOT rely on vector similarity alone.

---

## 1️⃣ Intent Taxonomy (Mandatory)

Every query must be classified into one or more intents **before retrieval**.

### Core Intent Types

| Intent | Description |
|------|------------|
| FACT_LOOKUP | Concrete facts, definitions, properties |
| DECISION_RATIONALE | Why something was chosen |
| RELATIONSHIP | How entities connect |
| PROCEDURE | Steps, workflows, how-to |
| COMPARISON | Trade-offs, alternatives |
| TEMPORAL | Evolution over time |
| EXPLANATION | Conceptual understanding |
| ROOT_CAUSE | Failure analysis, reasoning chains |

---

## 2️⃣ Retriever Selection Matrix

Based on intent, the system must select the **primary retriever**.

| Intent | Primary Retriever | Secondary |
|------|------------------|-----------|
| FACT_LOOKUP | Vector | Graph |
| DECISION_RATIONALE | Graph | Vector |
| RELATIONSHIP | Graph | None |
| PROCEDURE | Vector | Graph |
| COMPARISON | Vector | Graph |
| TEMPORAL | Graph | Vector |
| EXPLANATION | Vector | Graph |
| ROOT_CAUSE | Graph | Vector |

⚠️ Graph retrieval is authoritative for **relationships and causality**.

---

## 3️⃣ Vector Retrieval Rules (FAISS)

### Vector Store Scope
- Chunk size: 300–800 tokens
- Overlap: ≤20%
- Embeddings represent **semantic content only**, not authority

### Vector Retrieval Constraints
- Top-K ≤ 8
- Similarity threshold enforced
- Reject semantically close but logically unrelated chunks

### Use Vector Retrieval For:
- Descriptions
- Procedures
- Explanations
- Background context

---

## 4️⃣ Knowledge Graph Retrieval Rules (Neo4j)

### Graph Node Types (examples)
- Concept
- Decision
- Entity
- Event
- Policy
- System
- Artifact

### Graph Edge Semantics
- CAUSES
- DEPENDS_ON
- DECIDED_BY
- REPLACED_BY
- IMPLEMENTS
- CONSTRAINS

### Use Graph Retrieval For:
- Causality
- Ownership
- Dependencies
- Evolution over time
- Authority resolution

Graph traversal depth:
- Default: 1–2 hops
- Max: 3 hops (explicit reasoning required)

---

## 5️⃣ Authority & Trust Model

Each knowledge source is assigned:

- **Authority Level**
  - PRIMARY
  - SECONDARY
  - CONTEXTUAL
  - HISTORICAL

- **Confidence Score**
  - High / Medium / Low

When conflict exists:
PRIMARY > SECONDARY > CONTEXTUAL > HISTORICAL

Vector similarity does NOT override authority.

---

## 6️⃣ Hybrid Retrieval Composition Rules

### Allowed Patterns

✅ Graph → Vector → Synthesis  
✅ Vector → Graph → Synthesis  
✅ Graph-only (relationships)  
✅ Vector-only (simple explanation)

### Forbidden Patterns

❌ Vector-only for decisions  
❌ Graph-only for explanations  
❌ Blind Top-K merging  

---

## 7️⃣ Evidence Assembly Rules

Before generation, the system must assemble:

- Retrieved chunks (vector)
- Traversed nodes/edges (graph)
- Explicit reasoning path

The LLM must see:
- What was retrieved
- Why it was retrieved
- What was rejected

---

## 8️⃣ Generation Constraints

The model must:
- Generate only from retrieved evidence
- Explicitly state uncertainty
- Avoid filling gaps with prior knowledge
- Preserve reasoning chains

---

## 9️⃣ Output Contract

**Answer**
- Direct response

**Reasoning**
- Logical steps derived from retrieved evidence

**Evidence**
- Vector chunks (IDs or titles)
- Graph paths (node → edge → node)

**Confidence**
- High / Medium / Low

---

## 🔟 Known Failure Modes

The system must flag:
- Sparse graph coverage
- Low similarity matches
- Conflicting authorities
- Incomplete traversal paths

---

## Maintenance Rules

When adding new knowledge:
1. Embed content
2. Attach to graph with typed edges
3. Assign authority
4. Update intent coverage if needed

---

## Final Instruction

This index governs retrieval behavior.
Generation quality is secondary to correctness.
