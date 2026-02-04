from neo4j import GraphDatabase
from pyvis.network import Network
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def fetch_graph(limit=200):
    q = """
    MATCH (e:Entity)-[r:REL]->(o:Entity)
    RETURN e.eid AS a, e.name AS a_name, type(r) as rel, o.eid AS b, o.name AS b_name
    LIMIT $limit
    """
    with driver.session() as session:
        res = session.run(q, limit=limit)
        return [dict(r) for r in res]

def make_pyvis(nodes_edges, out_html="outputs/graph.html"):
    net = Network(notebook=False, height="800px", width="100%", directed=True)
    added = {}
    for r in nodes_edges:
        a = r['a']; a_name = r.get('a_name') or a
        b = r['b']; b_name = r.get('b_name') or b
        if a not in added:
            net.add_node(a, label=a_name, title=a_name, color="#97C2FC")
            added[a] = True
        if b not in added:
            net.add_node(b, label=b_name, title=b_name, color="#FFA807")
            added[b] = True
        net.add_edge(a, b, title=r.get('rel','REL'))
    net.show(out_html)
    print(f"Graph visualization written to {out_html}")

if __name__ == "__main__":
    rows = fetch_graph()
    if not rows:
        print("No relations found in Neo4j. Run kg_builder.py first.")
    else:
        make_pyvis(rows)
