CREATE CONSTRAINT node_uuid IF NOT EXISTS FOR (n:Node) REQUIRE n.uuid IS UNIQUE;
CREATE INDEX node_type IF NOT EXISTS FOR (n:Node) ON (n.type);
CREATE INDEX edge_type IF NOT EXISTS FOR ()-[r:EDGE]-() ON (r.type);
