from neo4j import GraphDatabase
import json
import time

print("=" * 60)
print("بارگذاری یال‌ها در Neo4j")
print("=" * 60)

DATA_FILE = '../data.json'
BATCH_SIZE = 5000

try:
    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "4570176501")
    )
    
    with driver.session() as session:
        total = 0
        edge_batch = []
        
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except:
                    continue
                
                if 'datum' not in record:
                    continue
                
                datum = record['datum']
                for key, value in datum.items():
                    if 'Event' in key and isinstance(value, dict):
                        event = value
                        subject_uuid = None
                        object_uuid = None
                        
                        if 'subject' in event and event['subject']:
                            for k, v in event['subject'].items():
                                if 'UUID' in k:
                                    subject_uuid = v
                                    break
                        
                        if 'predicateObject' in event and event['predicateObject']:
                            for k, v in event['predicateObject'].items():
                                if 'UUID' in k:
                                    object_uuid = v
                                    break
                        
                        if subject_uuid and object_uuid:
                            edge_batch.append({
                                'src': subject_uuid,
                                'dst': object_uuid,
                                'type': event.get('type', 'UNKNOWN'),
                                'ts': event.get('timestampNanos', 0)
                            })
                            total += 1
                
                if len(edge_batch) >= BATCH_SIZE:
                    session.run(
                        """
                        UNWIND $edges AS row
                        MATCH (src:Node {uuid: row.src})
                        MATCH (dst:Node {uuid: row.dst})
                        CREATE (src)-[r:EDGE {type: row.type, ts: row.ts}]->(dst)
                        """,
                        edges=edge_batch
                    )
                    edge_batch = []
                    if total % 50000 == 0:
                        print(f"   {total} یال بارگذاری شد...")
            
            if edge_batch:
                session.run(
                    """
                    UNWIND $edges AS row
                    MATCH (src:Node {uuid: row.src})
                    MATCH (dst:Node {uuid: row.dst})
                    CREATE (src)-[r:EDGE {type: row.type, ts: row.ts}]->(dst)
                    """,
                    edges=edge_batch
                )
    
    driver.close()
    print(f"✅ Neo4j: {total} یال بارگذاری شد")
    
except Exception as e:
    print(f"❌ خطا: {e}")
