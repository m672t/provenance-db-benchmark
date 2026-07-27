-- محاسبه میانگین گپ زمانی (Beaconing) اتصالات یک پروسه به شبکه
WITH network_events AS (
    SELECT 
        e.src, 
        e.ts, 
        LAG(e.ts) OVER (PARTITION BY e.src, e.dst ORDER BY e.ts) as prev_ts
    FROM edges e
    JOIN nodes n1 ON e.src = n1.uuid
    JOIN nodes n2 ON e.dst = n2.uuid
    WHERE n1.type = 'SUBJECT_PROCESS' 
      AND n2.type = 'NetFlowObject'
)
SELECT 
    src AS process_uuid, 
    AVG(ts - prev_ts) AS avg_time_gap
FROM network_events
WHERE prev_ts IS NOT NULL
GROUP BY src
ORDER BY avg_time_gap ASC;