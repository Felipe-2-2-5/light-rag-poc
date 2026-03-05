import os, json
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from vector_store import FaissStore
from config import EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import argparse
import re
from document_parser import DocumentParser
from neo4j import GraphDatabase
import logging

from logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i+chunk_size])
        chunks.append(chunk)
        i += (chunk_size - overlap)
    return chunks

def simple_ner_and_relations(chunks, doc_basename):
    """
    Very lightweight heuristic NER/RE for Vietnamese legal text:
    - Identify 'Điều N' (Article) references as entities
    - Identify capitalized words sequences as organizations (heuristic)
    - Identify 'Luật' and 'Nghị định' mentions
    Return list of entities and relations inferred per chunk.
    """
    entities = {}
    relations = []
    for i, c in enumerate(chunks):
        # find articles
        for m in re.finditer(r"Điều\s*\d+", c, flags=re.I):
            ent = m.group(0).strip()
            eid = f"ARTICLE_{ent.replace(' ', '_')}"
            entities[eid] = {"label": ent, "type": "Article", "source_chunk": i, "chunk_id": f"{doc_basename}_C{i}"}
        # find law/regulation mentions
        for m in re.finditer(r"(Luật|Nghị định)\s*[^\.,\n]+", c, flags=re.I):
            ent = m.group(0).strip()
            eid = f"LAW_{hash(ent)}"
            entities[eid] = {"label": ent, "type": "Law", "source_chunk": i, "chunk_id": f"{doc_basename}_C{i}"}
        # crude organization: sequences of capitalized words (not perfect)
        for m in re.finditer(r"\b[A-Z][a-z0-9ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯảồộêầậếẻỹạảằếựỳ...]+\b(?:\s+[A-Z][\w\-\.\']+){0,4}", c):
            ent = m.group(0).strip()
            if len(ent.split()) <= 5 and len(ent) > 3:
                eid = f"ORG_{hash(ent)}"
                entities[eid] = {"label": ent, "type": "Org", "source_chunk": i, "chunk_id": f"{doc_basename}_C{i}"}
    # simple relation heuristics: if a chunk mentions an Article and a Law -> relation
    for eid1, e1 in entities.items():
        for eid2, e2 in entities.items():
            if eid1 != eid2 and e1['source_chunk'] == e2['source_chunk']:
                relations.append((eid1, "MENTIONED_WITH", eid2))
    return entities, relations

def build_knowledge_graph(entities, relations, chunks, doc_basename):
    """
    Build knowledge graph in Neo4j database from extracted entities and relations.
    """
    logger.info("Connecting to Neo4j database...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # Create entities
            logger.info(f"Creating {len(entities)} entities...")
            for eid, props in entities.items():
                session.run("""
                    MERGE (e:Entity {eid:$eid})
                    SET e.name = $name, e.type = $type, e.source_chunk = $source_chunk
                """, eid=eid, name=props.get("label"), type=props.get("type"), 
                source_chunk=props.get("source_chunk"))
            
            # Create chunk nodes
            logger.info(f"Creating {len(chunks)} chunk nodes...")
            for i, chunk_text in enumerate(chunks):
                chunk_id = f"{doc_basename}_C{i}"
                session.run("""
                    MERGE (c:Chunk {chunk_id:$chunk_id})
                    SET c.text = $text, c.doc_id = $doc_id
                """, chunk_id=chunk_id, text=chunk_text[:2000], doc_id=doc_basename)
            
            # Create relations between entities
            logger.info(f"Creating {len(relations)} relations...")
            for a, rel, b in relations:
                try:
                    session.run("""
                        MATCH (a:Entity {eid:$a}), (b:Entity {eid:$b})
                        MERGE (a)-[r:REL {type:$rel}]->(b)
                        SET r.first_seen = coalesce(r.first_seen, timestamp())
                    """, a=a, b=b, rel=rel)
                except Exception as e:
                    logger.warning(f"Failed to create relation {a}->{b}: {e}")
            
            # Link entities to chunks
            logger.info("Linking entities to chunks...")
            for eid, props in entities.items():
                chunk_id = props.get("chunk_id")
                if chunk_id:
                    session.run("""
                        MATCH (e:Entity {eid:$eid}), (c:Chunk {chunk_id:$chunk_id})
                        MERGE (e)-[:MENTIONED_IN]->(c)
                    """, eid=eid, chunk_id=chunk_id)
        
        logger.info("Knowledge graph built successfully!")
    except Exception as e:
        logger.error(f"Error building knowledge graph: {e}")
        raise
    finally:
        driver.close()

def main(input_path, model_name=EMBEDDING_MODEL, ade_api_key=None, build_kg=True):
    # Use hybrid document parser (free first, ADE fallback)
    parser = DocumentParser(ade_api_key=ade_api_key, use_ade_fallback=True)
    
    logger.info(f"Parsing document: {input_path}")
    text, metadata = parser.parse_document(input_path)
    
    logger.info(f"Parser used: {parser.last_parser_used}")
    if metadata:
        logger.info(f"Metadata: {metadata}")
    
    # Get document basename for IDs
    doc_basename = os.path.basename(input_path)
    
    # Chunk the text
    chunks = chunk_text(text)
    logger.info(f"Split into {len(chunks)} chunks.")
    
    # Generate embeddings
    logger.info("Generating embeddings...")
    model = SentenceTransformer(model_name)
    embeddings = model.encode(chunks, show_progress_bar=True)
    dim = embeddings.shape[1]
    
    # Store in FAISS vector store
    logger.info("Storing embeddings in FAISS...")
    store = FaissStore(dim)
    metas = []
    for i, c in enumerate(chunks):
        metas.append({"chunk_id": f"{doc_basename}_C{i}", "text": c})
    store.add(embeddings, metas)
    
    # Extract entities and relations
    logger.info("Extracting entities and relations...")
    entities, relations = simple_ner_and_relations(chunks, doc_basename)
    logger.info(f"Found {len(entities)} entities and {len(relations)} relations")
    
    # Save entities & relations to disk for reference
    with open("outputs/entities.json", "w", encoding="utf-8") as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)
    with open("outputs/relations.json", "w", encoding="utf-8") as f:
        json.dump(relations, f, ensure_ascii=False, indent=2)
    
    # Build knowledge graph in Neo4j
    if build_kg:
        try:
            build_knowledge_graph(entities, relations, chunks, doc_basename)
        except Exception as e:
            logger.error(f"Failed to build knowledge graph: {e}")
            logger.info("Continuing without knowledge graph...")
    
    logger.info("✓ Ingestion complete! Outputs saved to outputs/")
    logger.info(f"  - Vector embeddings: FAISS index with {len(chunks)} chunks")
    logger.info(f"  - Knowledge graph: {len(entities)} entities, {len(relations)} relations")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to document file to ingest (PDF, TXT, images, etc.)")
    parser.add_argument("--ade-api-key", help="Optional Landing AI API key for ADE fallback", default=None)
    parser.add_argument("--no-kg", action="store_true", help="Skip knowledge graph building")
    args = parser.parse_args()
    
    # Try to get ADE API key from environment if not provided
    ade_api_key = args.ade_api_key or os.environ.get("ADE_API_KEY")
    if ade_api_key:
        logger.info("ADE API key found - will use as fallback for complex documents")
    else:
        logger.info("No ADE API key - using free parsers only")
    
    os.makedirs("outputs", exist_ok=True)
    main(args.input, ade_api_key=ade_api_key, build_kg=not args.no_kg)
