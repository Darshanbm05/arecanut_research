from pathlib import Path
import re
import numpy as np
import pandas as pd
import geopandas as gpd

ROOT=Path(__file__).resolve().parents[1]
RAIN=ROOT/"data/processed/karnataka_integrated_taluk_rainfall_groundwater_2016_2025.csv"
GW=ROOT/"data/processed/karnataka_taluk_groundwater_static_2016_2025_final.csv"
CROP=ROOT/"data/processed/karnataka_arecanut_district_1997_2023.csv"
BOUND=ROOT/"data/boundaries/karnataka_taluk_gis_ready_2025.gpkg"
OUT=ROOT/"outputs/tables"; OUT.mkdir(parents=True,exist_ok=True)

def norm(v): return re.sub(r"[^a-z0-9]","",str(v).lower())
rain=pd.read_csv(RAIN); gw=pd.read_csv(GW); crop=pd.read_csv(CROP)
boundary=gpd.read_file(BOUND)
boundary["key"]=boundary["KGISTalukN"].map(norm)
rain["key"]=rain["Taluk"].map(norm)
rain=rain.merge(boundary[["key","KGISDistri"]].drop_duplicates("key"),on="key",how="left")
cross=gw[["Source_Taluk","District"]].dropna().drop_duplicates()
cross["key"]=cross["Source_Taluk"].map(norm)
code_names=boundary[["key","KGISDistri"]].drop_duplicates().merge(cross,on="key",how="inner")
code_to_district=code_names.groupby("KGISDistri")["District"].agg(lambda x:x.value_counts().index[0]).to_dict()
rain["District"]=rain["KGISDistri"].map(code_to_district)
district_rain=rain.groupby(["District","Year"],as_index=False).agg(
    District_Mean_Annual_Rainfall_mm=("Mean_Rainfall_mm","mean"),
    District_Mean_JJAS_Rainfall_mm=("Mean_Monsoon_Rainfall_mm","mean"),
    Taluks_Rainfall_Contributing=("Taluk","nunique"))
district_gw=gw.groupby(["District","Year"],as_index=False).agg(
    District_Mean_Static_Water_Level_m_bgl=("Static_Water_Level_m","mean"),
    Estimated_GW_Records=("Data_Quality",lambda x:(x=="Estimated").sum()))
climate=district_rain.merge(district_gw,on=["District","Year"],how="left")
aliases={"belgaum":"Belagavi","bijapur":"Vijayapur","chamarajanagar":"Chamrajnagar",
"chikballapur":"Chikkaballapura","dakshin kannad":"Dakshina Kannada","davangere":"Davanagere",
"gulbarga":"Kalaburgi","uttar kannad":"Uttar Kannada","vijayanagar":"Vijayanagara",
"bangalore rural":"Bangalore Rural","bengaluru urban":"Bangalore Urban"}
crop["District_Source"]=crop["District"]
crop["District"]=crop["District"].apply(lambda x:aliases.get(str(x).strip().lower(),x))
crop["Year"]=crop["Year_start"].astype(int)
integrated=crop.merge(climate,on=["District","Year"],how="left")
integrated["Climate_GW_Match_Status"]=np.where(integrated["District_Mean_Annual_Rainfall_mm"].notna(),"Matched district-year","No district-year match")
integrated.to_csv(OUT/"karnataka_integrated_district_arecanut_rainfall_groundwater_2016_2023.csv",index=False)
print("Integrated dataset saved. Crop rows:",len(integrated))
print("District-year matches:",integrated["Climate_GW_Match_Status"].eq("Matched district-year").sum())
print("Note: Crop records before 2016 have no overlapping climate/GW period.")
