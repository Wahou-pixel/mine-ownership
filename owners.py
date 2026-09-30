from pathlib import Path
import re
import unicodedata

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from collections import defaultdict
from collections import Counter, defaultdict
pio.renderers.default = "browser"
ROOT = Path(__file__).resolve().parent

OUTPUT_DIR = ROOT / "outputs" / "plots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

metals = ["cobalt", "copper", "lithium", "nickel", "graphite"]
COST_CURVE_FILES = {
    metal: ROOT / "outputs" / f"SPGlobal_CostCurve_{metal}.csv"
    for metal in metals
}
PROPERTY_FILES = {
    metal: ROOT / "outputs" / f"SPGlobal_Property_{metal}.csv"
    for metal in metals
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
from collections import defaultdict
import pandas as pd

def owner_type_shares_by_country(
    cost_curve_file,
    property_file
):

    # --------------------------------------------------
    # Load data
    # --------------------------------------------------

    cost_df = pd.read_csv(cost_curve_file, dtype=str)
    prop_df = pd.read_csv(property_file, dtype=str)

    cost_df.columns = [c.strip() for c in cost_df.columns]
    prop_df.columns = [c.strip() for c in prop_df.columns]

    # --------------------------------------------------
    # Find production column
    # --------------------------------------------------

    prod_col = next(
        (
            col for col in cost_df.columns
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

    if prod_col is None:
        raise ValueError(
            f"Could not find production column in {cost_curve_file}"
        )

    cost_df[prod_col] = pd.to_numeric(
        cost_df[prod_col]
        .astype(str)
        .str.replace(",", "", regex=False),
        errors="coerce"
    )

    # --------------------------------------------------
    # Property -> mine country
    # --------------------------------------------------

    mine_country = {
        normalize_text(row["Property"]): row["Country/Region"]
        for _, row in cost_df.iterrows()
    }

    # --------------------------------------------------
    # Property -> mine production
    # --------------------------------------------------

    mine_production = {
        normalize_text(row["Property"]): row[prod_col]
        for _, row in cost_df.iterrows()
    }

    # --------------------------------------------------
    # Mine statistics by country
    # --------------------------------------------------

    country_stats = (
        cost_df
        .groupby("Country/Region")
        .agg(
            mine_count=("Property", "nunique"),
            cumulative_capacity=(prod_col, "sum")
        )
        .to_dict("index")
    )

    # --------------------------------------------------
    # Weighted ownership by owner type
    # --------------------------------------------------

    country_owner_types = defaultdict(
        lambda: defaultdict(float)
    )

    for _, row in prop_df.iterrows():

        property_name = normalize_text(
            row.get("Property", "")
        )

        country = mine_country.get(property_name)

        if not country:
            continue

        owner_type = str(
            row.get("Company type", "")
        ).strip()

        try:
            equity = float(
                row.get("Equity Ownership (%)", 0)
            )
        except:
            equity = 0.0

        production = mine_production.get(
            property_name,
            0
        )

        if pd.isna(production):
            production = 0

        weighted_capacity = (
            production * equity / 100
        )

        if owner_type:
            country_owner_types[country][owner_type] += (
                weighted_capacity
            )

    # --------------------------------------------------
    # Build output
    # --------------------------------------------------

    results = []

    for country, counts in country_owner_types.items():

        total_weighted_capacity = sum(
            counts.values()
        )

        row = {
            "Country": country,
            "Mine count": country_stats.get(
                country, {}
            ).get(
                "mine_count", 0
            ),
            "Cumulative capacity": country_stats.get(
                country, {}
            ).get(
                "cumulative_capacity", 0
            ),
            "Total weighted ownership": round(
                total_weighted_capacity,
                2
            )
        }

        for owner_type, weighted_capacity in counts.items():

            row[
                f"{owner_type}_weighted_capacity"
            ] = round(
                weighted_capacity,
                2
            )

            row[
                f"{owner_type}_share"
            ] = round(
                100
                * weighted_capacity
                / total_weighted_capacity,
                2
            ) if total_weighted_capacity > 0 else 0

        results.append(row)

    output_df = pd.DataFrame(results)

    output_df = output_df.sort_values(
        "Cumulative capacity",
        ascending=False
    )

    return output_df


# ==================================================
# RUN FOR ALL METALS
# ==================================================

for metal in metals:

    df = owner_type_shares_by_country(
        COST_CURVE_FILES[metal],
        PROPERTY_FILES[metal]
    )

    df["Metal"] = metal

    output_file = (
        OUTPUT_DIR
        / f"{metal}_owner_type_weighted_shares.csv"
    )

    df.to_csv(
        output_file,
        index=False
    )

    print(f"Saved: {output_file}")