
import pandas as pd


file_path = "SPGlobal_MineEconomics_05-Jun-2026.xlsx"


df = pd.read_excel(
    file_path,
    sheet_name="Data",
    engine="openpyxl"
)

cols = [
    "Paid Copper (000 tonnes)",
    "Cumulative paid copper",
    "Total Cash Cost (¢/lb)",
    "Property" 
]

df = df[cols].dropna()

print(df.dtypes)