import json
import time
import os
import re
import csv
import random
import datetime
import shutil
import pandas as pd

from llm.generate_caption import generate_caption

encoding = 'latin-1'

# Load secrets
with open("config/secrets.json", "r") as f:
    secrets = json.load(f)

ACCESS_TOKEN = secrets["access_token"]
IG_USER_ID = secrets["ig_user_id"]

PENDING_APPROVALS_CSV = "data/pending_approvals.csv"

# Ensure log file exists
def ensure_log():
    if not os.path.exists("data/posted_log.csv"):
        with open("data/posted_log.csv", "w", newline="", encoding=encoding) as f:
            writer = csv.writer(f)
            writer.writerow(["id", "timestamp", "status"])

def ensure_approvals_csv():
    if not os.path.exists(PENDING_APPROVALS_CSV):
        with open(PENDING_APPROVALS_CSV, "w", newline="", encoding=encoding) as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["product_id", "titel", "description", "caption_file", "image_urls_file", "approved"])

def already_posted(product_id):
    if not os.path.exists("data/posted_log.csv"):
        return False
    with open("data/posted_log.csv", "r", encoding=encoding) as f:
        return product_id in f.read()

def log_post(product_id, status):
    with open("data/posted_log.csv", "a", newline="", encoding=encoding) as f:
        writer = csv.writer(f)
        writer.writerow([product_id, time.strftime("%Y-%m-%d %H:%M:%S"), status])

def collect_all_image_urls(row):
    urls = []
    base_url = row.get("image_link")
    if base_url:
        urls.append(base_url)

        filename_base = base_url.split("/")[-1].rsplit(".", 1)[0]
        extension = base_url.split("/")[-1].rsplit(".", 1)[-1]

        for i in range(1, 5):
            key = f"Zusatzbild_{i}"
            if row.get(key):
                alt_filename = f"{filename_base}_{i}.{extension}"
                alt_url = base_url.rsplit("/", 1)[0] + "/" + alt_filename
                urls.append(alt_url)
    return urls

def append_to_approvals_csv(product_id, titel, description, caption_path, image_urls_path):
    # Read caption text
    with open(caption_path, "r", encoding='utf-8') as f:
        caption = f.read().strip()

    # Read image URLs and join them into one string with newlines
    with open(image_urls_path, "r", encoding='utf-8') as f:
        image_urls = "|".join([line.strip() for line in f if line.strip()])

    # Check if header is needed (file does not exist or is empty)
    needs_header = not os.path.exists(PENDING_APPROVALS_CSV) or os.stat(PENDING_APPROVALS_CSV).st_size == 0

    # Append to CSV using ';' as delimiter
    with open(PENDING_APPROVALS_CSV, "w", newline="", encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([product_id, titel, description, caption, image_urls, "FALSE"])

def is_seasonally_relevant(row):
    today = datetime.date.today()
    month = today.month
    category = row.get("category", "").lower()
    title = row.get("titel", "").lower()
    description = row.get("description", "").lower()

    if month == 12:
        return any(keyword in (title + description + category) for keyword in ["weihnachten", "xmas", "christmas", "advent"])
    if month in [3, 4]:
        return any(keyword in (title + description + category) for keyword in ["ostern", "hase", "frühling", "oster"])
    return not any(k in (title + description + category) for k in ["weihnachten", "xmas", "christmas", "advent", "ostern", "hase"])

def convert_csv_to_excel_and_copy(csv_path, excel_path):
    df = pd.read_csv(csv_path, sep=";", encoding="utf-8")
    with pd.ExcelWriter(excel_path, mode='a',engine='xlsxwriter') as writer:
        df.to_excel(writer,index=False)
    print(f"✅ Excel file saved: {excel_path}")

def prepare_multiple_products(limit=7):
    ensure_log()
    ensure_approvals_csv()
    os.makedirs("output", exist_ok=True)

    with open("data/product_list.csv", "r", encoding=encoding) as f:
        reader = list(csv.DictReader(f, delimiter=';'))
        random.shuffle(reader)

        prepared = 0
        for row in reader:
            if prepared >= limit:
                break

            product_id = row.get("id")
            if not product_id or already_posted(product_id) or re.match(r'^\d+H[A-Z]\d+', product_id):
                continue

            try:
                stock = int(float(row.get("Bestand", 0)))
                if stock < 10 or not is_seasonally_relevant(row):
                    continue

                name = row.get("titel")
                description = row.get("description")
                product_dir = os.path.join("output", product_id)
                os.makedirs(product_dir, exist_ok=True)

                caption_path = os.path.join(product_dir, "caption.txt")
                image_urls_path = os.path.join(product_dir, "image_urls.txt")
                image_urls = collect_all_image_urls(row)

                with open(image_urls_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(image_urls))

                caption = generate_caption(description, name, product_id)
                with open(caption_path, "w", encoding="utf-8") as f:
                    f.write(caption)

                append_to_approvals_csv(product_id, name, description, caption_path, image_urls_path)
                log_post(product_id, "prepared")
                prepared += 1

            except Exception as e:
                log_post(product_id, f"failed: {str(e)}")
                continue

if __name__ == "__main__":
    csv_path = "data/pending_approvals.csv"
    excel_path = secrets['sharepoint']

    prepare_multiple_products(limit=7)
    convert_csv_to_excel_and_copy(csv_path, excel_path)