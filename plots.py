# The goal is to plot the cost curves with markers to indicate the
# location of the mining project, the risk score associated with the
# location and the country of the "ultimate parent company"

from pathlib import Path
import re
import unicodedata

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from collections import defaultdict

pio.renderers.default = "browser"


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent

OUTPUT_DIR = ROOT / "outputs" / "plots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

metals = ["cobalt", "copper", "lithium", "nickel", "graphite"]

RISK_FILE = ROOT / "outputs" / "SPGlobal_CountryRiskScores.csv"

COST_CURVE_FILES = {
    metal: ROOT / "outputs" / f"SPGlobal_CostCurve_{metal}.csv"
    for metal in metals
}
PROPERTY_FILES = {
    metal: ROOT / "outputs" / f"SPGlobal_Property_{metal}.csv"
    for metal in metals
}
PUBLIC_PROPERTY_FILES = {
    metal: ROOT / "outputs" / f"SPGlobal_PublicProperty_{metal}.csv"
    for metal in metals
}

# ============================================================
# HELPERS
# ============================================================

OECD_COUNTRIES = {
    "Australia",
    "Austria",
    "Belgium",
    "Canada",
    "Chile",
    "Colombia",
    "Costa Rica",
    "Czech Republic",
    "Denmark",
    "Estonia",
    "Finland",
    "France",
    "Germany",
    "Greece",
    "Hungary",
    "Iceland",
    "Ireland",
    "Israel",
    "Italy",
    "Japan",
    "South Korea",
    "Latvia",
    "Lithuania",
    "Luxembourg",
    "Mexico",
    "Netherlands",
    "New Zealand",
    "Norway",
    "Poland",
    "Portugal",
    "Slovak Republic",
    "Slovenia",
    "Spain",
    "Sweden",
    "Switzerland",
    "Türkiye",
    "United Kingdom",
    "USA"
}

def normalize_text(value):
    if pd.isna(value):
        return ""

    text = str(value).strip()

    text = unicodedata.normalize("NFKD", text)

    text = "".join(
        ch for ch in text
        if not unicodedata.combining(ch)
    )

    return re.sub(r"\s+", " ", text).casefold()


def normalize_property_id(value):
    if pd.isna(value):
        return ""

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return ""

    try:
        number = float(text)
        if number.is_integer():
            return str(int(number))
        return str(number)
    except ValueError:
        return text


def extract_risk_score(value):

    if pd.isna(value):
        return None

    match = re.search(
        r"([-+]?\d+(?:\.\d+)?)",
        str(value)
    )

    return float(match.group(1)) if match else None


def load_risk_lookup(path):

    risk_df = pd.read_csv(
        path,
        skiprows=[1],
        dtype=str
    )

    risk_df.columns = [
        col.strip()
        for col in risk_df.columns
    ]

    risk_df["risk_score"] = (
        risk_df["Prior Overall Score"]
        .apply(extract_risk_score)
    )

    lookup = {}

    for _, row in risk_df.iterrows():

        country = normalize_text(
            row["Country/Region"]
        )

        score = row["risk_score"]

        if country and score is not None:
            lookup[country] = float(score)

    return lookup

def build_owner_lookup(path): #lookup["28811"] and lookup["aktogay"] would return [{"owner": "KAZ Minerals Limited","keyinstn": "4199214", "equity_ownership": "100"},{"owner": "Another Shareholder","keyinstn": "9999999","equity_ownership": "12"}]

    prop_df = pd.read_csv(path, dtype=str)
    prop_df.columns = [c.strip() for c in prop_df.columns]

    lookup = {}

    for _, row in prop_df.iterrows():
       
        property_name = normalize_text(
            row.get("Property", "")
        )

        if not property_name:
            continue

        owner_record={
           "owner": row.get("Owner", ""),
           "keyinstn": row.get("KeyInstn", ""),
           "equity_ownership": row.get("Equity Ownership (%)", ""),
           "company_type": row.get("Company type", ""),
           "owner_country": row.get("Owner country", ""),
           "parent_company": row.get("Parent Company Name", ""),
           "parent_country": row.get("Parent Company Country", ""),
           "parent_keyinstn": row.get("Parent company KeyInstn", ""),
           "parent_company_type": row.get("Parent company type", ""),
           "ultimate_parent_company": row.get("Ultimate Parent Company Name", ""),
           "ultimate_parent_country": row.get("Ultimate Parent Company Country", ""),
           "ultimate_parent_keyinstn": row.get("Ultimate Parent company KeyInstn", ""),
           "ultimate_parent_company_type": row.get("Ultimate Parent company type", ""),
           "percent_owned_all_institutions": row.get("Percent Owned All-Insitutions", ""),
           "percent_owned_public_companies": row.get("Percent Owned Public Companies", ""),
           "insiders": row.get("Insiders", ""),
           "strategic_hedge_funds": row.get("Strategic Hedge Funds Managers >=5% stake", ""),
           "strategic_vc_pe": row.get("Strategic VC/PE firms >=5% stake", ""),
           "sovereign_wealth_funds": row.get("Sovereign Wealth Funds >=5% stake", ""),
           "strategic_company_controlled_foundations": row.get("Strategic company controlled foundations", ""),
           "strategic_esop": row.get("Strategic ESOP", ""), 
           "strategic_state_owner":row.get("Strategic State Owner",""),
           "strategic_corportation_private":row.get("Strategic Corporation (Private)",""),
           "strategic_corportation_public":row.get("Strategic Corporation (Public)","")
       }
        for key in [property_name]:
            if key:
                lookup.setdefault(key, []).append(owner_record)

    return lookup


def build_owner_country_lookup(property_file, public_property_file):

    owner_lookup=build_owner_lookup(property_file)

    public_df = pd.read_csv(public_property_file, dtype=str)
    public_df.columns = [c.strip() for c in public_df.columns]
    public_df = public_df.drop_duplicates(
        subset=[
            "Owner_ID",
            "Holder_ID",
            "Holder_Country",
            "Percent_Held_by_Holder"
        ]
    )
    # --------------------------------------------------
    # PUBLIC COMPANIES LOOKUP
    # Owner_ID -> {country: pct}
    # --------------------------------------------------

    public_lookup = {}

    for owner_id, group in public_df.groupby("Owner_ID"):

        country_weights = defaultdict(float)

        for _, row in group.iterrows():

            holder_type=str(row.get("Holder_Type","")).strip()
            if holder_type == "Individuals/Insiders":
                continue
            country = str(
                row.get("Holder_Country", "")
            ).strip()

            try:
                pct = float(
                    row.get("Percent_Held_by_Holder", 0)
                )
            except:
                pct = 0.0

            if country:
                country_weights[country] += pct

        public_lookup[normalize_property_id(owner_id)] = dict(country_weights)

    # --------------------------------------------------
    # PROPERTY LOOKUP
    # Property ID / Property Name -> ownership structure
    # --------------------------------------------------

    country_lookup = {}

    for property_key, owners in owner_lookup.items():

        ownership_by_country= defaultdict(float)
        owner_types=set()
        owner_names = set()
        owner_details = []
        owner_debug = []
        for owner in owners:
            try:
                equity_pct=float(owner.get("equity_ownership", 0) or 0)
            except Exception:
                equity_pct = 0.0
            owner_name = str(
                owner.get("owner", "")
            ).strip()
            if owner_name:
                owner_names.add(owner_name)
            try:
                equity_pct=float(owner.get("equity_ownership", 0) or 0)
            except:
                equity_pct = 0.0
            owner_details.append(
                f"{owner_name} ({equity_pct:.1f}%)"
            )
            company_type=str(owner.get("company_type", "")).strip()
            owner_debug_record = {
                "owner": owner_name,
                "equity_ownership": equity_pct,
                "company_type": company_type
            }
            if company_type:
                owner_types.add(company_type)
            # private company
            if company_type == "Private Company":
                country=""
                if owner.get("ultimate_parent_country"):
                    country= owner["ultimate_parent_country"]
                elif owner.get("parent_country"):
                    country = owner["parent_country"]
                else: 
                    country=owner["owner_country"]
                if country:
                    ownership_by_country[country]+= equity_pct
            # Foundation/ Gov/ Fund
            elif company_type in {"Foundation or Charitable Institution","Government Institution", "Private Fund"}:
                country=owner["owner_country"]
                if country:
                    ownership_by_country[country]+= equity_pct
            # Public company
            elif company_type == "Public Company":
                keyinstn = normalize_property_id(owner.get("keyinstn", ""))
                holder_breakdown= public_lookup.get(keyinstn,{})
                if holder_breakdown:
                    owner_oecd = sum(pct for country, pct in holder_breakdown.items() if country in OECD_COUNTRIES)
                    owner_non_oecd = (sum(holder_breakdown.values())- owner_oecd)
                    owner_debug_record["owner_oecd_ownership"] = round(owner_oecd, 2)
                    owner_debug_record["owner_non_oecd_ownership"] = round(owner_non_oecd, 2)
                    
                    for country, holder_pct in (holder_breakdown.items()):
                        mine_pct = (equity_pct* holder_pct)/100
                        ownership_by_country[country]+= mine_pct
            owner_debug.append(owner_debug_record)
        oecd_ownership=0.0
        for country, pct in ownership_by_country.items():
            if country in OECD_COUNTRIES:
                    oecd_ownership += pct
        non_oecd_ownership = (sum(ownership_by_country.values())-oecd_ownership)
        country_lookup[property_key] = {
            "countries": {
                c: round(v,2)
                for c, v in ownership_by_country.items()
            },
            "oecd_ownership":round(oecd_ownership,2),
            "non_oecd_ownership":round(non_oecd_ownership,2),
            "owner_details": owner_details,
            "owner_types": sorted(owner_types),
            "owner_debug": owner_debug
        }            
    return country_lookup
# ============================================================
# COST CURVE
# ============================================================

def plot_cost_curve(metal, risk_lookup, owner_country_lookup):

    csv_file = COST_CURVE_FILES[metal]

    if not csv_file.exists():
        print(f"Missing file: {csv_file}")
        return

    df = pd.read_csv(csv_file)

    df.columns = [
        col.strip()
        for col in df.columns
    ]

    # --------------------------------------------------------
    # Find production column
    # --------------------------------------------------------

    prod_col = next(
        (
            col for col in df.columns
            if (
                (
                    "paid" in col.lower()
                    or "production" in col.lower()
                )
                and "cumulative" not in col.lower()
            )
        ),
        None
    )

    # --------------------------------------------------------
    # Find cumulative column
    # --------------------------------------------------------

    cum_col = next(
        (
            col for col in df.columns
            if "cumulative" in col.lower()
        ),
        None
    )

    # --------------------------------------------------------
    # Find total cost column
    # --------------------------------------------------------

    total_col = next(
        (
            col for col in df.columns
            if "total cash cost" in col.lower()
        ),
        None
    )

    if not all([prod_col, cum_col, total_col]):
        print(f"Columns not found for {metal}")
        return

    # --------------------------------------------------------
    # Keep useful columns
    # --------------------------------------------------------

    plot_df = df[
        [
            "Property",
            "Property ID",
            "Country/Region",
            prod_col,
            cum_col,
            total_col
        ]
    ].copy()

    # Numeric conversion

    for col in [prod_col, cum_col, total_col]:

        plot_df[col] = pd.to_numeric(
            plot_df[col]
            .astype(str)
            .str.replace(",", ""),
            errors="coerce"
        )

    plot_df = plot_df.dropna(
        subset=[prod_col, cum_col, total_col]
    )

    # --------------------------------------------------------
    # Risk score
    # --------------------------------------------------------

    plot_df["risk_score"] = (
        plot_df["Country/Region"]
        .apply(
            lambda country:
            risk_lookup.get(
                normalize_text(country),
                3.0
            )
        )
    )
    def resolve_owner_meta(row):
        property_name_key = normalize_text(row["Property"])
        if property_name_key and property_name_key in owner_country_lookup:
            return owner_country_lookup[property_name_key]
        return {
            "countries": {}, 
            "oecd_ownership": None,
            "non_oecd_ownership": None
        }

    owner_meta = plot_df.apply(resolve_owner_meta, axis=1)

    plot_df["owner_names"] = owner_meta.apply(
        lambda x: ", ".join(
            x.get("owner_names", [])
        )
    )
    plot_df["owner_details"] = owner_meta.apply(
    lambda x: "<br>".join(
        x.get("owner_details", [])
        )
    )
    plot_df["owner_types"] = owner_meta.apply(
    lambda x: ", ".join(
        x.get("owner_types", [])
        )
    )

    plot_df["oecd_ownership"] = owner_meta.apply(
        lambda x: x.get("oecd_ownership", 0)
    )
    plot_df["non_oecd_ownership"] = owner_meta.apply(
        lambda x: x.get("non_oecd_ownership", 0)
    )
    #plot_df["owner_level"] = owner_meta.apply( lambda item: item.get("level", "unknown") if isinstance(item, dict) else "unknown")
    plot_df["owner_countries"] = owner_meta.apply(
        lambda x: "<br>".join(
            f"{country}: {pct:.2f}%"
            for country, pct in sorted(
                x.get("countries", {}).items(),
                key=lambda item: item[1],
                reverse=True
            )
        )
    )
    plot_df["oecd_owner"] = (
        plot_df["oecd_ownership"]
        > plot_df["non_oecd_ownership"]
    )
    # --------------------------------------------------------
    # Rectangle position
    # --------------------------------------------------------

    plot_df["x_start"] = (
        plot_df[cum_col]
        - plot_df[prod_col]
    )

    plot_df["x_center"] = (
        plot_df["x_start"]
        + plot_df[prod_col] / 2
    )
    non_oecd = plot_df[
        ~plot_df["oecd_owner"]
    ]
    oecd = plot_df[
        plot_df["oecd_owner"]
    ]
    # --------------------------------------------------------
    # Plot
    # --------------------------------------------------------

    fig = go.Figure()

    if not non_oecd.empty:
        fig.add_trace(
            go.Bar(
                x=non_oecd["x_center"],
                y=non_oecd[total_col],
                width=non_oecd[prod_col],
                marker=dict(
                    color=non_oecd["risk_score"],
                    colorscale="RdYlGn_r",
                    cmin=1,
                    cmax=5,
                    colorbar=dict(title="Risk Score")
                ),
                customdata=non_oecd[
                    [
                        "Property",
                        "Country/Region",
                        "risk_score",
                        "owner_details",
                        "owner_types",
                        "oecd_ownership",
                        "non_oecd_ownership",
                        "owner_countries"
                    ]
                ].values,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Country: %{customdata[1]}<br>"
                    "Risk score: %{customdata[2]}<br>"
                    "Owners: %{customdata[3]}<br>"
                    "Owner type(s): %{customdata[4]}<br>"
                    "OECD ownership: %{customdata[5]}%<br>"
                    "Non-OECD ownership: %{customdata[6]}%<br>"
                    #"Ownership by country: <br>%{customdata[5]}<br>"
                    "<extra></extra>"
                ),
                showlegend=False,
            )
        )

    if not oecd.empty:
        fig.add_trace(
            go.Bar(
                x=oecd["x_center"],
                y=oecd[total_col],
                width=oecd[prod_col],
                marker=dict(
                    color=oecd["risk_score"],
                    colorscale="RdYlGn_r",
                    cmin=1,
                    cmax=5,
                    colorbar=dict(title="Risk Score"),
                    line=dict(color="rgba(0, 82, 204, 0.95)", width=2.5)
                ),
                customdata=oecd[
                    [
                        "Property",
                        "Country/Region",
                        "risk_score",
                        "owner_details",
                        "owner_types",
                        "oecd_ownership",
                        "non_oecd_ownership",
                        "owner_countries"
                    ]
                ].values,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Country: %{customdata[1]}<br>"
                    "Risk score: %{customdata[2]}<br>"
                    "Owners: %{customdata[3]}<br>"
                    "Owner type(s): %{customdata[4]}<br>"
                    "OECD ownership: %{customdata[5]}%<br>"
                    "Non-OECD ownership: %{customdata[6]}%<br>"
                    #"Ownership by country: <br>%{customdata[5]}<br>"
                    "<extra></extra>"
                ),
                showlegend=False,
            )
        )

    high_risk = plot_df[plot_df["risk_score"] > 3.5]
    if not high_risk.empty:
        oecd_share = (
            high_risk["oecd_ownership"].sum()
        / (high_risk["oecd_ownership"].sum() + high_risk["non_oecd_ownership"].sum())*100
        )
        annotation_text = f"OECD-owner share among projects with risk score > 3.5: {oecd_share:.1f}%"
    else:
        annotation_text = "OECD-owner share among projects with risk score > 3.5: n/a"

    fig.update_layout(
        title=f"{metal.title()} Cost Curve",
        xaxis_title="Cumulative Production (000 tonnes)",
        yaxis_title="Total Cash Cost (¢/lb)",
        template="plotly_white",
        bargap=0,
        margin=dict(t=80, r=20, b=40, l=40),
        annotations=[
            dict(
                x=0.99,
                y=0.98,
                xref="paper",
                yref="paper",
                text=annotation_text,
                showarrow=False,
                align="right",
                xanchor="right",
                yanchor="top",
                font=dict(size=11, color="#2c3e50"),
                bgcolor="rgba(255,255,255,0.9)",
                borderpad=4
            )
        ]
    )

    output_file = (
        OUTPUT_DIR /
        f"{metal}_cost_curve.html"
    )

    fig.write_html(
        output_file,
        include_plotlyjs="cdn"
    )

    print(f"Saved: {output_file}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    risk_lookup = load_risk_lookup(RISK_FILE)
    owner_lookup=build_owner_lookup(PROPERTY_FILES["copper"])
    owner_country_lookup = build_owner_country_lookup(PROPERTY_FILES["copper"],PUBLIC_PROPERTY_FILES["copper"])
    #print(owner_country_lookup["aitik"])
    #print(owner_country_lookup["aitik"]["owner_debug"])
    #print(owner_country_lookup["antamina"])
    print(owner_country_lookup["antamina"]["owner_debug"])
    
    #for metal in metals:
        #owner_country_lookup = build_owner_country_lookup(PROPERTY_FILES[metal],PUBLIC_PROPERTY_FILES[metal])
        #plot_cost_curve(metal, risk_lookup, owner_country_lookup)