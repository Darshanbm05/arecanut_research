from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"data/processed/karnataka_arecanut_district_1997_2023.csv"
OUT=ROOT/"outputs/tables"; MAP=ROOT/"outputs/maps"
OUT.mkdir(parents=True,exist_ok=True); MAP.mkdir(parents=True,exist_ok=True)
df=pd.read_csv(SRC)
df=df.sort_values(["District","Year_start"])

# District-level year-over-year dataset: retain original reporting gaps.
state=df.groupby("Year",as_index=False).agg(
    Total_Area_ha=("Area_ha","sum"),
    Total_Production_t=("Production_t","sum"),
    Mean_District_Yield_t_ha=("Yield_t_ha","mean"),
    Districts_Reported=("District","nunique")
)
state.to_csv(OUT/"arecanut_statewide_summary_by_year.csv",index=False)

# District trend slopes; minimum three observations to avoid unstable fits.
rows=[]
for dist,g in df.groupby("District"):
    row={"District":dist,"Years_Reported":len(g),
         "First_Year":g["Year"].iloc[0],"Latest_Year":g["Year"].iloc[-1]}
    for col,label in [("Area_ha","Area"),("Production_t","Production"),("Yield_t_ha","Yield")]:
        if len(g)>=3:
            row[label+"_Trend_per_year"]=float(np.polyfit(g["Year_start"],g[col],1)[0])
        else: row[label+"_Trend_per_year"]=np.nan
    rows.append(row)
pd.DataFrame(rows).to_csv(OUT/"arecanut_district_trends.csv",index=False)

latest=df["Year_start"].max()
latest_rows=df[df["Year_start"].eq(latest)].copy()
latest_rows.to_csv(OUT/"arecanut_latest_district_comparison.csv",index=False)

def chart(x,y,title,ylabel,file):
    fig,ax=plt.subplots(figsize=(10,5))
    ax.plot(x,y,marker="o",linewidth=2)
    ax.set_title(title); ax.set_xlabel("Agricultural year"); ax.set_ylabel(ylabel)
    ax.tick_params(axis="x",rotation=45); ax.grid(True,alpha=.3)
    fig.tight_layout(); fig.savefig(MAP/file,dpi=300); plt.close(fig)

chart(state["Year"],state["Total_Area_ha"],"Karnataka Arecanut Cultivated Area by Year","Area (hectares)","chart_03_arecanut_area_trend.png")
chart(state["Year"],state["Total_Production_t"],"Karnataka Arecanut Production by Year","Production (tonnes)","chart_04_arecanut_production_trend.png")
chart(state["Year"],state["Mean_District_Yield_t_ha"],"Average Reported District Arecanut Yield","Yield (tonnes/hectare)","chart_05_arecanut_yield_trend.png")

print("ARECANUT ANALYSIS COMPLETE")
print("Source records:",len(df)," | Districts:",df["District"].nunique(),
      " | Years:",df["Year"].nunique()," | Year range:",df["Year_start"].min(),"-",df["Year_start"].max())
print("\\nLatest reported agricultural year:",latest_rows["Year"].iloc[0])
print(latest_rows[["District","Area_ha","Production_t","Yield_t_ha"]].sort_values("Area_ha",ascending=False).head(10).round(2).to_string(index=False))
print("\\nStatewide yearly totals:")
print(state.round(2).to_string(index=False))
