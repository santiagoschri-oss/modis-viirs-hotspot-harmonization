from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba, Normalize, PowerNorm
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
import streamlit as st

A, B, N_MIN = 0.94, -0.245, 7      # relative error ≈ A·N^B, validated for N ≥ 7
COLORS = {"Terra_estimado": "#E69F00", "MODIS": "#0072B2", "VIIRS_eq": "#009E73", "mixto": "#7F7F7F"}
LABELS = {"Terra_estimado": "Terra only (estimated)", "MODIS": "MODIS (Terra + Aqua)",
          "VIIRS_eq": "VIIRS (converted to MODIS scale)", "mixto": "mixed sources"}


# Baseline for the historical median: observed MODIS + converted VIIRS only
# (the 20 Terra-only months and the provisional NRT months are excluded).
BASE_START, BASE_END = pd.Period("2002-07", "M"), pd.Period("2026-07", "M")
EST_END, PROV_START = pd.Period("2002-06", "M"), pd.Period("2026-08", "M")
PARTIAL = pd.Period("2026-11", "M")   # latest month: MODIS ends on the 13th, VIIRS on the 1st
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def fmt_count(v):
    if v >= 10000: return f"{v/1000:.0f}k"
    if v >= 1000: return f"{v/1000:.1f}k"
    return f"{v:.0f}"

def calendar_fig(full, first, last, mode):
    """Year x month calendar. mode: 'counts' or 'anomaly' (ratio to the historical median of that calendar month)."""
    y0, n_years = first.year, last.year - first.year + 1
    vals = np.full((n_years, 12), np.nan)
    for p, v in full.items():
        if first <= p <= last:
            vals[p.year - y0, p.month - 1] = v
    base = full[(full.index >= BASE_START) & (full.index <= BASE_END)]
    med = base.groupby(base.index.month).median().reindex(range(1, 13)).to_numpy()

    if mode == "counts":
        vmax = np.nanmax(vals) if np.isfinite(vals).any() else 1.0
        data, low = vals, vals < N_MIN
        cmap, norm = plt.get_cmap("viridis").copy(), PowerNorm(gamma=0.5, vmin=0, vmax=max(vmax, 1.0))
        cbar_label = "Hotspots per month (MODIS scale, square-root color scale)"
    else:
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = vals / med[None, :]
        ratio[:, ~(med > 0)] = np.nan            # undefined when the median is 0
        data = np.log2(np.clip(ratio, 0.25, 4.0))
        low = (vals < N_MIN) | (med[None, :] < N_MIN)
        cmap, norm = plt.get_cmap("RdBu_r").copy(), Normalize(-2, 2)
        cbar_label = "Ratio to the median of the same calendar month"
    cmap.set_bad("#e6e6e6")
    pr, pc = PARTIAL.year - y0, PARTIAL.month - 1
    if mode == "anomaly" and 0 <= pr < n_years and np.isfinite(vals[pr, pc]):
        data[pr, pc] = np.nan                  # an incomplete month has no meaningful ratio

    fig, ax = plt.subplots(figsize=(11, max(3.2, 0.28 * n_years + 1.6)))
    im = ax.imshow(np.ma.masked_invalid(data), cmap=cmap, norm=norm, aspect="auto")
    for r in range(n_years):
        for c in range(12):
            if not np.isfinite(vals[r, c]):
                continue
            p = pd.Period(year=y0 + r, month=c + 1, freq="M")
            hatch = ".." if p <= EST_END else ("\\\\" if p >= PROV_START else None)
            if hatch:
                ax.add_patch(Rectangle((c - 0.5, r - 0.5), 1, 1, fill=False, hatch=hatch,
                                       edgecolor=(0, 0, 0, 0.4), linewidth=0))
            if mode == "anomaly" and p == PARTIAL:
                ax.text(c, r, "partial", ha="center", va="center", fontsize=6.5, color="black")
            elif np.isfinite(data[r, c]):
                rgba = cmap(norm(data[r, c]))
                txt_col = "black" if (0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]) > 0.5 else "white"
                if mode == "counts":
                    label = fmt_count(vals[r, c])
                else:
                    rv = vals[r, c] / med[c]
                    label = "<0.1x" if rv < 0.1 else (f"{rv:.0f}x" if rv >= 10 else f"{rv:.1f}x")
                ax.text(c, r, label + ("*" if low[r, c] else ""), ha="center", va="center",
                        fontsize=6.5, color=txt_col)
    ax.set_xticks(range(12)); ax.set_xticklabels(MONTH_NAMES)
    ax.set_yticks(range(n_years)); ax.set_yticklabels(range(y0, y0 + n_years), fontsize=8)
    ax.xaxis.tick_top(); ax.tick_params(length=0)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label(cbar_label, fontsize=8)
    if mode == "anomaly":
        cbar.set_ticks([-2, -1, 0, 1, 2]); cbar.set_ticklabels(["<=0.25x", "0.5x", "median", "2x", ">=4x"])
    handles = [Patch(facecolor="white", edgecolor="black", hatch="..", label="estimated (Terra only)"),
               Patch(facecolor="white", edgecolor="black", hatch="\\\\", label="provisional (NRT)"),
               Patch(facecolor="#e6e6e6", edgecolor="grey", label="no data / undefined"),
               Line2D([], [], linestyle="none", label=f"* low reliability (N < {N_MIN})")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=4, fontsize=7, frameon=False)
    return fig

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
full_series = sel.groupby("mes").conteo_eq.sum().reindex(all_months, fill_value=0.0)
series = full_series.loc[pd.Period(start, "M"):pd.Period(end, "M")]

g = pd.DataFrame({"n": series.values, "group": series.index.asfreq(freq),
                  "source": [source(m) for m in series.index],
                  "prov": series.index >= pd.Period("2026-08", "M")})
res = g.groupby("group").agg(n=("n", "sum"), months=("n", "size"), prov=("prov", "any"),
                             source=("source", lambda s: s.iat[0] if s.nunique() == 1 else "mixto"))
res["low"] = res.n < N_MIN
res["err"] = np.where(res.low, np.nan, res.n * A * np.maximum(res.n, 1e-9) ** B)

# ---- Chart ----
st.subheader("Hotspot time series")
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
ax.legend(handles=legend, loc="upper right", fontsize=8)
fig.tight_layout()
st.pyplot(fig)
plt.close(fig)

# ---- Interactive globe ----
st.subheader("Interactive globe")
try:
    from globe import build_globe
    in_rng = (sel.mes >= pd.Period(start, "M")) & (sel.mes <= pd.Period(end, "M"))
    cell_tot = sel[in_rng].groupby(["lat", "lon"], as_index=False).conteo_eq.sum()
    st.plotly_chart(build_globe(cell_tot, float(res.n.sum()), str(series.idxmax()), start, end),
                    theme=None, width="stretch")
    st.caption("Drag to rotate and scroll to zoom. Each square is a 0.25-degree cell with harmonized hotspots "
               "for the area and month range selected in the sidebar. Only Paraguay has harmonized data so far; "
               "the other countries are coming soon. The globe needs an internet connection to load the country shapes.")
except Exception as e:
    st.info(f"The interactive globe is not available: {e}")

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

# ---- CSV downloads ----
st.subheader("Download data")

# 1. Datos por celda y mes
cell_export = sel[
    sel["mes"].between(pd.Period(start, "M"), pd.Period(end, "M"))
].copy()

cell_export["mes"] = cell_export["mes"].astype(str)
cell_export["origen"] = cell_export["mes"].map(
    lambda m: LABELS[source(pd.Period(m, "M"))]
)
cell_export["provisorio"] = cell_export["mes"].map(
    lambda m: pd.Period(m, "M") >= PROV_START
)

cell_export = cell_export[
    ["cy", "cx", "lat", "lon", "mes", "conteo_eq", "origen", "provisorio"]
].sort_values(["mes", "cy", "cx"])

st.download_button(
    label="Download cell-by-month data (CSV)",
    data=cell_export.to_csv(index=False).encode("utf-8-sig"),
    file_name="hotspots_cell_month.csv",
    mime="text/csv"
)

# ---- Burning activity calendar ----
st.subheader("Burning activity calendar")
view = st.radio("Calendar shows", ["Hotspot counts", "Anomaly vs. historical median"], horizontal=True)
fig_cal = calendar_fig(full_series, pd.Period(start, "M"), pd.Period(end, "M"),
                       "counts" if view == "Hotspot counts" else "anomaly")
st.pyplot(fig_cal)
plt.close(fig_cal)
st.caption("Each cell is one month of the selected area. Values are printed in every cell, so the color is never the only cue. "
           "The color scales are perceptually uniform (viridis) and blue-red diverging, which stay distinguishable with common forms of color blindness.")
st.caption("Anomaly = count divided by the median of the same calendar month over 2002-07 to 2026-07 (observed MODIS and converted VIIRS; "
           "the Terra-only and provisional months are not part of the baseline). 2x means twice the usual activity for that month. "
           "Gray cells have no data or an undefined ratio (median = 0). Estimated and provisional months are hatched. "
           "The latest month is incomplete and is left out of the anomaly view.")
with st.expander("View aggregated data"):
    out = res.reset_index().astype({"group": str})
    out["source"] = out["source"].map(LABELS)
    out = out.rename(columns={"group": "period", "n": "hotspots", "prov": "provisional",
                              "low": "low_reliability", "err": "error_bar"})
    st.dataframe(out)
    st.download_button(
        label="Download aggregated time series (CSV)",
        data=out.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"hotspots_aggregated_{agg.lower()}.csv",
        mime="text/csv"
    )

# ============================================================
# NATIONAL HOTSPOT FORECAST - PARAGUAY
# N-HiTS-inspired model implemented in Keras
# (last on purpose: if it fails, nothing above is affected)
# ============================================================

st.divider()
st.header("National Fire Activity Forecast")
st.caption(
    "Monthly national estimates for Paraguay using a deep learning "
    "model trained on the harmonized historical time series."
)

MODEL_DIR = Path(__file__).parent / "models" / "nhits"
MODEL_PATH = MODEL_DIR / "nbeats_final.keras"
METADATA_PATH = MODEL_DIR / "metadata.json"


@st.cache_resource
def load_forecast_model():
    from tensorflow import keras      # imported here so TensorFlow only loads for the forecast

    model = keras.models.load_model(
        MODEL_PATH,
        compile=False
    )

    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return model, metadata


@st.cache_data
def prepare_national_series():
    # Load the complete original dataset, without applying the user's AOI.
    data = load().copy()

    # Exclude the current incomplete month.
    current_month = pd.Period(pd.Timestamp.today(), freq="M")
    data = data[data["mes"] < current_month].copy()

    # Exclude provisional records, following the same procedure used during training.
    if "provisorio" in data.columns:
        provisional = (
            data["provisorio"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(["true", "1", "si", "sí"])
        )
        data = data[~provisional].copy()

    # National aggregation: all grid cells across Paraguay.
    national = (
        data.groupby("mes")["conteo_eq"]
        .sum()
        .sort_index()
    )

    if national.empty:
        raise ValueError("No historical data is available.")

    # Fill missing months with zero.
    full_index = pd.period_range(
        start=national.index.min(),
        end=national.index.max(),
        freq="M"
    )

    national = national.reindex(full_index, fill_value=0)
    national.index.name = "mes"

    return national.astype(float)


try:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model file not found: {MODEL_PATH}"
        )

    if not METADATA_PATH.exists():
        raise FileNotFoundError(
            f"Metadata file not found: {METADATA_PATH}"
        )

    model, metadata = load_forecast_model()
    national_series = prepare_national_series()

    input_size = int(metadata["input_size"])
    horizon = int(metadata["horizon"])

    if len(national_series) < input_size:
        raise ValueError(
            f"At least {input_size} months of historical data are required."
        )

    # Load the scaler parameters saved during model training.
    mu = float(metadata["scaler"]["mu"])
    sd = float(metadata["scaler"]["sd"])

    if sd == 0:
        raise ValueError("The scaler standard deviation is zero.")

    # Select the last 36 complete months.
    historical_values = national_series.iloc[-input_size:].values

    # Apply the same transformation used during training.
    x_scaled = (
        (np.log1p(historical_values) - mu) / sd
    ).astype("float32")

    x_input = x_scaled.reshape(1, input_size)

    # Direct prediction for the next 12 months.
    prediction_scaled = model.predict(
        x_input,
        verbose=0
    ).reshape(-1)

    if len(prediction_scaled) != horizon:
        raise ValueError(
            f"The model returned {len(prediction_scaled)} values; "
            f"{horizon} were expected."
        )

    # Invert the logarithmic transformation.
    prediction = np.maximum(
        np.expm1(prediction_scaled * sd + mu),
        0
    )

    # Generate future months starting after the last complete historical month.
    last_month = national_series.index[-1]

    future_months = pd.period_range(
        start=last_month + 1,
        periods=horizon,
        freq="M"
    )

    forecast_df = pd.DataFrame({
        "Month": future_months.astype(str),
        "Estimated_Equivalent_Hotspots": np.round(prediction).astype(int)
    })

    # Display forecast results.
    st.subheader("Forecast for the Next 12 Months")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Last Observed Month",
        str(last_month)
    )

    col2.metric(
        "Forecast Horizon",
        f"{horizon} months"
    )

    col3.metric(
        "Estimated Monthly Average",
        f"{np.mean(prediction):,.0f}"
    )

    # Plot recent historical data alongside the forecast.
    historical_plot = national_series.iloc[-36:]

    fig_forecast, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        [str(x) for x in historical_plot.index],
        historical_plot.values,
        label="Observed Historical Data",
        linewidth=2
    )

    ax.plot(
        forecast_df["Month"],
        prediction,
        label="N-HiTS Forecast",
        linewidth=2,
        linestyle="--",
        marker="o"
    )

    ax.axvline(
        x=35.5,
        linestyle=":",
        alpha=0.7,
        label="Forecast Start"
    )

    ax.set_title("National Hotspot Activity: Historical Data and Forecast")
    ax.set_xlabel("Month")
    ax.set_ylabel("Equivalent Hotspots")
    ax.tick_params(axis="x", rotation=75)
    ax.grid(alpha=0.25)
    ax.legend()
    fig_forecast.tight_layout()

    st.pyplot(fig_forecast)
    plt.close(fig_forecast)

    # Display forecast values in a table.
    st.subheader("Estimated Monthly Values")
    st.dataframe(
        forecast_df,
        use_container_width=True,
        hide_index=True
    )

    # Download forecast as a CSV file.
    csv_forecast = forecast_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="Download Forecast as CSV",
        data=csv_forecast,
        file_name="paraguay_national_hotspot_forecast.csv",
        mime="text/csv"
    )

    st.caption(
        "Note: These values represent estimated monthly equivalent hotspots, "
        "not fire probabilities or fire risk indices. "
        "The forecast covers all of Paraguay and is independent of the AOI "
        "selected in the application."
    )

except Exception as e:
    st.error(f"Unable to generate the forecast: {e}")
