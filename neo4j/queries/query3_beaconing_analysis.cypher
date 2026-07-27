// محاسبه میانگین گپ زمانی (Beaconing) اتصالات یک پروسه به شبکه
MATCH (p:Node {type: 'SUBJECT_PROCESS'})-[e:EDGE]->(n:Node {type: 'NetFlowObject'})
WITH p, n, e ORDER BY e.ts
WITH p, n, collect(e.ts) AS times
WHERE size(times) > 1
UNWIND range(1, size(times)-1) AS i
WITH p, n, times[i] - times[i-1] AS gap
RETURN p.uuid AS process_uuid, avg(gap) AS avg_time_gap
ORDER BY avg_time_gap ASC;