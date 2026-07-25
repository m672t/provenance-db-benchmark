WITH RECURSIVE path AS (
    SELECT 
        src AS start_node,
        src,
        dst,
        type,
        1 AS depth
    FROM edges
    WHERE src IN (SELECT uuid FROM nodes WHERE type = 'SUBJECT_PROCESS')
      AND type IN ('EVENT_EXECUTE', 'EVENT_CONNECT')
    
    UNION ALL
    
    SELECT 
        p.start_node,
        e.src,
        e.dst,
        e.type,
        p.depth + 1
    FROM edges e
    JOIN path p ON e.src = p.dst
    WHERE p.depth < 6
      AND e.type IN ('EVENT_EXECUTE', 'EVENT_CONNECT')
)
SELECT DISTINCT start_node
FROM path
WHERE depth = 6
  AND dst IN (SELECT uuid FROM nodes WHERE type IN ('FILE_OBJECT_BLOCK', 'NetFlowObject'));
