DROP TABLE IF EXISTS edges CASCADE;
DROP TABLE IF EXISTS nodes CASCADE;

CREATE TABLE nodes (
    uuid UUID PRIMARY KEY,
    type VARCHAR(50) NOT NULL
);

CREATE TABLE edges (
    id SERIAL PRIMARY KEY,
    src UUID NOT NULL,
    dst UUID NOT NULL,
    type VARCHAR(50) NOT NULL,
    ts BIGINT NOT NULL,
    FOREIGN KEY (src) REFERENCES nodes(uuid) ON DELETE CASCADE,
    FOREIGN KEY (dst) REFERENCES nodes(uuid) ON DELETE CASCADE
);

CREATE INDEX idx_edges_src ON edges(src);
CREATE INDEX idx_edges_dst ON edges(dst);
CREATE INDEX idx_edges_type ON edges(type);
CREATE INDEX idx_nodes_type ON nodes(type);
CREATE INDEX idx_edges_src_type ON edges(src, type);
CREATE INDEX idx_edges_dst_type ON edges(dst, type);
