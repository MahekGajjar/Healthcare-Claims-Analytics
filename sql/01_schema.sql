-- 01_schema.sql
-- Star schema for the Healthcare Claims Analytics warehouse.
-- Fact table: claims.  Dimensions: members, providers, plans, diagnoses.
-- Written for DuckDB / standard SQL; load the CSVs in data/ before querying.

CREATE TABLE plans (
    plan_id          VARCHAR PRIMARY KEY,
    plan_name        VARCHAR,
    plan_type        VARCHAR,           -- HMO, PPO, EPO, Medicare Advantage, HDHP
    monthly_premium  DECIMAL(8,2)
);

CREATE TABLE diagnoses (
    diagnosis_code   VARCHAR PRIMARY KEY,
    description      VARCHAR,
    chronic_flag     INTEGER,           -- 1 = chronic condition
    cost_multiplier  DECIMAL(5,2)
);

CREATE TABLE providers (
    provider_id      VARCHAR PRIMARY KEY,
    provider_name    VARCHAR,
    specialty        VARCHAR,
    region           VARCHAR
);

CREATE TABLE members (
    member_id        VARCHAR PRIMARY KEY,
    first_name       VARCHAR,
    last_name        VARCHAR,
    gender           VARCHAR,
    age              INTEGER,
    region           VARCHAR,
    plan_id          VARCHAR REFERENCES plans(plan_id),
    enrollment_date  DATE
);

CREATE TABLE claims (
    claim_id         VARCHAR PRIMARY KEY,
    member_id        VARCHAR REFERENCES members(member_id),
    provider_id      VARCHAR REFERENCES providers(provider_id),
    service_date     DATE,
    claim_type       VARCHAR,           -- Inpatient, Outpatient, Professional, Pharmacy, Emergency
    diagnosis_code   VARCHAR REFERENCES diagnoses(diagnosis_code),
    billed_amount    DECIMAL(12,2),
    allowed_amount   DECIMAL(12,2),
    paid_amount      DECIMAL(12,2),
    claim_status     VARCHAR            -- Paid, Denied
);
