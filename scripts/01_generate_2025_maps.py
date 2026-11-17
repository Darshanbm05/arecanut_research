from pathlib import Path
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = ROOT / "data/boundaries/karnataka_taluk_gis_ready_2025.gpkg"
DATA = ROOT / "data/processed/karnataka_integrated_taluk_rainfall_groundwater_2001_2025.csv"
OUT = ROOT / "outputs/maps"
OUT.mkdir(parents=True, exist_ok=True)

gdf = gpd.read_file(BOUNDARY)
df = pd.read_csv(DATA)

# Use the 2025 records and join to boundary using the stable normalized taluk key.
d = df[df["Year"] == 2025].copy()
d["Taluk_Key"] = d["Taluk"].astype(str).str.lower().str.replace(r"[^a-z0-9]", "", regex=True)
gdf["Taluk_Key"] = gdf["Taluk_Key"].astype(str).str.lower().str.replace(r"[^a-z0-9]", "", regex=True)

# Keep one record per key; stop rather than silently duplicate spatial features.
if d["Taluk_Key"].duplicated().any():
    raise ValueError("Duplicate taluk keys in 2025 table. Inspect before mapping.")
joined = gdf.merge(d, on="Taluk_Key", how="left", suffixes=("", "_table"))

if len(joined) != len(gdf):
    raise ValueError("Join changed the number of taluk polygons.")
print(f"Taluk polygons: {len(gdf)}")
print(f"Taluks with rainfall values: {joined['Mean_Rainfall_mm'].notna().sum()}")
print(f"Taluks with groundwater values: {joined['Static_Water_Level_m'].notna().sum()}")

def draw_map(column, title, filename, cmap):
    fig, ax = plt.subplots(figsize=(9, 10))
    joined.plot(column=column, ax=ax, legend=True, cmap=cmap,
                missing_kwds={"color": "lightgrey", "label": "No data"},
                edgecolor="white", linewidth=0.15,
                legend_kwds={"shrink": 0.65})
    ax.set_title(title, fontsize=14, pad=14)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(OUT / filename, dpi=300, bbox_inches="tight")
    plt.close(fig)

draw_map("Mean_Rainfall_mm", "Karnataka Taluk-wise Annual Rainfall (2025)",
         "map_01_annual_rainfall_2025.png", "Blues")
draw_map("Mean_Monsoon_Rainfall_mm", "Karnataka Taluk-wise JJAS Rainfall (2025)",
         "map_02_jjas_rainfall_2025.png", "YlGnBu")
draw_map("Static_Water_Level_m", "Karnataka Taluk-wise Static Groundwater Level (2025)",
         "map_03_static_groundwater_level_2025.png", "YlOrBr")

# Export joined 2025 attribute table for easy inspection.
joined.drop(columns="geometry").to_csv(ROOT / "outputs/tables/taluk_joined_2025.csv", index=False)
print("Maps and joined table exported.")
