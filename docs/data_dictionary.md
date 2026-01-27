# Data Dictionary (Draft)

This document will describe all tables and columns used in the project.

## Tables

- `fact_claims`
- `dim_member`
- `dim_provider`
- `dim_date`

---

## fact_claims (draft)

- `claim_id` – Unique identifier for each claim
- `member_id` – Links to `dim_member`
- `provider_id` – Links to `dim_provider`
- `service_date_id` – Links to `dim_date`
- `paid_amount` – Final paid amount for the claim
- `allowed_amount` – Allowed amount before member cost-sharing
- `diagnosis_code` – Primary diagnosis (ICD category or synthetic code)
- `procedure_code` – Procedure or service code
- `place_of_service` – Inpatient, outpatient, office, etc.
- `claim_status` – Paid / denied / adjusted

(We will expand this dictionary as the project progresses.)
