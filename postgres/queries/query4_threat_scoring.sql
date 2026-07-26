WITH threat_metrics AS (
    SELECT
        target.uuid AS target_uuid,
        target.type AS target_type,

        COUNT(DISTINCT source.uuid)
            AS distinct_source_processes,

        COUNT(*) FILTER (
            WHERE edge.type = 'EVENT_EXECUTE'
        ) AS execute_count,

        COUNT(*) FILTER (
            WHERE edge.type = 'EVENT_WRITE'
        ) AS write_count

    FROM edges AS edge

    JOIN nodes AS source
        ON source.uuid = edge.src
       AND source.type = 'SUBJECT_PROCESS'

    JOIN nodes AS target
        ON target.uuid = edge.dst

    GROUP BY
        target.uuid,
        target.type
)

SELECT
    target_uuid,
    target_type,
    distinct_source_processes,
    execute_count,
    write_count,

    (
        5 * distinct_source_processes
        + 10 * execute_count
        + 2 * write_count
    ) AS threat_score

FROM threat_metrics

ORDER BY
    threat_score DESC,
    target_uuid ASC;
