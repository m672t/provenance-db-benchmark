DROP INDEX IF EXISTS idx_q4_nodes_type_uuid;
DROP INDEX IF EXISTS idx_q4_edges_src_dst_type;
DROP INDEX IF EXISTS idx_q4_edges_dst_src_type;

ANALYZE nodes;
ANALYZE edges;
