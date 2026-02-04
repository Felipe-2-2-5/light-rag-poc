from neo4j import GraphDatabase
import json
import os
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def create_entities(tx, eid, props):
    tx.run("""
        MERGE (e:Entity {eid:$eid})
        SET e.name = $name, e.type = $type, e.source_chunk = $source_chunk
    """, eid=eid, name=props.get("label"), type=props.get("type"), source_chunk=props.get("source_chunk"))

def create_relation(tx, a, rel, b):
    tx.run("""
        MATCH (a:Entity {eid:$a}), (b:Entity {eid:$b})
        MERGE (a)-[r:REL {type:$rel}]->(b)
        SET r.first_seen = coalesce(r.first_seen, timestamp())
    """, a=a, b=b, rel=rel)

def create_chunk_node(tx, chunk_id, text, doc_id=None):
    tx.run("""
        MERGE (c:Chunk {chunk_id:$chunk_id})
        SET c.text = $text, c.doc_id = $doc_id
    """, chunk_id=chunk_id, text=text, doc_id=doc_id)

def link_entity_to_chunk(tx, eid, chunk_id):
    tx.run("""
        MATCH (e:Entity {eid:$eid}), (c:Chunk {chunk_id:$chunk_id})
        MERGE (e)-[:MENTIONED_IN]->(c)
    """, eid=eid, chunk_id=chunk_id)

def run():
    ents = json.load(open("outputs/entities.json", encoding="utf-8"))
    rels = json.load(open("outputs/relations.json", encoding="utf-8"))
    meta = json.load(open("outputs/meta.json", encoding="utf-8")) if os.path.exists("outputs/meta.json") else {}
    with driver.session() as session:
        for eid, props in ents.items():
            session.write_transaction(create_entities, eid, props)
        # create chunk nodes from vector metadata
        for i, m in meta.items():
            # meta keys are string indices in our Faiss wrapper; convert accordingly
            chunk_id = m.get("chunk_id")
            text = m.get("text")[:2000] if m.get("text") else ""
            session.write_transaction(create_chunk_node, chunk_id, text, doc_id=None)
        # link entities to chunks & create relations
        for a, rel, b in rels:
            try:
                session.write_transaction(create_relation, a, rel, b)
            except Exception as e:
                print("Relation create error:", e)
        # link entities to chunks based on stored source_chunk
        for eid, props in ents.items():
            sc = props.get("source_chunk")
            chunk_id = f"vn_law_sample.txt_C{sc}"
            session.write_transaction(link_entity_to_chunk, eid, chunk_id)
    print("KG population complete.")

if __name__ == "__main__":
    run()
