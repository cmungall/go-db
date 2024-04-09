CREATE TABLE gorule_violations_m AS
    SELECT * FROM gorule_violations;

CREATE TABLE IF NOT EXISTS gaf_association_plus_violations_m AS
SELECT a.*, string_agg(v.rule, ',') AS violations
FROM gaf_association a
LEFT JOIN gorule_violations_m v ON a.internal_id = v.internal_id
GROUP BY a.*;