MATCH (source:Node {type: 'SUBJECT_PROCESS'})
      -[edge:EDGE]->
      (target:Node)

WITH
    target,

    count(DISTINCT source)
        AS distinct_source_processes,

    sum(
        CASE
            WHEN edge.type = 'EVENT_EXECUTE' THEN 1
            ELSE 0
        END
    ) AS execute_count,

    sum(
        CASE
            WHEN edge.type = 'EVENT_WRITE' THEN 1
            ELSE 0
        END
    ) AS write_count

WITH
    target,
    distinct_source_processes,
    execute_count,
    write_count,

    (
        5 * distinct_source_processes
        + 10 * execute_count
        + 2 * write_count
    ) AS threat_score

RETURN
    target.uuid AS target_uuid,
    target.type AS target_type,
    distinct_source_processes,
    execute_count,
    write_count,
    threat_score

ORDER BY
    threat_score DESC,
    target_uuid ASC;
