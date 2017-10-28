SELECT
    CONVERT(p.page_title, CHAR CHARACTER SET utf8) AS title,
    DATE_FORMAT(CAST(r.rev_timestamp AS DATETIME), '%Y-%m-%dT%TZ') AS modified,
    CONVERT(t.old_text, CHAR CHARACTER SET utf8) AS json_text

FROM
    page p
        INNER JOIN revision r
            ON p.page_latest = r.rev_id
        INNER JOIN text t
            ON r.rev_text_id = t.old_id

WHERE
        p.page_namespace IN (120, 122)
    AND r.rev_deleted = 0
    AND p.page_is_redirect = 0

ORDER BY
    p.page_title
;
