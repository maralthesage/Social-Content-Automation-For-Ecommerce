import pandas as pd
import requests
import os
import json


# Load secrets
with open("config/secrets.json", "r") as f:
    secrets = json.load(f)
    
ws_url = secrets['websale-url']    
encoding = "latin-1"

def fetch_product_data():
    print("Fetching product data...")
    
    # Load the full product CSV
    product_df = pd.read_csv(
        ws_url,
        encoding=encoding,
        on_bad_lines='skip',
        sep='\t'
    )

    # Base columns to keep
    base_columns = ['id', 'titel', 'description', 'image_link', 'Bestand']
    
    # Check and include Zusatzbild columns if present
    zusatz_columns = [col for col in product_df.columns if col.startswith("Zusatzbild_")]
    columns_to_export = base_columns + zusatz_columns

    product_df = product_df[columns_to_export]

    # Save to local CSV
    product_df.to_csv("data/product_list.csv", index=False, sep=';', encoding=encoding)
    print("Product list updated with Zusatzbild columns.")

if __name__ == "__main__":
    fetch_product_data()
