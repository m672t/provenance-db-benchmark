-- Accelerates selection of source process nodes.
CREATE INDEX IF NOT EXISTS idx_q4_nodes_type_uuid
    ON nodes (type, uuid);

ANALYZE nodes;
ANALYZE edges;
