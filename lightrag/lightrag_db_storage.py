"""
LightRAG Database Storage Module

Stores LightRAG ingestion outputs (entities, relationships, chunks) into Neo4j
for efficient graph-based searching and querying.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from neo4j import GraphDatabase
from datetime import datetime

logger = logging.getLogger(__name__)


class LightRAGNeo4jStorage:
    """
    Saves LightRAG storage files to Neo4j database for efficient searching.
    
    Extracts data from:
    - kv_store_full_entities.json -> Entity nodes
    - kv_store_full_relations.json -> Relationship edges
    - kv_store_text_chunks.json -> Chunk nodes
    - vdb_entities.json -> Entity embeddings (optional)
    """
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """Initialize Neo4j connection"""
        try:
            self.driver = GraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"✓ Connected to Neo4j at {neo4j_uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def create_indexes(self):
        """Create Neo4j indexes for better search performance"""
        with self.driver.session() as session:
            # Entity indexes
            session.run("CREATE INDEX entity_name IF NOT EXISTS FOR (e:LightRAGEntity) ON (e.entity_name)")
            session.run("CREATE INDEX entity_type IF NOT EXISTS FOR (e:LightRAGEntity) ON (e.entity_type)")
            
            # Chunk indexes
            session.run("CREATE INDEX chunk_id IF NOT EXISTS FOR (c:LightRAGChunk) ON (c.chunk_id)")
            
            # Document indexes
            session.run("CREATE INDEX doc_id IF NOT EXISTS FOR (d:LightRAGDocument) ON (d.doc_id)")
            
            logger.info("✓ Created Neo4j indexes")
    
    def clear_lightrag_data(self):
        """Clear all LightRAG data from Neo4j (for fresh ingestion)"""
        with self.driver.session() as session:
            # Delete all LightRAG nodes and relationships
            session.run("""
                MATCH (n)
                WHERE n:LightRAGEntity OR n:LightRAGChunk OR n:LightRAGDocument
                DETACH DELETE n
            """)
            logger.info("✓ Cleared existing LightRAG data from Neo4j")
    
    def load_storage_files(self, working_dir: str) -> Dict[str, Any]:
        """Load LightRAG storage files"""
        working_path = Path(working_dir)
        
        storage_data = {
            'entities': {},
            'relations': {},
            'chunks': {},
            'documents': {},
        }
        
        # Load entities
        entities_file = working_path / "kv_store_full_entities.json"
        if entities_file.exists():
            with open(entities_file, 'r', encoding='utf-8') as f:
                storage_data['entities'] = json.load(f)
            logger.info(f"✓ Loaded {len(storage_data['entities'])} entities")
        
        # Load relations
        relations_file = working_path / "kv_store_full_relations.json"
        if relations_file.exists():
            with open(relations_file, 'r', encoding='utf-8') as f:
                storage_data['relations'] = json.load(f)
            logger.info(f"✓ Loaded {len(storage_data['relations'])} relations")
        
        # Load chunks
        chunks_file = working_path / "kv_store_text_chunks.json"
        if chunks_file.exists():
            with open(chunks_file, 'r', encoding='utf-8') as f:
                storage_data['chunks'] = json.load(f)
            logger.info(f"✓ Loaded {len(storage_data['chunks'])} chunks")
        
        # Load documents
        docs_file = working_path / "kv_store_full_docs.json"
        if docs_file.exists():
            with open(docs_file, 'r', encoding='utf-8') as f:
                storage_data['documents'] = json.load(f)
            logger.info(f"✓ Loaded {len(storage_data['documents'])} documents")
        
        return storage_data
    
    def save_entities_to_neo4j(self, entities: Dict[str, Any]):
        """Save entities to Neo4j as nodes"""
        with self.driver.session() as session:
            count = 0
            for entity_name, entity_data in entities.items():
                try:
                    # Extract entity properties
                    entity_type = entity_data.get('entity_type', 'UNKNOWN')
                    description = entity_data.get('description', '')
                    source_id = entity_data.get('source_id', '')
                    
                    # Create entity node
                    session.run("""
                        MERGE (e:LightRAGEntity {entity_name: $entity_name})
                        SET e.entity_type = $entity_type,
                            e.description = $description,
                            e.source_id = $source_id,
                            e.updated_at = datetime()
                    """, 
                        entity_name=entity_name,
                        entity_type=entity_type,
                        description=description,
                        source_id=source_id
                    )
                    count += 1
                    
                    if count % 100 == 0:
                        logger.info(f"  Saved {count} entities...")
                        
                except Exception as e:
                    logger.warning(f"Failed to save entity {entity_name}: {e}")
            
            logger.info(f"✓ Saved {count} entities to Neo4j")
    
    def save_relations_to_neo4j(self, relations: Dict[str, Any]):
        """Save relationships to Neo4j as edges"""
        with self.driver.session() as session:
            count = 0
            for relation_key, relation_data in relations.items():
                try:
                    # Extract relation properties
                    src_id = relation_data.get('src_id', '')
                    tgt_id = relation_data.get('tgt_id', '')
                    relation_type = relation_data.get('relation_type', 'RELATED_TO')
                    description = relation_data.get('description', '')
                    weight = relation_data.get('weight', 1.0)
                    
                    if not src_id or not tgt_id:
                        continue
                    
                    # Create relationship between entities
                    session.run("""
                        MATCH (src:LightRAGEntity {entity_name: $src_id})
                        MATCH (tgt:LightRAGEntity {entity_name: $tgt_id})
                        MERGE (src)-[r:LIGHTRAG_RELATION {relation_key: $relation_key}]->(tgt)
                        SET r.relation_type = $relation_type,
                            r.description = $description,
                            r.weight = $weight,
                            r.updated_at = datetime()
                    """,
                        src_id=src_id,
                        tgt_id=tgt_id,
                        relation_key=relation_key,
                        relation_type=relation_type,
                        description=description,
                        weight=weight
                    )
                    count += 1
                    
                    if count % 100 == 0:
                        logger.info(f"  Saved {count} relations...")
                        
                except Exception as e:
                    logger.warning(f"Failed to save relation {relation_key}: {e}")
            
            logger.info(f"✓ Saved {count} relations to Neo4j")
    
    def save_chunks_to_neo4j(self, chunks: Dict[str, Any]):
        """Save text chunks to Neo4j and link to entities"""
        with self.driver.session() as session:
            count = 0
            for chunk_id, chunk_data in chunks.items():
                try:
                    # Extract chunk properties
                    content = chunk_data.get('content', '')
                    tokens = chunk_data.get('tokens', 0)
                    chunk_order_index = chunk_data.get('chunk_order_index', 0)
                    full_doc_id = chunk_data.get('full_doc_id', '')
                    
                    # Create chunk node
                    session.run("""
                        MERGE (c:LightRAGChunk {chunk_id: $chunk_id})
                        SET c.content = $content,
                            c.tokens = $tokens,
                            c.chunk_order_index = $chunk_order_index,
                            c.full_doc_id = $full_doc_id,
                            c.updated_at = datetime()
                    """,
                        chunk_id=chunk_id,
                        content=content[:10000],  # Limit content size
                        tokens=tokens,
                        chunk_order_index=chunk_order_index,
                        full_doc_id=full_doc_id
                    )
                    
                    # Link chunk to document
                    if full_doc_id:
                        session.run("""
                            MATCH (c:LightRAGChunk {chunk_id: $chunk_id})
                            MERGE (d:LightRAGDocument {doc_id: $doc_id})
                            MERGE (c)-[:PART_OF]->(d)
                        """,
                            chunk_id=chunk_id,
                            doc_id=full_doc_id
                        )
                    
                    count += 1
                    
                    if count % 50 == 0:
                        logger.info(f"  Saved {count} chunks...")
                        
                except Exception as e:
                    logger.warning(f"Failed to save chunk {chunk_id}: {e}")
            
            logger.info(f"✓ Saved {count} chunks to Neo4j")
    
    def link_entities_to_chunks(self, working_dir: str):
        """Link entities to chunks based on entity_chunks mapping"""
        working_path = Path(working_dir)
        entity_chunks_file = working_path / "kv_store_entity_chunks.json"
        
        if not entity_chunks_file.exists():
            logger.warning("Entity-chunk mapping file not found, skipping linking")
            return
        
        with open(entity_chunks_file, 'r', encoding='utf-8') as f:
            entity_chunks = json.load(f)
        
        with self.driver.session() as session:
            count = 0
            for entity_name, chunk_ids in entity_chunks.items():
                try:
                    if isinstance(chunk_ids, str):
                        chunk_ids = json.loads(chunk_ids)
                    
                    for chunk_id in chunk_ids:
                        session.run("""
                            MATCH (e:LightRAGEntity {entity_name: $entity_name})
                            MATCH (c:LightRAGChunk {chunk_id: $chunk_id})
                            MERGE (e)-[:MENTIONED_IN]->(c)
                        """,
                            entity_name=entity_name,
                            chunk_id=chunk_id
                        )
                        count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to link entity {entity_name}: {e}")
            
            logger.info(f"✓ Linked {count} entity-chunk relationships")
    
    def save_lightrag_to_neo4j(self, working_dir: str, clear_existing: bool = False):
        """
        Main method to save all LightRAG data to Neo4j
        
        Args:
            working_dir: Path to LightRAG storage directory
            clear_existing: Whether to clear existing data before saving
        """
        logger.info("\n" + "=" * 80)
        logger.info("Saving LightRAG Data to Neo4j")
        logger.info("=" * 80)
        
        # Create indexes
        self.create_indexes()
        
        # Clear existing data if requested
        if clear_existing:
            self.clear_lightrag_data()
        
        # Load storage files
        logger.info("\n⏳ Loading LightRAG storage files...")
        storage_data = self.load_storage_files(working_dir)
        
        # Save to Neo4j
        logger.info("\n⏳ Saving entities to Neo4j...")
        self.save_entities_to_neo4j(storage_data['entities'])
        
        logger.info("\n⏳ Saving relationships to Neo4j...")
        self.save_relations_to_neo4j(storage_data['relations'])
        
        logger.info("\n⏳ Saving chunks to Neo4j...")
        self.save_chunks_to_neo4j(storage_data['chunks'])
        
        logger.info("\n⏳ Linking entities to chunks...")
        self.link_entities_to_chunks(working_dir)
        
        logger.info("\n✓ LightRAG data successfully saved to Neo4j!")
        
        # Print statistics
        self.print_neo4j_statistics()
    
    def print_neo4j_statistics(self):
        """Print statistics about stored data"""
        with self.driver.session() as session:
            # Count entities
            result = session.run("MATCH (e:LightRAGEntity) RETURN count(e) as count")
            entity_count = result.single()['count']
            
            # Count relations
            result = session.run("MATCH ()-[r:LIGHTRAG_RELATION]->() RETURN count(r) as count")
            relation_count = result.single()['count']
            
            # Count chunks
            result = session.run("MATCH (c:LightRAGChunk) RETURN count(c) as count")
            chunk_count = result.single()['count']
            
            # Count documents
            result = session.run("MATCH (d:LightRAGDocument) RETURN count(d) as count")
            doc_count = result.single()['count']
            
            logger.info("\n" + "=" * 80)
            logger.info("Neo4j Storage Statistics")
            logger.info("=" * 80)
            logger.info(f"  Entities: {entity_count:,}")
            logger.info(f"  Relations: {relation_count:,}")
            logger.info(f"  Chunks: {chunk_count:,}")
            logger.info(f"  Documents: {doc_count:,}")


def save_lightrag_to_database(
    working_dir: str,
    neo4j_uri: str = "bolt://localhost:7687",
    neo4j_user: str = "neo4j",
    neo4j_password: str = "test",
    clear_existing: bool = False
):
    """
    Convenience function to save LightRAG data to Neo4j
    
    Args:
        working_dir: Path to LightRAG storage directory
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        clear_existing: Whether to clear existing data
    """
    with LightRAGNeo4jStorage(neo4j_uri, neo4j_user, neo4j_password) as storage:
        storage.save_lightrag_to_neo4j(working_dir, clear_existing=clear_existing)


if __name__ == "__main__":
    # Example usage
    import sys
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    # Get Neo4j credentials from environment
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "test")
    
    working_dir = sys.argv[1] if len(sys.argv) > 1 else "./lightrag_storage"
    
    # Save to Neo4j
    save_lightrag_to_database(
        working_dir=working_dir,
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        clear_existing=True
    )
