WITH threat_metrics AS (
    SELECT
        edge.dst AS target_uuid,

        COUNT(DISTINCT edge.src)
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

    GROUP BY edge.dst
)

SELECT
    metrics.target_uuid,
    target.type AS target_type,
    metrics.distinct_source_processes,
    metrics.execute_count,
    metrics.write_count,

    (
        5 * metrics.distinct_source_processes
        + 10 * metrics.execute_count
        + 2 * metrics.write_count
    ) AS threat_score

FROM threat_metrics AS metrics

JOIN nodes AS target
    ON target.uuid = metrics.target_uuid

ORDER BY
    threat_score DESC,
    metrics.target_uuid ASC;
