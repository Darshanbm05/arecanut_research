from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/processed/karnataka_integrated_taluk_rainfall_groundwater_2016_2025.csv"
OUT_T = ROOT / "outputs/tables"
OUT_M = ROOT / "outputs/maps"
OUT_T.mkdir(parents=True, exist_ok=True)
OUT_M.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INPUT)
df = df[df["Year"].between(2016, 2025)].copy()

# Exclude only the flagged JJAS/annual inconsistencies from rainfall trend calculations.
rain = df[df["Rainfall_Consistency_Flag"].fillna("OK").eq("OK")].copy()

# Annual statewide summaries; groundwater estimates and observations are reported separately.
annual = df.groupby("Year").agg(
    Mean_Annual_Rainfall_mm=("Mean_Rainfall_mm", "mean"),
    Mean_JJAS_Rainfall_mm=("Mean_Monsoon_Rainfall_mm", "mean"),
    Taluks_Rainfall=("Taluk", "nunique")
).reset_index()

gw_all = df.groupby("Year").agg(
    Mean_Static_Water_Level_All_m_bgl=("Static_Water_Level_m", "mean"),
    Taluks_With_GW=("Static_Water_Level_m", "count")
).reset_index()
gw_obs = (df[df["Data_Quality"].eq("Observed")]
          .groupby("Year")["Static_Water_Level_m"].mean()
          .rename("Mean_Static_Water_Level_Observed_m_bgl").reset_index())
annual = annual.merge(gw_all, on="Year", how="left").merge(gw_obs, on="Year", how="left")
annual.to_csv(OUT_T / "statewide_annual_summary_2016_2025.csv", index=False)

# Linear trend slopes by taluk. Slopes are descriptive, not causal.
def slope(group, col):
    x = group["Year"].to_numpy(dtype=float)
    y = group[col].to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 5:
        return np.nan
    return float(np.polyfit(x[mask], y[mask], 1)[0])

rows = []
for taluk, g in df.groupby("Taluk"):
    gr = rain[rain["Taluk"].eq(taluk)]
    rows.append({
        "Taluk": taluk,
        "Annual_Rainfall_Trend_mm_per_year": slope(gr, "Mean_Rainfall_mm"),
        "JJAS_Rainfall_Trend_mm_per_year": slope(gr, "Mean_Monsoon_Rainfall_mm"),
        "Groundwater_Level_Trend_m_bgl_per_year": slope(g, "Static_Water_Level_m"),
        "Groundwater_Observed_Years": int(g.loc[g["Data_Quality"].eq("Observed"), "Static_Water_Level_m"].notna().sum()),
        "Groundwater_Estimated_Years": int(g.loc[g["Data_Quality"].eq("Estimated"), "Static_Water_Level_m"].notna().sum())
    })
trends = pd.DataFrame(rows)
trends.to_csv(OUT_T / "taluk_trends_2016_2025.csv", index=False)

# Groundwater year-to-year change (positive = deeper water table; negative = shallower).
gw = df.pivot_table(index="Taluk", columns="Year", values="Static_Water_Level_m", aggfunc="mean")
if 2016 in gw.columns and 2025 in gw.columns:
    change = (gw[2025] - gw[2016]).rename("Change_2016_to_2025_m_bgl").reset_index()
    change["Interpretation"] = np.where(change["Change_2016_to_2025_m_bgl"] > 0,
                                         "Water table deeper", "Water table shallower or unchanged")
    change.to_csv(OUT_T / "groundwater_change_2016_2025.csv", index=False)

# Charts
def line_chart(x, ys, labels, title, ylabel, filename):
    fig, ax = plt.subplots(figsize=(9, 5))
    for y, label in zip(ys, labels):
        ax.plot(annual["Year"], annual[y], marker="o", linewidth=2, label=label)
    ax.set_title(title)
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_M / filename, dpi=300)
    plt.close(fig)

line_chart(None,
    ["Mean_Annual_Rainfall_mm", "Mean_JJAS_Rainfall_mm"],
    ["Annual rainfall", "JJAS rainfall"],
    "Karnataka: Mean Taluk Rainfall (2016–2025)",
    "Rainfall (mm)", "chart_01_rainfall_trend_2016_2025.png")

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(annual["Year"], annual["Mean_Static_Water_Level_Observed_m_bgl"],
        marker="o", label="Observed records only")
ax.plot(annual["Year"], annual["Mean_Static_Water_Level_All_m_bgl"],
        marker="s", linestyle="--", label="Observed + estimated")
ax.set_title("Karnataka: Mean Static Groundwater Level (2016–2025)")
ax.set_xlabel("Year")
ax.set_ylabel("Depth below ground level (m bgl)")
ax.grid(True, alpha=.3)
ax.legend()
fig.tight_layout()
fig.savefig(OUT_M / "chart_02_groundwater_trend_2016_2025.png", dpi=300)
plt.close(fig)

# Rainfall-groundwater association at taluk-year level; descriptive correlation only.
corr_data = df[df["Rainfall_Consistency_Flag"].fillna("OK").eq("OK")][["Mean_Monsoon_Rainfall_mm", "Static_Water_Level_m", "Data_Quality"]].dropna()
corr_observed = corr_data[corr_data["Data_Quality"].eq("Observed")]
corr = pd.DataFrame([
    {"Subset": "Observed groundwater only", "Records": len(corr_observed),
     "Pearson_r": corr_observed["Mean_Monsoon_Rainfall_mm"].corr(corr_observed["Static_Water_Level_m"])},
    {"Subset": "Observed + estimated groundwater", "Records": len(corr_data),
     "Pearson_r": corr_data["Mean_Monsoon_Rainfall_mm"].corr(corr_data["Static_Water_Level_m"])}
])
corr.to_csv(OUT_T / "rainfall_groundwater_correlation.csv", index=False)

print("ANALYSIS COMPLETE")
print(f"Taluks analysed: {df['Taluk'].nunique()}")
print(f"Years: {df['Year'].min()}-{df['Year'].max()}")
print(f"Rainfall rows excluded from trend due to consistency flag: {len(df)-len(rain)}")
print("\\nStatewide annual summary:")
print(annual.round(2).to_string(index=False))
print("\\nCorrelation (descriptive only):")
print(corr.round(3).to_string(index=False))
