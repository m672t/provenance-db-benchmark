// ایندکس‌های بهینه‌سازی کوئری‌های ۲ و ۳
CREATE INDEX node_type_idx IF NOT EXISTS FOR (n:Node) ON (n.type);
// ایندکس روی ویژگی ts یال‌ها برای تسریع در مرتب‌سازی
CREATE INDEX edge_ts_idx IF NOT EXISTS FOR ()-[e:EDGE]-() ON (e.ts);