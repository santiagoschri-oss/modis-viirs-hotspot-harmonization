"""Interactive globe for the Streamlit app (Plotly orthographic projection).

Paraguay shows the harmonized hotspot cells; every other country says "Coming soon".
Drag to rotate, scroll to zoom. Needs `plotly` in requirements.txt.
"""
import numpy as np
import plotly.graph_objects as go

# ISO 3166-1 alpha-3 code and English name.
_COUNTRIES = """
AFG Afghanistan
ALA Aland Islands
ALB Albania
DZA Algeria
ASM American Samoa
AND Andorra
AGO Angola
AIA Anguilla
ATA Antarctica
ATG Antigua and Barbuda
ARG Argentina
ARM Armenia
ABW Aruba
AUS Australia
AUT Austria
AZE Azerbaijan
BHS Bahamas
BHR Bahrain
BGD Bangladesh
BRB Barbados
BLR Belarus
BEL Belgium
BLZ Belize
BEN Benin
BMU Bermuda
BTN Bhutan
BOL Bolivia
BES Bonaire, Sint Eustatius and Saba
BIH Bosnia and Herzegovina
BWA Botswana
BVT Bouvet Island
BRA Brazil
IOT British Indian Ocean Territory
BRN Brunei
BGR Bulgaria
BFA Burkina Faso
BDI Burundi
CPV Cabo Verde
KHM Cambodia
CMR Cameroon
CAN Canada
CYM Cayman Islands
CAF Central African Republic
TCD Chad
CHL Chile
CHN China
CXR Christmas Island
CCK Cocos Islands
COL Colombia
COM Comoros
COG Republic of the Congo
COD DR Congo
COK Cook Islands
CRI Costa Rica
CIV Cote d'Ivoire
HRV Croatia
CUB Cuba
CUW Curacao
CYP Cyprus
CZE Czechia
DNK Denmark
DJI Djibouti
DMA Dominica
DOM Dominican Republic
ECU Ecuador
EGY Egypt
SLV El Salvador
GNQ Equatorial Guinea
ERI Eritrea
EST Estonia
SWZ Eswatini
ETH Ethiopia
FLK Falkland Islands
FRO Faroe Islands
FJI Fiji
FIN Finland
FRA France
GUF French Guiana
PYF French Polynesia
ATF French Southern Territories
GAB Gabon
GMB Gambia
GEO Georgia
DEU Germany
GHA Ghana
GIB Gibraltar
GRC Greece
GRL Greenland
GRD Grenada
GLP Guadeloupe
GUM Guam
GTM Guatemala
GGY Guernsey
GIN Guinea
GNB Guinea-Bissau
GUY Guyana
HTI Haiti
HMD Heard Island and McDonald Islands
VAT Vatican City
HND Honduras
HKG Hong Kong
HUN Hungary
ISL Iceland
IND India
IDN Indonesia
IRN Iran
IRQ Iraq
IRL Ireland
IMN Isle of Man
ISR Israel
ITA Italy
JAM Jamaica
JPN Japan
JEY Jersey
JOR Jordan
KAZ Kazakhstan
KEN Kenya
KIR Kiribati
PRK North Korea
KOR South Korea
XKX Kosovo
KWT Kuwait
KGZ Kyrgyzstan
LAO Laos
LVA Latvia
LBN Lebanon
LSO Lesotho
LBR Liberia
LBY Libya
LIE Liechtenstein
LTU Lithuania
LUX Luxembourg
MAC Macao
MDG Madagascar
MWI Malawi
MYS Malaysia
MDV Maldives
MLI Mali
MLT Malta
MHL Marshall Islands
MTQ Martinique
MRT Mauritania
MUS Mauritius
MYT Mayotte
MEX Mexico
FSM Micronesia
MDA Moldova
MCO Monaco
MNG Mongolia
MNE Montenegro
MSR Montserrat
MAR Morocco
MOZ Mozambique
MMR Myanmar
NAM Namibia
NRU Nauru
NPL Nepal
NLD Netherlands
NCL New Caledonia
NZL New Zealand
NIC Nicaragua
NER Niger
NGA Nigeria
NIU Niue
NFK Norfolk Island
MKD North Macedonia
MNP Northern Mariana Islands
NOR Norway
OMN Oman
PAK Pakistan
PLW Palau
PSE Palestine
PAN Panama
PNG Papua New Guinea
PRY Paraguay
PER Peru
PHL Philippines
PCN Pitcairn Islands
POL Poland
PRT Portugal
PRI Puerto Rico
QAT Qatar
REU Reunion
ROU Romania
RUS Russia
RWA Rwanda
BLM Saint Barthelemy
SHN Saint Helena
KNA Saint Kitts and Nevis
LCA Saint Lucia
MAF Saint Martin
SPM Saint Pierre and Miquelon
VCT Saint Vincent and the Grenadines
WSM Samoa
SMR San Marino
STP Sao Tome and Principe
SAU Saudi Arabia
SEN Senegal
SRB Serbia
SYC Seychelles
SLE Sierra Leone
SGP Singapore
SXM Sint Maarten
SVK Slovakia
SVN Slovenia
SLB Solomon Islands
SOM Somalia
ZAF South Africa
SGS South Georgia and the South Sandwich Islands
SSD South Sudan
ESP Spain
LKA Sri Lanka
SDN Sudan
SUR Suriname
SJM Svalbard and Jan Mayen
SWE Sweden
CHE Switzerland
SYR Syria
TWN Taiwan
TJK Tajikistan
TZA Tanzania
THA Thailand
TLS Timor-Leste
TGO Togo
TKL Tokelau
TON Tonga
TTO Trinidad and Tobago
TUN Tunisia
TUR Turkey
TKM Turkmenistan
TCA Turks and Caicos Islands
TUV Tuvalu
UGA Uganda
UKR Ukraine
ARE United Arab Emirates
GBR United Kingdom
USA United States
UMI United States Minor Outlying Islands
URY Uruguay
UZB Uzbekistan
VUT Vanuatu
VEN Venezuela
VNM Vietnam
VGB British Virgin Islands
VIR US Virgin Islands
WLF Wallis and Futuna
ESH Western Sahara
YEM Yemen
ZMB Zambia
ZWE Zimbabwe
"""
COUNTRY_NAMES = dict(line.split(" ", 1) for line in _COUNTRIES.strip().splitlines())

PARAGUAY_VIEW = {"geo.projection.rotation.lon": -58.4, "geo.projection.rotation.lat": -23.2, "geo.projection.scale": 4}
WORLD_VIEW = {"geo.projection.rotation.lon": -58.4, "geo.projection.rotation.lat": -10, "geo.projection.scale": 1}


def build_globe(cells, total, peak_month, start, end):
    """cells: DataFrame with columns lat, lon, conteo_eq (hotspots of each 0.25-degree cell in the selected range)."""
    others = [c for c in COUNTRY_NAMES if c != "PRY"]
    fig = go.Figure()

    # Every other country: neutral color and a "Coming soon" hover.
    fig.add_trace(go.Choropleth(
        locations=others, locationmode="ISO-3", z=[0] * len(others),
        colorscale=[[0, "#e3e8ec"], [1, "#e3e8ec"]], showscale=False,
        marker_line_color="#aab4bd", marker_line_width=0.5,
        customdata=[COUNTRY_NAMES[c] for c in others],
        hovertemplate="<b>%{customdata}</b><br>Coming soon<extra></extra>",
    ))

    # Paraguay: highlighted, with the totals of the current selection.
    peak = peak_month if total > 0 else "n/a"
    fig.add_trace(go.Choropleth(
        locations=["PRY"], locationmode="ISO-3", z=[1],
        colorscale=[[0, "#f6e7c1"], [1, "#f6e7c1"]], showscale=False,
        marker_line_color="#555555", marker_line_width=1.2,
        hovertemplate=(f"<b>Paraguay</b><br>{total:,.0f} hotspots in the selected area"
                       f"<br>{start} to {end}<br>Peak month: {peak}<extra></extra>"),
    ))

    # Harmonized hotspot cells, colored on a log scale (a few cells have most of the fire).
    if len(cells):
        tot = cells["conteo_eq"].to_numpy(dtype=float)
        color = np.log10(1 + tot)
        ticks = [v for v in (1, 10, 100, 1000, 10000, 100000) if v <= tot.max()] or [1]
        fig.add_trace(go.Scattergeo(
            lon=cells["lon"], lat=cells["lat"], mode="markers",
            marker=dict(size=6, symbol="square", color=color, colorscale="Viridis",
                        cmin=0, cmax=max(float(color.max()), 1e-6), opacity=0.92, line=dict(width=0),
                        colorbar=dict(title=dict(text="Hotspots in range<br>(MODIS scale)", side="right"),
                                      tickvals=[np.log10(1 + v) for v in ticks],
                                      ticktext=[f"{v:,}" for v in ticks], len=0.6, thickness=14)),
            customdata=tot,
            hovertemplate="Cell center %{lat:.3f}, %{lon:.3f}<br>%{customdata:,.0f} hotspots<extra></extra>",
        ))

    fig.update_geos(
        projection_type="orthographic",
        projection_rotation=dict(lon=WORLD_VIEW["geo.projection.rotation.lon"], lat=WORLD_VIEW["geo.projection.rotation.lat"]),
        projection_scale=1,
        showland=True, landcolor="#eceff1", showocean=True, oceancolor="#cde4f5",
        showcountries=True, countrycolor="#b0bec5", showcoastlines=True, coastlinecolor="#90a4ae",
        showlakes=False, showframe=False, bgcolor="rgba(0,0,0,0)",
        lonaxis=dict(showgrid=True, gridcolor="rgba(120,144,156,0.25)", dtick=30),
        lataxis=dict(showgrid=True, gridcolor="rgba(120,144,156,0.25)", dtick=30),
    )
    fig.update_layout(
        height=620, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
        updatemenus=[dict(
            type="buttons", direction="right", x=0.01, y=0.99, xanchor="left", yanchor="top",
            buttons=[dict(label="Zoom to Paraguay", method="relayout", args=[PARAGUAY_VIEW]),
                     dict(label="Whole globe", method="relayout", args=[WORLD_VIEW])],
        )],
    )
    return fig
