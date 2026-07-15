from datasets import load_dataset
import pandas as pd

print("Downloading SymCAT dataset...")

dataset = load_dataset(
    "cristian-untaru/symcat-medical-triage-dataset"
)

print(dataset)

# Convert train split
df = dataset["train"].to_pandas()

print(df.head())

# Save locally
df.to_csv(
    "datasets/symcat.csv",
    index=False
)

print("Dataset saved successfully")