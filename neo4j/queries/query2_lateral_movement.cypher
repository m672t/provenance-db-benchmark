// الگوی الماسی: دو پروسه متمایز که یک فایل مشترک را لمس کرده و به شبکه مشترک متصل شده‌اند
MATCH (p1:Node {type: 'SUBJECT_PROCESS'})-[e1:EDGE]->(f:Node {type: 'FILE_OBJECT_BLOCK'})
MATCH (p2:Node {type: 'SUBJECT_PROCESS'})-[e2:EDGE]->(f)
MATCH (p1)-[e3:EDGE]->(n:Node {type: 'NetFlowObject'})
MATCH (p2)-[e4:EDGE]->(n)
WHERE p1.uuid <> p2.uuid
RETURN DISTINCT 
    p1.uuid AS process1, 
    p2.uuid AS process2, 
    f.uuid AS shared_file, 
    n.uuid AS shared_network;