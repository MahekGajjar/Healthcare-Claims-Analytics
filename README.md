# Healthcare Claims & Cost Analytics

This project simulates an enterprise health insurer environment using synthetic claims and membership data. The goal is to analyze healthcare costs, high-cost members, and provider performance using SQL, Data Modeling, and Interactive Dashboards.

## 1. Business Goal

Health plans need to answer questions like:

- Which conditions and member segments drive the highest costs?
- Which providers and specialties are associated with higher per-member-per-month (PMPM) costs?
- How do costs trend over time by plan type, region, and age group?
- Who are the "high-cost members" and what patterns do they share?

## 2. Tech Stack

- **Database / SQL**: (to be finalized – e.g., PostgreSQL / SQL Server / BigQuery style SQL)
- **Analytics / Dashboards**: Power BI or Tableau
- **Data Modeling**: Star schema (fact & dimension tables)
- **Documentation**: Markdown (this README), data dictionary

## 3. Data Model (Star Schema – Draft)

### fact_claims

- `claim_id`
- `member_id`
- `provider_id`
- `service_date_id`
- `paid_amount`
- `allowed_amount`
- `diagnosis_code`
- `procedure_code`
- `place_of_service`
- `claim_status`

### dim_member

- `member_id`
- `gender`
- `age_group`
- `state`
- `plan_type`
- `product_line` (e.g., Commercial, Medicare, Medicaid)

### dim_provider

- `provider_id`
- `provider_type` (facility, professional)
- `specialty`
- `state`
- `network_flag` (in-network / out-of-network)

### dim_date

- `date_id`
- `date`
- `month`
- `quarter`
- `year`

## 4. Planned Analyses

- **PMPM (Per Member Per Month)** cost by:
  - Product line, plan type, region, age group
- **High-Cost Members**:
  - Identify members above specific cost thresholds
- **Condition-Level Insights**:
  - Paid amount by diagnosis category
- **Provider Performance**:
  - Cost and utilization by specialty and provider type
- **Trend Analysis**:
  - Year-over-year and month-over-month cost trends

## 5. Repository Structure (Planned)

- `data/` – synthetic claims & membership datasets (CSV)
- `sql/` – DDL and analytical SQL queries
- `dashboards/` – Power BI / Tableau files + screenshots
- `docs/` – data dictionary, ERD diagrams
- `images/` – exported images used in documentation

## 6. Status

This project is currently in progress. The first milestone is to:
- Finalize the star schema design
- Generate synthetic data consistent with the model
- Load the data into a database and write core cost analytics queries

Once that is complete, I will add dashboards and more documentation.

