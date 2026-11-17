"""
Karnataka arecanut seasonal water-gap screening (district level)
Downloads monthly NASA POWER rainfall for district centroids and estimates
a preliminary dry-season irrigation gap using an explicit CPCRI-based scenario.

IMPORTANT:
- This is a screening scenario, not a calibrated crop water-balance model.
- Assumes 20 L/palm/day drip water, 2.7 m x 2.7 m spacing, Nov-May irrigation.
- Effective rainfall uses the simplified FAO monthly formula. It is not ideal
  for steep plantation slopes or detailed root-zone modelling.
- Does NOT estimate groundwater pumping or prove that groundwater supplies
  the gap. Compare the result separately with CGWB groundwater indicators.
"""

import time
import requests
import pandas as pd
import geopandas as gpd

BOUNDARY = "data/boundaries/karnataka_taluk_gis_ready_2025.gpkg"
OUT_MONTHLY = "data/processed/nasa_power_district_monthly_climate_2016_2023.csv"
OUT_BALANCE = "outputs/tables/arecanut_district_seasonal_water_gap_2016_2023.csv"

START_YEAR, END_YEAR = 2016, 2023
IRRIGATION_MONTHS = {11, 12, 1, 2, 3, 4, 5}
PALM_SPACING_M = 2.7
DRIP_LITRES_PALM_DAY = 20.0

DISTRICT_NAMES = {
    "01":"Belagavi","02":"Bagalkot","03":"Vijayapura","04":"Kalaburagi",
    "05":"Bidar","06":"Raichur","07":"Koppal","08":"Gadag","09":"Dharwad",
    "10":"Uttara Kannada","11":"Haveri","12":"Ballari","13":"Chitradurga",
    "14":"Shivamogga","15":"Davangere","16":"Udupi","17":"Chikkamagaluru",
    "18":"Tumakuru","19":"Kolar","20":"Bengaluru Urban","21":"Bengaluru Rural",
    "22":"Mandya","23":"Mysuru","24":"Dakshina Kannada","25":"Kodagu",
    "26":"Hassan","27":"Chamarajanagara","28":"Chikkaballapura",
    "29":"Ramanagara","30":"Yadgir","31":"Vijayanagara"
}

def effective_rainfall_mm(p_mm):
    # FAO simplified monthly effective rainfall formula
    if p_mm > 75:
        return max(0.0, 0.8 * p_mm - 25.0)
    return max(0.0, 0.6 * p_mm - 10.0)

def fetch_monthly(lat, lon):
    url = "https://power.larc.nasa.gov/api/temporal/monthly/point"
    params = {
        "parameters": "PRECTOTCORR",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": START_YEAR,
        "end": END_YEAR,
        "format": "JSON"
    }
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()
    values = payload["properties"]["parameter"]["PRECTOTCORR"]
    rows = []
    for key, value in values.items():
        if key.isdigit() and len(key) == 6 and float(value) > -900:
            year, month = int(key[:4]), int(key[4:])
            # NASA POWER may include month 13 as an annual aggregate.
            # This script needs monthly records only, so skip annual keys.
            if month < 1 or month > 12:
                continue
            # NASA POWER monthly PRECTOTCORR is an average daily rate (mm/day);
            # convert to monthly total using calendar days.
            days = pd.Period(f"{year}-{month:02d}").days_in_month
            rows.append({
                "Year": year, "Month": month,
                "Rainfall_mm": float(value) * days
            })
    return rows

def main():
    taluks = gpd.read_file(BOUNDARY)
    taluks["District_Code"] = (
        taluks["KGISDistri"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(2)
    )
    taluks["District"] = taluks["District_Code"].map(DISTRICT_NAMES)
    districts = taluks.dissolve(by=["District_Code", "District"], as_index=False)
    districts = districts.to_crs(4326)
    districts["centroid"] = districts.geometry.centroid
    districts["longitude"] = districts["centroid"].x
    districts["latitude"] = districts["centroid"].y

    climate_rows = []
    for _, row in districts.iterrows():
        print("Downloading:", row["District"])
        try:
            vals = fetch_monthly(row["latitude"], row["longitude"])
            for v in vals:
                v.update({
                    "District": row["District"],
                    "District_Code": row["District_Code"],
                    "Latitude": row["latitude"],
                    "Longitude": row["longitude"]
                })
                climate_rows.append(v)
        except Exception as exc:
            print("FAILED:", row["District"], exc)
        time.sleep(1.0)

    climate = pd.DataFrame(climate_rows)
    if climate.empty:
        raise RuntimeError("No NASA POWER data downloaded. Check internet/API response.")
    climate.to_csv(OUT_MONTHLY, index=False)

    # 20 L/palm/day converted to mm/day over 2.7 x 2.7 m spacing.
    palms_ha = 10000.0 / (PALM_SPACING_M ** 2)
    demand_mm_day = DRIP_LITRES_PALM_DAY * palms_ha / 10000.0

    climate["Effective_Rainfall_mm"] = climate["Rainfall_mm"].apply(effective_rainfall_mm)
    climate["Irrigation_Month"] = climate["Month"].isin(IRRIGATION_MONTHS)
    climate["Scenario_Demand_mm"] = climate.apply(
        lambda r: demand_mm_day * pd.Period(f'{int(r.Year)}-{int(r.Month):02d}').days_in_month
        if r["Irrigation_Month"] else 0.0, axis=1
    )
    climate["Effective_Rainfall_Credit_mm"] = climate.apply(
        lambda r: r["Effective_Rainfall_mm"] if r["Irrigation_Month"] else 0.0, axis=1
    )
    climate["Estimated_Irrigation_Gap_mm"] = (
        climate["Scenario_Demand_mm"] - climate["Effective_Rainfall_Credit_mm"]
    ).clip(lower=0)

    annual = (climate.groupby(["District", "District_Code", "Year"], as_index=False)
        .agg(DrySeason_Rainfall_mm=("Rainfall_mm",
             lambda s: float(s[climate.loc[s.index, "Irrigation_Month"]].sum())),
             Effective_Rainfall_Credit_mm=("Effective_Rainfall_Credit_mm", "sum"),
             Scenario_Demand_mm=("Scenario_Demand_mm", "sum"),
             Estimated_Irrigation_Gap_mm=("Estimated_Irrigation_Gap_mm", "sum")))
    annual["Estimated_Gap_MCM_per_1000ha"] = annual["Estimated_Irrigation_Gap_mm"] * 10.0
    annual.to_csv(OUT_BALANCE, index=False)
    print("Saved:", OUT_MONTHLY)
    print("Saved:", OUT_BALANCE)
    print("Demand assumption:", round(demand_mm_day, 3), "mm/day during Nov-May")
    print("Use the gap as a screening indicator only; do not label it measured groundwater demand.")

if __name__ == "__main__":
    main()
