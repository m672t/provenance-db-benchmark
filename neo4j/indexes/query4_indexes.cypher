CREATE INDEX node_type IF NOT EXISTS
FOR (node:Node)
ON (node.type);
