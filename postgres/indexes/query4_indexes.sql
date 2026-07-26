-- Locate source-process nodes efficiently.
CREATE INDEX IF NOT EXISTS idx_q4_nodes_type_uuid
    ON nodes (type, uuid);

-- Cover the edge columns required by Threat Scoring.
CREATE INDEX IF NOT EXISTS idx_q4_edges_src_dst_type
    ON edges (src, dst, type);

ANALYZE nodes;
ANALYZE edges;
