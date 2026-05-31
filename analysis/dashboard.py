"""
dashboard.py
------------
Builds the dashboard PNGs for the Healthcare Claims Analytics project.
Reads the CSVs in ../data, runs aggregate queries with DuckDB, and renders
three dashboard "pages" into ../images.

Run:  python dashboard.py
"""

import duckdb
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib import font_manager  # noqa: F401

# ----------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------
INK = "#1A2B3C"
ACCENT = "#0E7C7B"
ACCENT2 = "#E8743B"
MUTED = "#8895A7"
GRID = "#E3E8EE"
PALETTE = ["#0E7C7B", "#2E86AB", "#E8743B", "#5B8C5A", "#9B6A9E", "#C6973F"]

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": GRID,
    "axes.linewidth": 0.8,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.titlecolor": INK,
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

con = duckdb.connect()
for t in ["plans", "diagnoses", "providers", "members", "claims"]:
    con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto('../data/{t}.csv')")


def q(sql):
    return con.execute(sql).df()


def money(x, pos=None):
    if abs(x) >= 1e6:
        return f"${x/1e6:.1f}M"
    if abs(x) >= 1e3:
        return f"${x/1e3:.0f}K"
    return f"${x:.0f}"


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def kpi(ax, value, label):
    ax.axis("off")
    ax.text(0.5, 0.62, value, ha="center", va="center", fontsize=22,
            fontweight="bold", color=ACCENT)
    ax.text(0.5, 0.22, label, ha="center", va="center", fontsize=10, color=MUTED)
    for s in ax.spines.values():
        s.set_visible(False)


# ======================================================================
# PAGE 1 — Executive Overview
# ======================================================================
fig = plt.figure(figsize=(13, 7.5))
fig.suptitle("Healthcare Claims Analytics  ·  Executive Overview",
             fontsize=16, fontweight="bold", x=0.07, ha="left", y=0.97)
gs = fig.add_gridspec(3, 4, height_ratios=[0.6, 1.2, 1.2], hspace=0.5, wspace=0.35,
                      left=0.07, right=0.96, top=0.88, bottom=0.08)

tot = q("SELECT COUNT(*) c, SUM(paid_amount) p FROM claims").iloc[0]
mem = q("SELECT COUNT(*) c FROM members").iloc[0].c
avg_claim = tot.p / tot.c
kpi(fig.add_subplot(gs[0, 0]), f"${tot.p/1e6:.1f}M", "Total Paid")
kpi(fig.add_subplot(gs[0, 1]), f"{int(tot.c):,}", "Total Claims")
kpi(fig.add_subplot(gs[0, 2]), f"{int(mem):,}", "Members")
kpi(fig.add_subplot(gs[0, 3]), f"${avg_claim:,.0f}", "Avg Paid / Claim")

# Quarterly trend
ax = fig.add_subplot(gs[1, :2])
trend = q("""SELECT YEAR(service_date)||'-Q'||QUARTER(service_date) AS period,
             SUM(paid_amount) p FROM claims GROUP BY 1 ORDER BY 1""")
ax.plot(trend.period, trend.p, color=ACCENT, marker="o", linewidth=2.2)
ax.fill_between(range(len(trend)), trend.p, color=ACCENT, alpha=0.08)
ax.set_title("Paid Claims by Quarter")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(money))
ax.tick_params(axis="x", rotation=45)
style_ax(ax)

# Spend by claim type
ax = fig.add_subplot(gs[1, 2:])
ct = q("""SELECT claim_type, SUM(paid_amount) p FROM claims
          GROUP BY 1 ORDER BY p DESC""")
ax.barh(ct.claim_type[::-1], ct.p[::-1], color=ACCENT)
ax.set_title("Paid by Service Category")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(money))
style_ax(ax)
ax.grid(axis="x", color=GRID, linewidth=0.8)

# Cost concentration
ax = fig.add_subplot(gs[2, :2])
conc = q("""WITH mc AS (SELECT member_id, SUM(paid_amount) p FROM claims GROUP BY 1),
            r AS (SELECT p, NTILE(20) OVER (ORDER BY p DESC) v FROM mc)
            SELECT CASE WHEN v=1 THEN 'Top 5%' ELSE 'Other 95%' END g,
            SUM(p) p FROM r GROUP BY 1""")
colors = [ACCENT2 if g == "Top 5%" else GRID for g in conc.g]
wedges, _, autotexts = ax.pie(conc.p, labels=conc.g, colors=colors,
                              autopct="%1.0f%%", startangle=90,
                              wedgeprops=dict(width=0.42, edgecolor="white"))
for t_ in autotexts:
    t_.set_color(INK); t_.set_fontweight("bold")
ax.set_title("Spend Concentration: Top 5% of Members")

# Chronic vs acute
ax = fig.add_subplot(gs[2, 2:])
ch = q("""SELECT CASE WHEN d.chronic_flag=1 THEN 'Chronic' ELSE 'Acute/Other' END t,
          SUM(c.paid_amount) p FROM claims c JOIN diagnoses d
          ON c.diagnosis_code=d.diagnosis_code GROUP BY 1 ORDER BY p DESC""")
ax.bar(ch.t, ch.p, color=[ACCENT, MUTED], width=0.55)
ax.set_title("Chronic vs. Acute Spend")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(money))
style_ax(ax)

fig.savefig("../images/dashboard_executive_overview.png", dpi=130, bbox_inches="tight")
plt.close(fig)

# ======================================================================
# PAGE 2 — Cost Drivers
# ======================================================================
fig = plt.figure(figsize=(13, 7.5))
fig.suptitle("Healthcare Claims Analytics  ·  Cost Drivers",
             fontsize=16, fontweight="bold", x=0.07, ha="left", y=0.97)
gs = fig.add_gridspec(2, 2, hspace=0.45, wspace=0.32,
                      left=0.07, right=0.96, top=0.88, bottom=0.12)

# Top diagnoses
ax = fig.add_subplot(gs[0, :])
dx = q("""SELECT d.description, SUM(c.paid_amount) p, MAX(d.chronic_flag) ch
          FROM claims c JOIN diagnoses d ON c.diagnosis_code=d.diagnosis_code
          GROUP BY 1 ORDER BY p DESC LIMIT 8""")
bar_colors = [ACCENT2 if c == 1 else ACCENT for c in dx.ch]
ax.barh(dx.description[::-1], dx.p[::-1], color=bar_colors[::-1])
ax.set_title("Top Diagnoses by Total Paid  (orange = chronic)")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(money))
style_ax(ax); ax.grid(axis="x", color=GRID, linewidth=0.8); ax.grid(axis="y", visible=False)

# Avg paid per claim by type
ax = fig.add_subplot(gs[1, 0])
ap = q("""SELECT claim_type, AVG(paid_amount) a FROM claims GROUP BY 1 ORDER BY a DESC""")
ax.bar(ap.claim_type, ap.a, color=ACCENT, width=0.6)
ax.set_title("Avg Paid per Claim by Type")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(money))
ax.tick_params(axis="x", rotation=35)
style_ax(ax)

# Paid per member by age band
ax = fig.add_subplot(gs[1, 1])
ab = q("""SELECT CASE WHEN age<30 THEN '18-29' WHEN age<45 THEN '30-44'
          WHEN age<65 THEN '45-64' ELSE '65+' END band,
          SUM(c.paid_amount)/COUNT(DISTINCT m.member_id) ppm
          FROM members m LEFT JOIN claims c ON c.member_id=m.member_id
          GROUP BY 1 ORDER BY 1""")
ax.plot(ab.band, ab.ppm, color=ACCENT2, marker="o", linewidth=2.4)
ax.set_title("Paid per Member by Age Band")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(money))
style_ax(ax)

fig.savefig("../images/dashboard_cost_drivers.png", dpi=130, bbox_inches="tight")
plt.close(fig)

# ======================================================================
# PAGE 3 — Plan Performance
# ======================================================================
fig = plt.figure(figsize=(13, 7.5))
fig.suptitle("Healthcare Claims Analytics  ·  Plan Performance",
             fontsize=16, fontweight="bold", x=0.07, ha="left", y=0.97)
gs = fig.add_gridspec(2, 2, hspace=0.45, wspace=0.32,
                      left=0.07, right=0.96, top=0.88, bottom=0.12)

# PMPM by plan type
ax = fig.add_subplot(gs[0, 0])
pmpm = q("""WITH mm AS (SELECT m.member_id, p.plan_type,
            DATE_DIFF('month', m.enrollment_date, DATE '2024-12-31')+1 mo
            FROM members m JOIN plans p ON m.plan_id=p.plan_id)
            SELECT mm.plan_type, SUM(c.paid_amount)/SUM(mm.mo) pmpm
            FROM mm LEFT JOIN claims c ON c.member_id=mm.member_id
            GROUP BY 1 ORDER BY pmpm DESC""")
ax.bar(pmpm.plan_type, pmpm.pmpm, color=ACCENT, width=0.6)
ax.set_title("PMPM by Plan Type")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(money))
ax.tick_params(axis="x", rotation=30)
style_ax(ax)

# Loss ratio by plan
ax = fig.add_subplot(gs[0, 1])
lr = q("""WITH mm AS (SELECT m.member_id, m.plan_id,
          DATE_DIFF('month', m.enrollment_date, DATE '2024-12-31')+1 mo FROM members m)
          SELECT p.plan_name, 100.0*SUM(c.paid_amount)/SUM(mm.mo*p.monthly_premium) lr
          FROM mm JOIN plans p ON mm.plan_id=p.plan_id
          LEFT JOIN claims c ON c.member_id=mm.member_id
          GROUP BY 1 ORDER BY lr DESC""")
ax.barh(lr.plan_name[::-1], lr.lr[::-1], color=ACCENT2)
ax.set_title("Loss Ratio by Plan (%)")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f"{x:.0f}%"))
style_ax(ax); ax.grid(axis="x", color=GRID, linewidth=0.8); ax.grid(axis="y", visible=False)

# Denial rate by claim type
ax = fig.add_subplot(gs[1, 0])
dr = q("""SELECT claim_type,
          100.0*SUM(CASE WHEN claim_status='Denied' THEN 1 ELSE 0 END)/COUNT(*) r
          FROM claims GROUP BY 1 ORDER BY r DESC""")
ax.bar(dr.claim_type, dr.r, color=MUTED, width=0.6)
ax.set_title("Claim Denial Rate by Type")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f"{x:.0f}%"))
ax.tick_params(axis="x", rotation=35)
style_ax(ax)

# Paid per member by region
ax = fig.add_subplot(gs[1, 1])
rg = q("""SELECT m.region, SUM(c.paid_amount)/COUNT(DISTINCT m.member_id) ppm
          FROM members m LEFT JOIN claims c ON c.member_id=m.member_id
          GROUP BY 1 ORDER BY ppm DESC""")
ax.bar(rg.region, rg.ppm, color=PALETTE[1], width=0.6)
ax.set_title("Paid per Member by Region")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(money))
ax.tick_params(axis="x", rotation=30)
style_ax(ax)

fig.savefig("../images/dashboard_plan_performance.png", dpi=130, bbox_inches="tight")
plt.close(fig)

print("Saved 3 dashboard pages to ../images/")
