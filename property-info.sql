SELECT
    CONCAT('P', pi_property_id) as id,
    CONVERT(pi_type, CHAR CHARACTER SET utf8) as type
FROM
    wb_property_info
ORDER BY id;
