import pandas as pd

df = pd.read_stata("results/sc3_mindemand_results.dta")
print(df.columns.tolist())
print(df.head(5))
df.to_csv("results/sc3_mindemand_results.csv", index=False)
print("Saved to results/sc3_mindemand_results.csv")