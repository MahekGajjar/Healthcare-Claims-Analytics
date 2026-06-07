-- 02_analysis_queries.sql
-- Analytical queries answering the project's core business questions.
-- Each query is self-contained and runs against the star schema.

-- ----------------------------------------------------------------------
-- Q1. PMPM (Per Member Per Month) cost by plan type
--     Total paid divided by member-months of enrollment.
-- ----------------------------------------------------------------------
WITH member_months AS (
    SELECT
        m.member_id,
        p.plan_type,
        DATE_DIFF('month', m.enrollment_date, DATE '2024-12-31') + 1 AS months_enrolled
    FROM members m
    JOIN plans p ON m.plan_id = p.plan_id
)
SELECT
    mm.plan_type,
    COUNT(DISTINCT mm.member_id)               AS members,
    SUM(mm.months_enrolled)                     AS member_months,
    ROUND(SUM(c.paid_amount), 0)                AS total_paid,
    ROUND(SUM(c.paid_amount) / SUM(mm.months_enrolled), 2) AS pmpm
FROM member_months mm
LEFT JOIN claims c ON c.member_id = mm.member_id
GROUP BY mm.plan_type
ORDER BY pmpm DESC;

-- ----------------------------------------------------------------------
-- Q2. Top 5% highest-cost members and their share of total spend
-- ----------------------------------------------------------------------
WITH member_cost AS (
    SELECT member_id, SUM(paid_amount) AS member_paid
    FROM claims
    GROUP BY member_id
),
ranked AS (
    SELECT member_id, member_paid,
           NTILE(20) OVER (ORDER BY member_paid DESC) AS ventile
    FROM member_cost
)
SELECT
    CASE WHEN ventile = 1 THEN 'Top 5%' ELSE 'Bottom 95%' END AS cohort,
    COUNT(*)                                   AS members,
    ROUND(SUM(member_paid), 0)                 AS total_paid,
    ROUND(100.0 * SUM(member_paid) / SUM(SUM(member_paid)) OVER (), 1) AS pct_of_spend
FROM ranked
GROUP BY 1
ORDER BY total_paid DESC;

-- ----------------------------------------------------------------------
-- Q3. Provider cost ranking (top 10 by total paid)
-- ----------------------------------------------------------------------
SELECT
    pr.provider_id,
    pr.specialty,
    pr.region,
    COUNT(c.claim_id)              AS claim_count,
    ROUND(SUM(c.paid_amount), 0)   AS total_paid,
    ROUND(AVG(c.paid_amount), 0)   AS avg_paid_per_claim
FROM claims c
JOIN providers pr ON c.provider_id = pr.provider_id
GROUP BY pr.provider_id, pr.specialty, pr.region
ORDER BY total_paid DESC
LIMIT 10;

-- ----------------------------------------------------------------------
-- Q4. Quarterly cost trend
-- ----------------------------------------------------------------------
SELECT
    YEAR(service_date)                          AS yr,
    QUARTER(service_date)                       AS qtr,
    COUNT(*)                                    AS claims,
    ROUND(SUM(paid_amount), 0)                  AS total_paid
FROM claims
GROUP BY yr, qtr
ORDER BY yr, qtr;

-- ----------------------------------------------------------------------
-- Q5. Cost and volume by claim type (service category)
-- ----------------------------------------------------------------------
SELECT
    claim_type,
    COUNT(*)                                    AS claims,
    ROUND(SUM(paid_amount), 0)                  AS total_paid,
    ROUND(AVG(paid_amount), 0)                  AS avg_paid,
    ROUND(100.0 * SUM(paid_amount) / SUM(SUM(paid_amount)) OVER (), 1) AS pct_of_spend
FROM claims
GROUP BY claim_type
ORDER BY total_paid DESC;

-- ----------------------------------------------------------------------
-- Q6. Chronic vs non-chronic condition cost
-- ----------------------------------------------------------------------
SELECT
    CASE WHEN d.chronic_flag = 1 THEN 'Chronic' ELSE 'Acute / Other' END AS condition_type,
    COUNT(*)                                    AS claims,
    ROUND(SUM(c.paid_amount), 0)                AS total_paid,
    ROUND(AVG(c.paid_amount), 0)                AS avg_paid_per_claim
FROM claims c
JOIN diagnoses d ON c.diagnosis_code = d.diagnosis_code
GROUP BY 1
ORDER BY total_paid DESC;

-- ----------------------------------------------------------------------
-- Q7. Top diagnoses by total paid
-- ----------------------------------------------------------------------
SELECT
    d.diagnosis_code,
    d.description,
    d.chronic_flag,
    COUNT(*)                                    AS claims,
    ROUND(SUM(c.paid_amount), 0)                AS total_paid
FROM claims c
JOIN diagnoses d ON c.diagnosis_code = d.diagnosis_code
GROUP BY d.diagnosis_code, d.description, d.chronic_flag
ORDER BY total_paid DESC
LIMIT 10;

-- ----------------------------------------------------------------------
-- Q8. Claim denial rate overall and by claim type
-- ----------------------------------------------------------------------
SELECT
    claim_type,
    COUNT(*)                                    AS total_claims,
    SUM(CASE WHEN claim_status = 'Denied' THEN 1 ELSE 0 END) AS denied_claims,
    ROUND(100.0 * SUM(CASE WHEN claim_status = 'Denied' THEN 1 ELSE 0 END) / COUNT(*), 1) AS denial_rate_pct
FROM claims
GROUP BY claim_type
ORDER BY denial_rate_pct DESC;

-- ----------------------------------------------------------------------
-- Q9. Cost by member age band
-- ----------------------------------------------------------------------
SELECT
    CASE
        WHEN m.age < 30 THEN '18-29'
        WHEN m.age < 45 THEN '30-44'
        WHEN m.age < 65 THEN '45-64'
        ELSE '65+'
    END                                         AS age_band,
    COUNT(DISTINCT m.member_id)                 AS members,
    ROUND(SUM(c.paid_amount), 0)                AS total_paid,
    ROUND(SUM(c.paid_amount) / COUNT(DISTINCT m.member_id), 0) AS paid_per_member
FROM members m
LEFT JOIN claims c ON c.member_id = m.member_id
GROUP BY age_band
ORDER BY age_band;

-- ----------------------------------------------------------------------
-- Q10. Regional cost variation (paid per member by region)
-- ----------------------------------------------------------------------
SELECT
    m.region,
    COUNT(DISTINCT m.member_id)                 AS members,
    ROUND(SUM(c.paid_amount), 0)                AS total_paid,
    ROUND(SUM(c.paid_amount) / COUNT(DISTINCT m.member_id), 0) AS paid_per_member
FROM members m
LEFT JOIN claims c ON c.member_id = m.member_id
GROUP BY m.region
ORDER BY paid_per_member DESC;

-- ----------------------------------------------------------------------
-- Q11. Average billed-to-paid ratio (contractual discount) by claim type
-- ----------------------------------------------------------------------
SELECT
    claim_type,
    ROUND(SUM(paid_amount) / NULLIF(SUM(billed_amount), 0), 3) AS paid_to_billed_ratio,
    ROUND(SUM(allowed_amount) / NULLIF(SUM(billed_amount), 0), 3) AS allowed_to_billed_ratio
FROM claims
GROUP BY claim_type
ORDER BY paid_to_billed_ratio;

-- ----------------------------------------------------------------------
-- Q12. Plan-level cost vs premium revenue (loss ratio proxy)
-- ----------------------------------------------------------------------
WITH member_months AS (
    SELECT m.member_id, m.plan_id,
           DATE_DIFF('month', m.enrollment_date, DATE '2024-12-31') + 1 AS months_enrolled
    FROM members m
)
SELECT
    p.plan_name,
    p.plan_type,
    ROUND(SUM(mm.months_enrolled * p.monthly_premium), 0) AS premium_revenue,
    ROUND(SUM(c.paid_amount), 0)                           AS claims_paid,
    ROUND(100.0 * SUM(c.paid_amount) /
          NULLIF(SUM(mm.months_enrolled * p.monthly_premium), 0), 1) AS loss_ratio_pct
FROM member_months mm
JOIN plans p ON mm.plan_id = p.plan_id
LEFT JOIN claims c ON c.member_id = mm.member_id
GROUP BY p.plan_name, p.plan_type
ORDER BY loss_ratio_pct DESC;
