import json
import time
import os
import csv
import random
import datetime
import requests
from llm.generate_caption import generate_caption

encoding = 'latin-1'

# Load secrets
with open("config/secrets.json", "r") as f:
    secrets = json.load(f)

ACCESS_TOKEN = secrets["access_token"]
IG_USER_ID = secrets["ig_user_id"]

# Ensure log file exists
def ensure_log():
    if not os.path.exists("data/posted_log.csv"):
        with open("data/posted_log.csv", "w", newline="", encoding=encoding) as f:
            writer = csv.writer(f)
            writer.writerow(["id", "timestamp", "status"])

def already_posted(product_id):
    if not os.path.exists("data/posted_log.csv"):
        return False
    with open("data/posted_log.csv", "r", encoding=encoding) as f:
        return product_id in f.read()

def log_post(product_id, status):
    with open("data/posted_log.csv", "a", newline="", encoding=encoding) as f:
        writer = csv.writer(f)
        writer.writerow([product_id, time.strftime("%Y-%m-%d %H:%M:%S"), status])

def download_image(url, output_path):
    res = requests.get(url)
    if res.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(res.content)
    else:
        raise Exception(f"Failed to download image: {url}")

def download_all_images(row, product_dir):
    image_urls = []
    base_url = row.get("image_link")
    if base_url:
        image_urls.append((base_url, "img.jpg"))

        filename_base = base_url.split("/")[-1].rsplit(".", 1)[0]
        extension = base_url.split("/")[-1].rsplit(".", 1)[-1]

        for i in range(1, 5):
            key = f"Zusatzbild_{i}"
            if row.get(key):
                alt_filename = f"{filename_base}_{i}.{extension}"
                alt_url = base_url.rsplit("/", 1)[0] + "/" + alt_filename
                image_urls.append((alt_url, f"img_{i}.jpg"))

    for url, filename in image_urls:
        output_path = os.path.join(product_dir, filename)
        try:
            download_image(url, output_path)
        except Exception as e:
            print(f"Warning: Could not download {url}: {e}")

def is_seasonally_relevant(row):
    today = datetime.date.today()
    month = today.month
    category = row.get("category", "").lower()
    title = row.get("titel", "").lower()
    description = row.get("description", "").lower()

    # Christmas: December
    if month == 12:
        return any(keyword in (title + description + category) for keyword in ["weihnachten", "xmas", "christmas", "advent"])

    # Easter: March or April
    if month in [3, 4]:
        return any(keyword in (title + description + category) for keyword in ["ostern", "hase", "frühling", "oster"])

    # Outside those months: avoid themed products
    return not any(k in (title + description + category) for k in ["weihnachten", "xmas", "christmas", "advent", "ostern", "hase"])

def main():
    ensure_log()
    os.makedirs("output", exist_ok=True)

    with open("data/product_list.csv", "r", encoding=encoding) as f:
        reader = list(csv.DictReader(f, delimiter=';'))
        random.shuffle(reader)

        for row in reader:
            product_id = row.get("id")
            if not product_id:
                continue
            if already_posted(product_id):
                continue

            try:
                stock = int(float(row.get("Bestand", 0)))
            except ValueError:
                stock = 0

            if stock < 3:
                continue

            if not is_seasonally_relevant(row):
                continue

            name = row.get("titel")
            description = row.get("description")

            try:
                product_dir = os.path.join("output", product_id)
                os.makedirs(product_dir, exist_ok=True)

                caption_path = os.path.join(product_dir, "caption.txt")

                # Download all images (main + Zusatzbilder)
                download_all_images(row, product_dir)

                # Generate and save caption
                caption = generate_caption(description, name)
                with open(caption_path, "w", encoding="utf-8") as f:
                    f.write(caption)

                log_post(product_id, "prepared")
                break  # Only prepare one product per run
            except Exception as e:
                log_post(product_id, f"failed: {str(e)}")
                continue

if __name__ == "__main__":
    main()