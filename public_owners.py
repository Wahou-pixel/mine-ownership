from pathlib import Path
from collections import defaultdict
import pandas as pd
import re
import unicodedata

# ==================================================
# PATHS
# ==================================================

ROOT = Path(__file__).resolve().parent

metals = [
    "cobalt",
    "copper",
    "lithium",
    "nickel",
    "graphite"
]

OUTPUT_DIR = ROOT / "outputs" / "plots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COST_CURVE_FILES = {
    metal: ROOT / "outputs" / f"SPGlobal_CostCurve_{metal}.csv"
    for metal in metals
}

PROPERTY_FILES = {
    metal: ROOT / "outputs" / f"SPGlobal_Property_{metal}.csv"
    for metal in metals
}

# ==================================================
# INVESTOR CATEGORIES
# ==================================================

CATEGORY_MAPPING = {

    "Insitutions- Banks/ Investment banks":
        "Institutional Investor",

    "Corporate Pensions sponsors":
        "Institutional Investor",

    "Educational/cultural endowments":
        "Institutional Investor",

    "Insurance companies":
        "Institutional Investor",

    "Investment manager":
        "Institutional Investor",

    "Union Pensions sponsors":
        "Institutional Investor",

    "Hedge Fund Managers <5% stake":
        "Institutional Investor",

    "VC/PE firms <5% stake":
        "Institutional Investor",

    "Strategic Hedge Funds Managers >=5% stake":
        "Institutional Investor",

    "Strategic VC/PE firms >=5% stake":
        "Institutional Investor",

    "Gov pensions sponsors":
        "Public Sector",

    "Soverign Welth Funds <5% stake":
        "Public Sector",

    "Sovereign Wealth Funds >=5% stake":
        "Public Sector",

    "Strategic State Owner":
        "Public Sector",

    "Family Offices/Trusts":
        "Strategic Individual",

    "Insiders":
        "Strategic Individual",

    "Charitable Foundations":
        "Private Corporation",

    "REIT":
        "Private Corporation",

    "Strategic company controlled foundations":
        "Private Corporation",

    "Strategic ESOP":
        "Private Corporation",

    "Strategic Corporation (Private)":
        "Private Corporation",

    "Strategic Corporation (Public)":
        "Private Corporation",

    "Unclassified":
        "Unclassified"
}


# ==================================================
# HELPERS
# ==================================================

def normalize_text(value):

    if pd.isna(value):
        return ""

    text = str(value).strip()

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = "".join(
        ch for ch in text
        if not unicodedata.combining(ch)
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).casefold()


def normalize_column_name(value):
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text


# ==================================================
# MAIN
# ==================================================

def investor_breakdown_by_country(
    cost_curve_file,
    property_file
):

    cost_df = pd.read_csv(
        cost_curve_file,
        dtype=str
    )

    prop_df = pd.read_csv(
        property_file,
        dtype=str
    )

    cost_df.columns = [
        c.strip()
        for c in cost_df.columns
    ]

    prop_df.columns = [
        c.strip()
        for c in prop_df.columns
    ]

    normalized_prop_columns = {
        normalize_column_name(col): col
        for col in prop_df.columns
    }

    # -------------------------
    # Mine -> Country
    # -------------------------

    mine_country = {
        normalize_text(
            row["Property"]
        ): row["Country/Region"]
        for _, row in cost_df.iterrows()
    }

    # -------------------------
    # Country exposures
    # -------------------------

    country_category = defaultdict(
        lambda: defaultdict(float)
    )

    for _, row in prop_df.iterrows():

        if str(
            row.get(
                "Company type",
                ""
            )
        ).strip() != "Public Company":
            continue

        property_name = normalize_text(
            row.get(
                "Property",
                ""
            )
        )

        country = mine_country.get(
            property_name
        )

        if not country:
            continue

        try:
            equity = float(
                row.get(
                    "Equity Ownership (%)",
                    0
                )
            )
        except Exception:
            equity = 0

        for column, category in CATEGORY_MAPPING.items():
            real_col = normalized_prop_columns.get(
                normalize_column_name(column)
            )
            if real_col is None:
                continue

            try:
                pct = float(
                    row.get(
                        real_col,
                        0
                    )
                )
            except Exception:
                pct = 0

            contribution = (
                equity
                * pct
                / 100
            )

            country_category[country][category] += (
                contribution
            )

    # -------------------------
    # Output table
    # -------------------------

    rows = []

    for country, categories in country_category.items():

        total = sum(
            categories.values()
        )

        row = {
            "Country": country,
            "Total Exposure": round(
                total,
                2
            )
        }

        for category in sorted(
            set(
                CATEGORY_MAPPING.values()
            )
        ):

            value = categories.get(
                category,
                0
            )
            row[f"{category} Ownership"] = round(value, 2)
            row[f"{category} (%)"] = round(100 * value / total, 2) if total > 0 else 0

        rows.append(row)

    return pd.DataFrame(rows)


for metal in metals:

    df = investor_breakdown_by_country(
        COST_CURVE_FILES[metal],
        PROPERTY_FILES[metal]
    )

    output_file = (
        OUTPUT_DIR
        / f"{metal}_investor_breakdown_by_country.csv"
    )

    df.to_csv(
        output_file,
        index=False
    )

    print(f"Saved: {output_file}")