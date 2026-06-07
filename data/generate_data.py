"""
generate_data.py
-----------------
Generates a realistic synthetic healthcare claims dataset for the
Healthcare Claims Analytics project.

The data follows a star schema:
    fact:  claims
    dims:  members, providers, plans, diagnoses

All randomness is seeded so the dataset is fully reproducible.
Run:  python generate_data.py
"""

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

# ----------------------------------------------------------------------
# Reference / configuration
# ----------------------------------------------------------------------
N_MEMBERS = 8000
N_PROVIDERS = 400
START = pd.Timestamp("2023-01-01")
END = pd.Timestamp("2024-12-31")

REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]

PLANS = [
    # plan_id, plan_name, plan_type, monthly_premium
    ("PL01", "Essential HMO",        "HMO",                220),
    ("PL02", "Premier PPO",          "PPO",                385),
    ("PL03", "Select EPO",           "EPO",                300),
    ("PL04", "Senior Advantage",     "Medicare Advantage", 165),
    ("PL05", "Value HDHP",           "HDHP",               180),
]

SPECIALTIES = [
    "Primary Care", "Cardiology", "Orthopedics", "Oncology",
    "Emergency Medicine", "Radiology", "Behavioral Health",
    "Endocrinology", "Nephrology", "General Surgery",
]

# diagnosis_code, description, chronic_flag, base_cost_multiplier
DIAGNOSES = [
    ("E11.9", "Type 2 diabetes mellitus",            1, 1.6),
    ("I10",   "Essential hypertension",               1, 1.2),
    ("J45.9", "Asthma",                               1, 1.3),
    ("N18.3", "Chronic kidney disease stage 3",       1, 2.4),
    ("I50.9", "Heart failure",                        1, 2.8),
    ("F32.9", "Major depressive disorder",            1, 1.4),
    ("M54.5", "Low back pain",                        0, 0.9),
    ("J06.9", "Acute upper respiratory infection",    0, 0.5),
    ("S93.4", "Ankle sprain",                         0, 0.7),
    ("Z00.0", "General medical examination",          0, 0.3),
    ("C50.9", "Breast cancer",                        1, 3.5),
    ("K21.9", "Gastro-esophageal reflux disease",     0, 0.8),
]

CLAIM_TYPES = ["Inpatient", "Outpatient", "Professional", "Pharmacy", "Emergency"]
CLAIM_TYPE_BASE = {
    "Inpatient": 14000,
    "Outpatient": 1800,
    "Professional": 320,
    "Pharmacy": 140,
    "Emergency": 2600,
}
CLAIM_TYPE_WEIGHTS = [0.05, 0.28, 0.40, 0.20, 0.07]

# ----------------------------------------------------------------------
# Dimension: plans
# ----------------------------------------------------------------------
plans = pd.DataFrame(PLANS, columns=["plan_id", "plan_name", "plan_type", "monthly_premium"])

# ----------------------------------------------------------------------
# Dimension: diagnoses
# ----------------------------------------------------------------------
diagnoses = pd.DataFrame(
    DIAGNOSES, columns=["diagnosis_code", "description", "chronic_flag", "cost_multiplier"]
)

# ----------------------------------------------------------------------
# Dimension: providers
# ----------------------------------------------------------------------
provider_rows = []
for i in range(1, N_PROVIDERS + 1):
    specialty = np.random.choice(SPECIALTIES)
    provider_rows.append(
        {
            "provider_id": f"PR{i:04d}",
            "provider_name": fake.company() + " " + np.random.choice(["Medical Group", "Clinic", "Health", "Associates"]),
            "specialty": specialty,
            "region": np.random.choice(REGIONS),
        }
    )
providers = pd.DataFrame(provider_rows)

# ----------------------------------------------------------------------
# Dimension: members
# ----------------------------------------------------------------------
plan_share = [0.24, 0.22, 0.16, 0.22, 0.16]
member_rows = []
for i in range(1, N_MEMBERS + 1):
    plan_id = np.random.choice(plans["plan_id"], p=plan_share)
    # Medicare Advantage skews older
    if plan_id == "PL04":
        age = int(np.clip(np.random.normal(72, 7), 65, 95))
    else:
        age = int(np.clip(np.random.normal(42, 15), 18, 64))
    enroll = START + pd.Timedelta(days=int(np.random.randint(0, 200)))
    member_rows.append(
        {
            "member_id": f"M{i:05d}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "gender": np.random.choice(["F", "M"]),
            "age": age,
            "region": np.random.choice(REGIONS),
            "plan_id": plan_id,
            "enrollment_date": enroll.date(),
        }
    )
members = pd.DataFrame(member_rows)

# ----------------------------------------------------------------------
# Fact: claims
# ----------------------------------------------------------------------
# Annual claim frequency per member depends on age + chronic burden.
# A small share of members are "high utilizers" driving cost concentration.
high_util = np.random.rand(N_MEMBERS) < 0.05  # top ~5%
claim_rows = []
claim_counter = 1

diag_codes = diagnoses["diagnosis_code"].values
diag_mult = dict(zip(diagnoses["diagnosis_code"], diagnoses["cost_multiplier"]))

for idx, m in members.iterrows():
    age = m["age"]
    base_freq = 2.5 + (age - 40) * 0.06
    if high_util[idx]:
        base_freq *= 6
    base_freq = max(base_freq, 0.5)
    n_claims = np.random.poisson(base_freq)

    for _ in range(n_claims):
        service_date = fake.date_between_dates(
            date_start=max(pd.Timestamp(m["enrollment_date"]), START).date(),
            date_end=END.date(),
        )
        ctype = np.random.choice(CLAIM_TYPES, p=CLAIM_TYPE_WEIGHTS)
        dcode = np.random.choice(diag_codes)
        provider = providers.sample(1).iloc[0]

        base = CLAIM_TYPE_BASE[ctype]
        mult = diag_mult[dcode]
        billed = base * mult * np.random.lognormal(0, 0.45)
        # Allowed amount is a contracted discount off billed
        allowed = billed * np.random.uniform(0.45, 0.75)
        # ~8% of claims denied -> paid 0
        denied = np.random.rand() < 0.08
        paid = 0.0 if denied else allowed * np.random.uniform(0.80, 1.0)

        claim_rows.append(
            {
                "claim_id": f"C{claim_counter:07d}",
                "member_id": m["member_id"],
                "provider_id": provider["provider_id"],
                "service_date": service_date,
                "claim_type": ctype,
                "diagnosis_code": dcode,
                "billed_amount": round(billed, 2),
                "allowed_amount": round(allowed, 2),
                "paid_amount": round(paid, 2),
                "claim_status": "Denied" if denied else "Paid",
            }
        )
        claim_counter += 1

claims = pd.DataFrame(claim_rows)

# ----------------------------------------------------------------------
# Write to CSV
# ----------------------------------------------------------------------
plans.to_csv("plans.csv", index=False)
diagnoses.to_csv("diagnoses.csv", index=False)
providers.to_csv("providers.csv", index=False)
members.to_csv("members.csv", index=False)
claims.to_csv("claims.csv", index=False)

print("Generated:")
print(f"  plans.csv      {len(plans):>8,} rows")
print(f"  diagnoses.csv  {len(diagnoses):>8,} rows")
print(f"  providers.csv  {len(providers):>8,} rows")
print(f"  members.csv    {len(members):>8,} rows")
print(f"  claims.csv     {len(claims):>8,} rows")
print(f"  total paid:    ${claims['paid_amount'].sum():,.0f}")
