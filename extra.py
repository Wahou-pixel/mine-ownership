import os
import pandas as pd

folder_csv = "outputs"
metals = ["cobalt", "copper", "lithium", "nickel", "graphite"]

for metal in metals:
	csv_file = os.path.join(folder_csv, f"SPGlobal_CostCurve_{metal}.csv")
	if not os.path.exists(csv_file):
		print(f"Cost-curve CSV not found, skipping: {csv_file}")
		continue
	try:
		df = pd.read_csv(csv_file, encoding='utf-8')
		print(metal, pd.read_csv(csv_file, nrows=0, encoding='utf-8').columns.tolist())

		# find the first column whose name contains 'paid' (case-insensitive)
		keywords = ["paid", "production"]
		paid_col = None
		for c in df.columns:
			if any(keyword in str(c).lower() for keyword in keywords):
				paid_col = c
				break

		if paid_col is None:
			print(f"No 'Paid' column found in {csv_file}, skipping")
			continue

		paid_vals = pd.to_numeric(df[paid_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
		# First value of Paid metal has to be 0 (ok with the way the file was constructed)
		paid_vals.iloc[0] = 0
		df[paid_col] = paid_vals
		cum_col = f"Cumulative {paid_col}"
		# First value has to be 0
		cum_vals = paid_vals.cumsum()
		if cum_col in df.columns:
			df[cum_col] = cum_vals
			print(f"Updated existing column '{cum_col}' in {csv_file}")
		else:
			df.insert(list(df.columns).index(paid_col) + 1, cum_col, cum_vals)
			print(f"Added column '{cum_col}' to {csv_file}")
		print(f"Updated: {csv_file} (added column '{cum_col}')")

		total_col = None
		for c in df.columns:
			if str(c).strip().lower().startswith("total"):
				total_col = c
				break
		if total_col is not None and len(df) > 1:
		# The first value becomes equal to the next one
			df.loc[df.index[0], total_col] = df.loc[df.index[1], total_col]
			print(f"Updated first value of '{total_col}'")

		df.to_csv(csv_file, index=False, encoding='utf-8')
	except Exception as e:
		print(f"Error processing {csv_file}: {e}")
	
	