MATCH (start:Node {type: 'SUBJECT_PROCESS'})-[r:EDGE*6 {type: 'EVENT_EXECUTE'}]->(target:Node)
WHERE target.type IN ['FILE_OBJECT_BLOCK', 'NetFlowObject']
RETURN DISTINCT start.uuid AS StartNode;
