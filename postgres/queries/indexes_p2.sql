-- ایندکس‌های بهینه‌سازی کوئری‌های ۲ و ۳
CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
CREATE INDEX IF NOT EXISTS idx_edges_src_dst ON edges(src, dst);
CREATE INDEX IF NOT EXISTS idx_edges_ts ON edges(ts);