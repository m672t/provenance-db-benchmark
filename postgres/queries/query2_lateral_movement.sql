-- الگوی الماسی: دو پروسه متمایز که یک فایل مشترک را لمس کرده و به شبکه مشترک متصل شده‌اند
SELECT DISTINCT 
    n1.uuid AS process1, 
    n2.uuid AS process2, 
    n3.uuid AS shared_file, 
    n4.uuid AS shared_network
FROM edges e1
JOIN edges e2 ON e1.dst = e2.dst
JOIN edges e3 ON e1.src = e3.src
JOIN edges e4 ON e2.src = e4.src AND e3.dst = e4.dst
JOIN nodes n1 ON e1.src = n1.uuid
JOIN nodes n2 ON e2.src = n2.uuid
JOIN nodes n3 ON e1.dst = n3.uuid
JOIN nodes n4 ON e3.dst = n4.uuid
WHERE n1.type = 'SUBJECT_PROCESS'
  AND n2.type = 'SUBJECT_PROCESS'
  AND n3.type = 'FILE_OBJECT_BLOCK'
  AND n4.type = 'NetFlowObject'
  AND e1.src != e2.src;