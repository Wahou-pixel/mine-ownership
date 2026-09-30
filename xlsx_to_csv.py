import pandas as pd
import os

folder_csv = "outputs"
os.makedirs(folder_csv, exist_ok=True)

# List of metals
metals = ["cobalt", "copper", "lithium", "nickel", "graphite"]

for metal in metals:
    file_xlsx = f"inputs/SPGlobal_Ore_24-Jul-2026-{metal}.xlsx"
    
    try:
        df = pd.read_excel(file_xlsx, sheet_name='Ownership_txt', dtype=str)
        df.columns = (
            df.columns.astype(str)
            .str.replace("\n", " ", regex=False)
            .str.strip()
        )
        
        idx_property = df.columns.get_loc("Property")
        df_extrait = df.iloc[:, idx_property:]
        # Remove rows with all NaN values
        df_extrait = df_extrait.dropna(how='all')
        
        # Save to CSV
        output_file = os.path.join(folder_csv, f"SPGlobal_Property_{metal}.csv")
        df_extrait.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Saved: {output_file} ({len(df_extrait)} rows)")
        
    except FileNotFoundError:
        print(f"File not found: {file_xlsx}")
    except Exception as e:
        print(f"Error processing {file_xlsx}: {e}")

# Produce public companies ownership for each metal
for metal in metals:
    file_xlsx = f"inputs/SPGlobal_Ore_24-Jul-2026-{metal}.xlsx"
    
    try:
        df = pd.read_excel(
            file_xlsx,
            sheet_name="Public Companies Owners", skiprows=1, header=None, dtype=str
        )
        owner_row = 0      # lines of Owner IDs
        header_row = 1     # lines Holder Name / Holder ID ...
        results = []

        col = 0

        results = []

        for col in range(0, df.shape[1], 5):

            owner_id = df.iloc[owner_row, col]

            if pd.isna(owner_id):
                continue

            block = df.iloc[header_row + 1:, col:col + 5].copy()

            if block.shape[1] < 5:
                continue

            block.columns = [
                "Holder_Name",
                "Holder_ID",
                "Holder_Type",
                "Percent_Held_by_Holder",
                "Holder_Country"
            ]

            block["Owner_ID"] = owner_id

            block = block.dropna(
                subset=["Holder_Name"],
                how="all"
            )

            results.append(block)

        df_result = pd.concat(results, ignore_index=True)

        df_result = df_result[
            ["Owner_ID",
            "Holder_Name",
            "Holder_ID",
            "Holder_Type",
            "Percent_Held_by_Holder",
            "Holder_Country"]
        ]
        # Save to CSV
        output_file = os.path.join(folder_csv, f"SPGlobal_PublicProperty_{metal}.csv")
        df_result.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Saved: {output_file} ({len(df_result)} rows)")
    except FileNotFoundError:
        print(f"File not found: {file_xlsx}")
    except Exception as e:
        print(f"Error processing {file_xlsx}: {e}")

# Produce cost curve CSVs from MineEconomics files
for metal in metals:
    file_xlsx = f"inputs/SPGlobal_MineEconomics_08-Jul-2026_{metal}.xlsx"
    try:
        # Read Data sheet and use row 13 as header
        df = pd.read_excel(file_xlsx, sheet_name='Data', header=12)
        # Drop empty rows and empty columns
        df = df.dropna(how='all').dropna(axis=1, how='all')

        output_file = os.path.join(folder_csv, f"SPGlobal_CostCurve_{metal}.csv")
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Saved: {output_file} ({len(df)} rows, {len(df.columns)} columns)")
    except FileNotFoundError:
        print(f"File not found: {file_xlsx}")
    except Exception as e:
        print(f"Error processing {file_xlsx}: {e}")

#Produce CSV file for the country risk profile
file_xlsx = f"inputs/SPGlobal_CountryPMIAndRiskData_COUNTRYRISKSCORES_09-Jun-2026.xlsx"
try:
    df = pd.read_excel(file_xlsx, sheet_name='COUNTRY RISK SCORES', header=7)
    df = df.dropna(how='all').dropna(axis=1, how='all')

    output_file = os.path.join(folder_csv, "SPGlobal_CountryRiskScores.csv")
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Saved: {output_file} ({len(df)} rows, {len(df.columns)} columns)")
except FileNotFoundError:
    print(f"File not found: {file_xlsx}")
except Exception as e:
    print(f"Error processing {file_xlsx}: {e}")
