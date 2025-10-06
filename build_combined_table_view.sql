CREATE OR REPLACE VIEW `flu-project-473220.combined_data.combined_table` AS
WITH region_state AS (
  SELECT region_id AS region,
         state
  FROM `flu-project-473220.google_trends.HHS-regions-to-states`,
       UNNEST(states) AS state
)
SELECT
    f.region,
    f.week_start,
    f.wili,
    t.flu,
    t.fever,
    t.cough,
    t.`flu symptoms` AS flu_symptoms,
    t.`sore throat`  AS sore_throat,
    t.doordash AS doordash,
    t.postmates AS postmates
FROM `flu-project-473220.flu_data.flu_data` AS f
JOIN region_state      AS rs
       ON f.region = rs.region
JOIN `flu-project-473220.google_trends.country_trends` AS t
       ON rs.state = t.state
      AND f.week_start = CAST(t.date AS DATE);
