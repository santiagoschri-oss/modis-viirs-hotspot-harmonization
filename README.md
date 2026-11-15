# Harmonized MODIS + VIIRS hotspots 

Submission to the **2026 NASA Space Apps Challenge** (Asunción, Paraguay) · Challenge: *Harmonization of MODIS and VIIRS Hot Spots*.

**Live app:** `<PASTE STREAMLIT URL HERE>`

## What it does

A web app that turns MODIS (since 2000) and VIIRS (since 2012) active-fire detections into one consistent monthly series, so that the sensor of origin no longer matters. The user chooses a rectangular area and a month range, and the app shows the harmonized hotspot counts with an uncertainty band and reliability flags.

Current coverage: Paraguay, 0.25° grid, 2000-11 to 2026-11.

## Method

1. **Data.** NASA FIRMS archive downloads for Paraguay: MODIS C6.1 (Terra + Aqua) and VIIRS S-NPP (SUOMI VIIRS C2, 375 m). Standard-processing files are used for the archive and near-real-time (NRT) files for the most recent months.
2. **Filtering.** MODIS: confidence ≥ 30 (nominal or high) and `type == 0` (presumed vegetation fire). VIIRS: confidence `n` or `h` and `type == 0`. Duplicates removed.
3. **Gridding.** Each detection is assigned to a 0.25° cell (`y = floor((90 − lat)/0.25)`, `x = floor((lon + 180)/0.25)`) and counted per month and sensor.
4. **Harmonization.** One sensor per period, so the only splice point is 2012-02:
   - 2000-11 → 2002-06: Terra only (Aqua starts in 2002-07), scaled by the monthly (Terra + Aqua)/Terra ratio of 2003–2004. **Flagged as estimated.**
   - 2002-07 → 2012-01: observed MODIS (Terra + Aqua).
   - 2012-02 onward: VIIRS divided by a monthly-calendar factor (VIIRS/MODIS), calibrated on 2012-02 to 2025-12. VIIRS counts about 3.0 to 3.7 times MODIS depending on the month.
5. **Uncertainty.** Relative error between converted VIIRS and MODIS follows `RMS ≈ 0.94 · N^−0.245` (log-log fit on N ≥ 7, where N is the hotspot count of the selection on the MODIS scale). Selections with N < 7 are flagged as low reliability and shown without an error bar.

## Validation

Factor calibrated on 2013–2019 and tested on 2020–2025 (years it never saw), national level:

| Metric | Value |
|---|---|
| Total bias | +3.1 % |
| Mean monthly error | 9.5 % |
| Correlation | 0.993 |

By region (western Chaco / eastern region): bias +2.8 % / −1.3 %, correlation 0.991 / 0.994.

## Limitations

- The error law measures how much converted VIIRS and MODIS disagree. **It is not the error against actual fire.**
- The 20 Terra-only months (2000-11 to 2002-06) cannot be validated. The Terra+Aqua/Terra ratio fell from 3.47 (2003) to 2.48 (2011), so the true early ratio could be as high or higher than the one used. No upper bound is known.
- Calibration and the error law were tested on Paraguay only. Expanding to other regions requires recalibrating the monthly factor and repeating the fit.
- Cell-level error is larger than national-level error because there are few hotspots per cell and month; the N < 7 flag covers this.
- Counts are not corrected for cloud cover or missing data.
- Months from 2026-08 onward come from NRT data and are provisional. November 2026 is incomplete.
- Converting VIIRS to the MODIS scale does not exploit VIIRS's finer 375 m detail.
- The absence of a step at 2012-02 is partly true by construction, since the factor was calibrated on a window that includes 2012–2013. The independent evidence is the 2020–2025 validation above.

## Repository contents

| File | Purpose |
|---|---|
| `app.py` | Streamlit app |
| `tabla_armonizada.csv` | Harmonized table (`cy`, `cx`, `mes`, `conteo_eq`, `origen`, `provisorio`); `origen` is the source of each value |
| `requirements.txt` | Python dependencies |
| `harmonitazion.ipynb` | Code that produces the harmonized table and the uncertainty analysis |

Cell centers: `lat = 89.875 − 0.25·cy`, `lon = −179.875 + 0.25·cx`. The table only contains cell-months with at least one detection; missing combinations are zero from the start of each period.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Reproduce the table

Request the raw files from the FIRMS Archive Download page (Country → Paraguay; MODIS and VIIRS S-NPP; 2000-11-01 / 2012-01-20 to the latest date; CSV), then run the notebook. Raw FIRMS files are not included in this repository because of their size.

## Data sources

- NASA FIRMS (Fire Information for Resource Management System): MODIS Collection 6.1 and VIIRS S-NPP active fire data.
- MODIS Collection 6 Active Fire Product User's Guide (confidence classes and `type` field).

## Use of AI tools

AI assistance (Claude, by Anthropic) was used throughout this project for planning, writing and debugging the data-processing code in the notebook and the Streamlit app, and for drafting this README. The author ran all code, checked the outputs against the data, and made the design decisions. Numbers reported here come from the notebook outputs.

## Reused prior work

None

## Team

tatAI by Francisco Moreno
