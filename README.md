# OE_SEAT Karnataka: Groundwater, Rainfall and Arecanut Sustainability

## Project approach
All GIS processing and map generation are performed in Python. QGIS is not required.

## Folder structure
- `data/raw/`: original downloaded/source files
- `data/boundaries/`: cleaned taluk boundary GeoPackage
- `data/processed/`: integrated rainfall and groundwater tables
- `scripts/`: repeatable processing and mapping scripts
- `outputs/maps/`: exported thematic maps
- `outputs/tables/`: derived summary tables
- `reports/`: report/presentation material

## Current prepared data
- Integrated annual and JJAS rainfall + groundwater table: 2001–2025
- Groundwater static water level: 2016–2025
- Taluk boundaries: 240 polygons, repaired GIS-ready GeoPackage

## Run
Install dependencies:
```bash
python -m pip install -r requirements.txt
```
Generate the first map set:
```bash
python scripts/01_generate_2025_maps.py
```

## Important interpretation notes
- Rainfall is an approximate taluk mean from intersecting 0.25-degree IMD grid cells.
- Static groundwater level is in metres below ground level (m bgl). A larger number means a deeper water table.
- Groundwater values marked `Estimated` are proxies, not direct taluk observations.
- Rainfall records with `CHECK_JJAS_EXCEEDS_ANNUAL` should be reviewed before drawing conclusions.
- District-level arecanut statistics must remain district-level; do not infer taluk-level crop values.

## Phase 7: integrated district assessment
Run:
```bash
python scripts/04_integrated_sustainability_assessment.py
```
This aggregates taluk rainfall and static groundwater to districts, then joins district-level arecanut statistics. Crop data remains district-level. The crop series overlaps the available rainfall/groundwater period only from 2016 onward. Ramanagara is not matched in the current district crosswalk and should remain explicitly unmatched until its historical district boundary relationship is verified. CGWB groundwater extraction-stage data is not included in this integration yet.

## CGWB groundwater stress (2024)
The official CGWB/GWD Karnataka 2024 report Annexure IX (A) and IX (B) has been extracted into:
`data/processed/cgwb_karnataka_taluk_groundwater_resources_2024_237_units.csv`
It contains 237 assessment units and includes recharge, annual extractable groundwater resource, sector-wise extraction, stage of groundwater extraction (%) and official category.
Boundary join output:
- `data/boundaries/karnataka_taluk_cgwb_2024.gpkg`
- `outputs/tables/taluk_cgwb_groundwater_stress_2024_join.csv`
- `outputs/tables/cgwb_boundary_match_audit.csv`
- `outputs/maps/map_04_cgwb_groundwater_category_2024.png`
Only 151 of 240 boundary taluks matched directly using district and taluk names after basic normalization and known district-name harmonization. Unmatched boundary taluks are left null; no categories are invented or copied.
Official report category counts: 144 Safe, 33 Semi Critical, 15 Critical, 45 Over Exploited (237 units total). Statewide stage of extraction: 68.44%.


## Reviewed CGWB 2024 taluk matching (17 Nov 2026)
- Reviewed 240 current taluk polygons against the 237 CGWB 2024 assessment units.
- 151 records retained as original direct matches; 84 additional records matched using official CGWB assessment-unit names and spelling/transliteration variants.
- 5 remaining boundary taluks use the nearest matched taluk within the same district as a clearly labelled proxy: Arakera, Terdal, Manchenahalli, Chelur, and Bangarpet. Proxy distances are measured between polygon centroids in the projected boundary CRS.
- Proxy values are NOT direct CGWB observations for those five taluks. Keep `Match_Method`, `Confidence`, `Proxy_Taluk`, and `Distance_km` fields in all analysis and maps.
- Reviewed table: `outputs/tables/taluk_cgwb_groundwater_stress_2024_join_reviewed.csv`.
- Reviewed GeoPackage: `data/boundaries/karnataka_taluk_cgwb_2024_reviewed.gpkg`.


## Integrated CGWB–arecanut–climate analysis (17 Nov 2026)
- Added district-level CGWB category summary from reviewed taluk join, excluding five proxy taluks from direct category percentages.
- Added `outputs/tables/district_arecanut_rainfall_groundwater_CGWB_2022_23.csv` combining 2022-23 district arecanut indicators, 2016-2023 mean rainfall/static groundwater, and 2024 CGWB stress summaries.
- Added `outputs/tables/cgwb_district_stress_summary_2024.csv` and `outputs/tables/cgwb_stress_arecanut_climate_correlations_2022_23.csv`.
- Exploratory correlations are based on 23 matched districts and are not causal. Crop data is district-level; groundwater category data is 2024; rainfall/static water level averages cover 2016-2023. These time windows differ.
