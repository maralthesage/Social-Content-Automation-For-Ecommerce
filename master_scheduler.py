import os
import csv
import json
import time
import datetime
import requests
import pandas as pd

ENCODING = "utf-8"
LOG_PATH = "data/posted_log.csv"

with open("config/secrets.json", "r", encoding=ENCODING) as f:
    secrets = json.load(f)

ACCESS_TOKEN = secrets["access_token"]
IG_USER_ID = secrets["ig_user_id"]
APPROVALS_XLSX = secrets["sharepoint"]


def ensure_log():
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", newline="", encoding=ENCODING) as f:
            csv.writer(f).writerow(["id", "timestamp", "status"])


def update_log(product_id, status):
    # Load existing log (if any)
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, newline="", encoding=ENCODING) as f:
            reader = csv.reader(f)
            rows = [row for row in reader if row and row[0] != product_id]
    else:
        rows = []

    # Add the updated log entry
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    rows.append([product_id, timestamp, status])

    # Write the updated log back
    with open(LOG_PATH, "w", newline="", encoding=ENCODING) as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def get_approved_entries():
    if not os.path.exists(APPROVALS_XLSX):
        return []
    df = pd.read_excel(APPROVALS_XLSX, engine="openpyxl")
    df = df[df["approved"].astype(str).str.strip().str.lower().isin(["true", "wahr"])]
    return df.to_dict(orient="records")


def wait_until_ready(media_id):
    for _ in range(10):
        status_res = requests.get(
            f"https://graph.facebook.com/v22.0/{media_id}?fields=status_code",
            params={"access_token": ACCESS_TOKEN}
        )
        status = status_res.json().get("status_code")
        if status == "FINISHED":
            return True
        time.sleep(2)
    return False

def get_high_res_image_url(url: str) -> str:
    """Converts a product image URL to its high-resolution .webp version."""
    if not url:
        return url
    url = url.replace('/normal/', '/gross/')
    
    return url


def already_posted(product_id):
    if not os.path.exists(LOG_PATH):
        return False
    with open(LOG_PATH, "r", encoding=ENCODING) as f:
        reader = csv.DictReader(f, fieldnames=["id", "timestamp", "status"])
        return any(row["id"] == product_id and row["status"] == "published" for row in reader)


def upload_and_publish(product_id):
    folder_path = os.path.join("output", product_id)
    image_urls_path = os.path.join(folder_path, "image_urls.txt")
    caption_path = os.path.join(folder_path, "caption.txt")

    if not os.path.exists(image_urls_path):
        raise FileNotFoundError(f"No image_urls.txt found for {product_id}")
    if not os.path.exists(caption_path):
        raise FileNotFoundError(f"No caption.txt found for {product_id}")

    with open(image_urls_path, "r", encoding=ENCODING) as f:
        image_urls = [line.strip() for line in f if line.strip()]
        image_urls = [get_high_res_image_url(url) for url in image_urls]

    with open(caption_path, "r", encoding=ENCODING) as f:
        caption = f.read().strip().replace('\r\n', '\n')

    print(f"📸 Image URLs for {product_id}: {image_urls}")
    print(f"📝 Caption for {product_id}: {repr(caption)}")

    if not image_urls:
        raise Exception("No valid image URLs found.")

    media_ids = []

    if len(image_urls) == 1:
        res = requests.post(f"https://graph.facebook.com/v22.0/{IG_USER_ID}/media", params={
            "image_url": image_urls[0],
            "caption": caption,
            "access_token": ACCESS_TOKEN
        })
        creation_id = res.json().get("id")
        if not creation_id:
            raise Exception(f"Media creation failed: {res.text}")
        if not wait_until_ready(creation_id):
            raise Exception(f"Media {creation_id} not ready in time.")
        pub = requests.post(f"https://graph.facebook.com/v22.0/{IG_USER_ID}/media_publish", params={
            "creation_id": creation_id,
            "access_token": ACCESS_TOKEN
        })
    else:
        for url in image_urls:
            res = requests.post(f"https://graph.facebook.com/v22.0/{IG_USER_ID}/media", params={
                "image_url": url,
                "is_carousel_item": "true",
                "access_token": ACCESS_TOKEN
            })
            media_id = res.json().get("id")
            if not media_id:
                raise Exception(f"Carousel upload failed: {res.text}")
            if not wait_until_ready(media_id):
                raise Exception(f"Media {media_id} not ready in time.")
            media_ids.append(media_id)
            time.sleep(1)  # small pause between uploads

        print(f"🧩 Media IDs for carousel: {media_ids}")

        res = requests.post(f"https://graph.facebook.com/v22.0/{IG_USER_ID}/media", params={
            "children": ",".join(media_ids),
            "media_type": "CAROUSEL",
            "caption": caption,
            "access_token": ACCESS_TOKEN
        })
        carousel_id = res.json().get("id")
        if not carousel_id:
            raise Exception(f"Carousel container failed: {res.text}")
        if not wait_until_ready(carousel_id):
            raise Exception(f"Carousel {carousel_id} not ready in time.")
        pub = requests.post(f"https://graph.facebook.com/v22.0/{IG_USER_ID}/media_publish", params={
            "creation_id": carousel_id,
            "access_token": ACCESS_TOKEN
        })

    return pub.json()


def main():
    ensure_log()
    approved = get_approved_entries()
    print(f"🔍 Approved entries found: {len(approved)}")

    for row in approved:
        product_id = row["product_id"]

        if already_posted(product_id):
            print(f"⏭️ Skipping {product_id} (already published)")
            continue

        try:
            print(f"📤 Publishing {product_id} ...")
            response = upload_and_publish(product_id)
            update_log(product_id, "published")
            print(f"✅ Success: {response}")
            break
        except Exception as e:
            print(f"❌ Error posting {product_id}: {e}")
            update_log(product_id, f"failed: {e}")
            continue


if __name__ == "__main__":
    main()
