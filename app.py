from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from matplotlib.patches import Patch
import streamlit as st

A, B, N_MIN = 0.94, -0.245, 7      # relative error ≈ A·N^B, validated for N ≥ 7
COLORS = {"Terra_estimado": "#E69F00", "MODIS": "#0072B2", "VIIRS_eq": "#009E73", "mixto": "#7F7F7F"}
LABELS = {"Terra_estimado": "Terra only (estimated)", "MODIS": "MODIS (Terra + Aqua)",
          "VIIRS_eq": "VIIRS (converted to MODIS scale)", "mixto": "mixed sources"}

st.set_page_config(page_title="MODIS+VIIRS hotspot calendar", layout="wide")
st.title("Harmonized MODIS + VIIRS hotspots")

@st.cache_data
def load():
    df = pd.read_csv(Path(__file__).parent / "tabla_armonizada.csv")
    df["mes"] = pd.PeriodIndex(df["mes"], freq="M")
    df["lat"] = 89.875 - 0.25 * df.cy
    df["lon"] = -179.875 + 0.25 * df.cx
    return df

def source(m):
    if m < pd.Period("2002-07", "M"): return "Terra_estimado"
    if m < pd.Period("2012-02", "M"): return "MODIS"
    return "VIIRS_eq"

df = load()
all_months = pd.period_range("2000-11", df.mes.max(), freq="M")

# ---- Controls ----
sb = st.sidebar
sb.header("Area of interest (rectangle)")
lat_min = sb.number_input("Minimum latitude", value=-27.75, step=0.25)
lat_max = sb.number_input("Maximum latitude", value=-19.0, step=0.25)
lon_min = sb.number_input("Minimum longitude", value=-62.75, step=0.25)
lon_max = sb.number_input("Maximum longitude", value=-54.0, step=0.25)
options = [str(m) for m in all_months]
start, end = sb.select_slider("Month range", options=options, value=(options[0], options[-1]))
agg = sb.radio("Group by", ["Monthly", "Quarterly", "Yearly"])
freq, k, width = {"Monthly": ("M", 1, 20), "Quarterly": ("Q", 3, 80), "Yearly": ("Y", 12, 300)}[agg]

# ---- Selection and series ----
sel = df[df.lat.between(lat_min, lat_max) & df.lon.between(lon_min, lon_max)]
if sel.empty:
    st.warning("No cells with hotspots in that rectangle (the data cover Paraguay).")
    st.stop()
series = (sel.groupby("mes").conteo_eq.sum().reindex(all_months, fill_value=0.0)
             .loc[pd.Period(start, "M"):pd.Period(end, "M")])

g = pd.DataFrame({"n": series.values, "group": series.index.asfreq(freq),
                  "source": [source(m) for m in series.index],
                  "prov": series.index >= pd.Period("2026-08", "M")})
res = g.groupby("group").agg(n=("n", "sum"), months=("n", "size"), prov=("prov", "any"),
                             source=("source", lambda s: s.iat[0] if s.nunique() == 1 else "mixto"))
res["low"] = res.n < N_MIN
res["err"] = np.where(res.low, np.nan, res.n * A * np.maximum(res.n, 1e-9) ** B)

# ---- Chart ----
x = res.index.to_timestamp()
fig, ax = plt.subplots(figsize=(13, 4.5))
cols = [to_rgba(COLORS[o], 0.45 if p else 1.0) for o, p in zip(res.source, res.prov)]
bars = ax.bar(x, res.n, width=width, align="edge", color=cols, linewidth=0)
for b, low in zip(bars, res.low):
    if low:
        b.set_hatch("///"); b.set_edgecolor("black"); b.set_linewidth(0.3)
ok = ~res.low.to_numpy()
ax.errorbar(x[ok] + pd.Timedelta(days=width / 2), res.n.to_numpy()[ok],
            yerr=res.err.to_numpy()[ok], fmt="none", ecolor="black", elinewidth=0.8, capsize=1.5)
ax.set_ylabel("Hotspots (MODIS scale)")
ax.set_title(f"Hotspots in the selected area ({agg.lower()})")
legend = [Patch(color=COLORS[o], label=LABELS[o]) for o in res.source.unique()]
legend.append(Patch(facecolor="white", edgecolor="black", hatch="///", label=f"low reliability (N < {N_MIN})"))
if res.prov.any():
    legend.append(Patch(facecolor="grey", alpha=0.45, label="provisional (NRT)"))
ax.legend(handles=legend, loc="upper left", fontsize=8)
st.pyplot(fig)
plt.close(fig)

# ---- Metrics and caveats ----
c1, c2, c3 = st.columns(3)
c1.metric("Hotspots in range (MODIS scale)", f"{res.n.sum():,.0f}")
c2.metric("Cells with hotspots (0.25°)", sel[["cy", "cx"]].drop_duplicates().shape[0])
c3.metric("Low-reliability periods", f"{int(res.low.sum())} of {len(res)}")
partial = res.index[res.months < k]
if len(partial):
    st.caption("Incomplete periods: " + ", ".join(map(str, partial)))
st.caption("Error bars: typical discrepancy between converted VIIRS and MODIS ≈ 0.94·N^−0.245, validated for N ≥ 7 (Paraguay, 2020–2025). This is not the error against actual fire.")
st.caption("Orange: 2000-11 to 2002-06, Terra only, scaled with a factor that cannot be validated; the true value could be higher. Data from 2026-08 onward are provisional, and November 2026 is incomplete.")
st.caption("Counts are not corrected for clouds or missing data. A cell is included in the area if its center lies inside the rectangle (0.25° grid).")
with st.expander("View aggregated data"):
    out = res.reset_index().astype({"group": str})
    out["source"] = out["source"].map(LABELS)
    out = out.rename(columns={"group": "period", "n": "hotspots", "prov": "provisional",
                              "low": "low_reliability", "err": "error_bar"})
    st.dataframe(out)